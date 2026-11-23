"""
Comprehensive Automated Test Suite for Smart Study Planner
Directly tests the 14 Test Cases specified in Criterion B: Test Plan.
"""

import os
import unittest
import tempfile
from datetime import date, timedelta

import database
from priority_calculator import (
    calculate_priority,
    calculate_urgency,
    calculate_workload,
    is_overdue,
    days_remaining,
)
from app import app


class SmartStudyPlannerTestCase(unittest.TestCase):
    def setUp(self):
        """Set up a fresh temporary SQLite database and test Flask client for each test."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        database.init_db(self.db_path)

        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

        # Override DB_FILE in app context for route tests
        self.original_db = database.DEFAULT_DB_PATH
        import app as app_module
        app_module.DB_FILE = self.db_path

        self.today = date.today()

    def tearDown(self):
        """Clean up temporary files."""
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    # -------------------------------------------------------------------------
    # Test Case 1: Add task
    # Feature: Add task
    # Expected Outcome: Task should be saved in the database
    # -------------------------------------------------------------------------
    def test_01_add_task(self):
        task_id = database.add_task(
            title="Chemistry Lab Report",
            subject="Chemistry",
            deadline=(self.today + timedelta(days=4)).strftime("%Y-%m-%d"),
            difficulty=3,
            importance=4,
            estimated_hours=3.5,
            db_path=self.db_path
        )
        self.assertIsNotNone(task_id)
        task = database.get_task_by_id(task_id, self.db_path)
        self.assertIsNotNone(task)
        self.assertEqual(task["Task_Title"], "Chemistry Lab Report")
        self.assertEqual(task["Task_Subject"], "Chemistry")
        self.assertEqual(task["Task_Status"], "Pending")

    # -------------------------------------------------------------------------
    # Test Case 2: Input validation
    # Feature: Input validation
    # Expected Outcome: System should display an error message for empty required fields
    # -------------------------------------------------------------------------
    def test_02_input_validation_empty_fields(self):
        # Database level test
        with self.assertRaises(ValueError) as ctx:
            database.add_task(
                title="",
                subject="Mathematics",
                deadline=(self.today + timedelta(days=2)).strftime("%Y-%m-%d"),
                difficulty=3,
                importance=3,
                estimated_hours=2.0,
                db_path=self.db_path
            )
        self.assertIn("Please complete all required fields", str(ctx.exception))

        # Web Route level test
        response = self.client.post("/add-task", data={
            "title": "",
            "subject": "Math",
            "deadline": (self.today + timedelta(days=1)).strftime("%Y-%m-%d"),
            "difficulty": "3",
            "importance": "3",
            "estimated_hours": "2"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Please complete all required fields", response.data)

    # -------------------------------------------------------------------------
    # Test Case 3: Difficulty validation
    # Feature: Difficulty validation
    # Expected Outcome: System should reject the invalid value (outside 1-5)
    # -------------------------------------------------------------------------
    def test_03_difficulty_validation(self):
        # Value < 1
        with self.assertRaises(ValueError):
            database.add_task("Test Task", "Subject", "2026-12-01", 0, 3, 2.0, db_path=self.db_path)

        # Value > 5
        with self.assertRaises(ValueError):
            database.add_task("Test Task", "Subject", "2026-12-01", 6, 3, 2.0, db_path=self.db_path)

        # Web route check
        res = self.client.post("/add-task", data={
            "title": "Bio Essay",
            "subject": "Biology",
            "deadline": (self.today + timedelta(days=3)).strftime("%Y-%m-%d"),
            "difficulty": "7",
            "importance": "4",
            "estimated_hours": "3"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn(b"Invalid input", res.data)

    # -------------------------------------------------------------------------
    # Test Case 4: Importance validation
    # Feature: Importance validation
    # Expected Outcome: System should reject the invalid value (outside 1-5)
    # -------------------------------------------------------------------------
    def test_04_importance_validation(self):
        # Value < 1
        with self.assertRaises(ValueError):
            database.add_task("Test Task", "Subject", "2026-12-01", 3, 0, 2.0, db_path=self.db_path)

        # Value > 5
        with self.assertRaises(ValueError):
            database.add_task("Test Task", "Subject", "2026-12-01", 3, 9, 2.0, db_path=self.db_path)

        # Web route check
        res = self.client.post("/add-task", data={
            "title": "Bio Essay",
            "subject": "Biology",
            "deadline": (self.today + timedelta(days=3)).strftime("%Y-%m-%d"),
            "difficulty": "3",
            "importance": "-2",
            "estimated_hours": "3"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn(b"Invalid input", res.data)

    # -------------------------------------------------------------------------
    # Test Case 5: Priority calculation
    # Feature: Priority calculation
    # Expected Outcome: System should calculate the correct priority score
    # -------------------------------------------------------------------------
    def test_05_priority_calculation(self):
        # Known test case values:
        # days_remaining = 1 (deadline = today + 1 day) -> urgency = 5
        # importance = 5
        # difficulty = 4
        # estimated_hours = 3.0 -> workload = 3 (since >= 2 and < 4)
        # Expected: (0.4 * 5) + (0.3 * 5) + (0.2 * 4) + (0.1 * 3)
        #         = 2.0 + 1.5 + 0.8 + 0.3 = 4.6
        score = calculate_priority(
            deadline=(self.today + timedelta(days=1)),
            difficulty=4,
            importance=5,
            estimated_hours=3.0,
            current_date=self.today
        )
        self.assertEqual(score, 4.6)

        # Another case:
        # days_remaining = 10 -> urgency = 2 (<= 14)
        # importance = 2
        # difficulty = 2
        # estimated_hours = 0.5 -> workload = 1 (< 1)
        # Expected: (0.4*2) + (0.3*2) + (0.2*2) + (0.1*1) = 0.8 + 0.6 + 0.4 + 0.1 = 1.9
        score2 = calculate_priority(
            deadline=(self.today + timedelta(days=10)),
            difficulty=2,
            importance=2,
            estimated_hours=0.5,
            current_date=self.today
        )
        self.assertEqual(score2, 1.9)

    # -------------------------------------------------------------------------
    # Test Case 6: Task sorting
    # Feature: Task sorting
    # Expected Outcome: Tasks should be displayed in descending priority order
    # -------------------------------------------------------------------------
    def test_06_task_sorting(self):
        # Low priority task (score around 1.9)
        database.add_task("Low Task", "General", (self.today + timedelta(days=12)).strftime("%Y-%m-%d"), 1, 2, 0.5, db_path=self.db_path)
        # High priority task (score around 4.6)
        database.add_task("High Task", "General", (self.today + timedelta(days=1)).strftime("%Y-%m-%d"), 4, 5, 4.0, db_path=self.db_path)
        # Medium priority task
        database.add_task("Med Task", "General", (self.today + timedelta(days=5)).strftime("%Y-%m-%d"), 3, 3, 2.0, db_path=self.db_path)

        plan = database.get_study_plan(self.db_path, current_date=self.today)
        self.assertEqual(len(plan), 3)
        self.assertEqual(plan[0]["Task_Title"], "High Task")
        self.assertEqual(plan[1]["Task_Title"], "Med Task")
        self.assertEqual(plan[2]["Task_Title"], "Low Task")
        self.assertGreaterEqual(plan[0]["Priority_Score"], plan[1]["Priority_Score"])
        self.assertGreaterEqual(plan[1]["Priority_Score"], plan[2]["Priority_Score"])

    # -------------------------------------------------------------------------
    # Test Case 7: Edit task
    # Feature: Edit task
    # Expected Outcome: Updated information should be saved and priority recalculated
    # -------------------------------------------------------------------------
    def test_07_edit_task(self):
        t_id = database.add_task(
            "Draft Essay", "English", (self.today + timedelta(days=10)).strftime("%Y-%m-%d"), 2, 3, 1.0, db_path=self.db_path
        )
        old_task = database.get_task_by_id(t_id, self.db_path)
        old_score = old_task["Priority_Score"]

        # Now change deadline to tomorrow and difficulty to 5 (Urgency goes from 2 to 5)
        new_deadline = (self.today + timedelta(days=1)).strftime("%Y-%m-%d")
        database.update_task(
            task_id=t_id,
            title="Final Polished Essay",
            subject="English Literature",
            deadline=new_deadline,
            difficulty=5,
            importance=5,
            estimated_hours=4.0,
            db_path=self.db_path
        )

        updated_task = database.get_task_by_id(t_id, self.db_path)
        self.assertEqual(updated_task["Task_Title"], "Final Polished Essay")
        self.assertEqual(updated_task["Task_Deadline"], new_deadline)
        self.assertGreater(updated_task["Priority_Score"], old_score)

    # -------------------------------------------------------------------------
    # Test Case 8: Delete task
    # Feature: Delete task
    # Expected Outcome: Task should be removed from the database
    # -------------------------------------------------------------------------
    def test_08_delete_task(self):
        t_id = database.add_task(
            "To Delete", "Art", (self.today + timedelta(days=5)).strftime("%Y-%m-%d"), 1, 1, 1.0, db_path=self.db_path
        )
        self.assertIsNotNone(database.get_task_by_id(t_id, self.db_path))

        success = database.delete_task(t_id, self.db_path)
        self.assertTrue(success)
        self.assertIsNone(database.get_task_by_id(t_id, self.db_path))

    # -------------------------------------------------------------------------
    # Test Case 9: Complete task
    # Feature: Complete task
    # Expected Outcome: Task status should change to completed
    # -------------------------------------------------------------------------
    def test_09_complete_task(self):
        t_id = database.add_task(
            "Physics Lab", "Physics", (self.today + timedelta(days=2)).strftime("%Y-%m-%d"), 4, 4, 3.0, db_path=self.db_path
        )
        task = database.get_task_by_id(t_id, self.db_path)
        self.assertEqual(task["Task_Status"], "Pending")

        database.complete_task(t_id, self.db_path)
        completed = database.get_task_by_id(t_id, self.db_path)
        self.assertEqual(completed["Task_Status"], "Completed")

    # -------------------------------------------------------------------------
    # Test Case 10: Overdue tasks
    # Feature: Overdue tasks
    # Expected Outcome: Task should be labelled as overdue
    # -------------------------------------------------------------------------
    def test_10_overdue_tasks(self):
        past_date = (self.today - timedelta(days=2)).strftime("%Y-%m-%d")
        t_id = database.add_task(
            "Past Assignment", "History", past_date, 3, 3, 2.0, db_path=self.db_path
        )
        task = database.get_task_by_id(t_id, self.db_path)
        self.assertTrue(task["is_overdue"])
        self.assertLess(task["days_remaining"], 0)

        overdue_list = database.get_overdue_tasks(self.db_path, current_date=self.today)
        self.assertTrue(any(t["Task_ID"] == t_id for t in overdue_list))

    # -------------------------------------------------------------------------
    # Test Case 11: Upcoming deadlines
    # Feature: Upcoming deadlines
    # Expected Outcome: Upcoming tasks should be displayed clearly
    # -------------------------------------------------------------------------
    def test_11_upcoming_deadlines(self):
        upcoming_date = (self.today + timedelta(days=3)).strftime("%Y-%m-%d")
        far_date = (self.today + timedelta(days=30)).strftime("%Y-%m-%d")

        t1 = database.add_task("Near Task", "Math", upcoming_date, 3, 3, 2.0, db_path=self.db_path)
        t2 = database.add_task("Far Task", "Math", far_date, 3, 3, 2.0, db_path=self.db_path)

        upcoming = database.get_upcoming_tasks(days_ahead=7, db_path=self.db_path, current_date=self.today)
        upcoming_ids = [t["Task_ID"] for t in upcoming]

        self.assertIn(t1, upcoming_ids)
        self.assertNotIn(t2, upcoming_ids)

    # -------------------------------------------------------------------------
    # Test Case 12: Data storage
    # Feature: Data storage
    # Expected Outcome: Saved tasks should remain available upon reconnect/reload
    # -------------------------------------------------------------------------
    def test_12_data_storage(self):
        t_id = database.add_task(
            "Persistent Task", "Economics", (self.today + timedelta(days=5)).strftime("%Y-%m-%d"), 3, 4, 2.0, db_path=self.db_path
        )
        # Close and reopen by querying a brand-new connection
        all_tasks = database.get_all_tasks(self.db_path)
        persisted = [t for t in all_tasks if t["Task_ID"] == t_id]
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["Task_Title"], "Persistent Task")

    # -------------------------------------------------------------------------
    # Test Case 13: Study plan
    # Feature: Study plan
    # Expected Outcome: An organized study plan should be generated
    # -------------------------------------------------------------------------
    def test_13_study_plan(self):
        database.add_task("Task 1", "Sub1", (self.today + timedelta(days=5)).strftime("%Y-%m-%d"), 2, 2, 1.0, db_path=self.db_path)
        database.add_task("Task 2", "Sub2", (self.today + timedelta(days=1)).strftime("%Y-%m-%d"), 5, 5, 6.0, db_path=self.db_path)
        
        plan = database.get_study_plan(self.db_path, current_date=self.today)
        self.assertGreaterEqual(len(plan), 2)
        # Top task in study plan must be Task 2
        self.assertEqual(plan[0]["Task_Title"], "Task 2")
        self.assertIn("Priority_Score", plan[0])
        self.assertIn("urgency", plan[0])
        self.assertIn("workload", plan[0])

    # -------------------------------------------------------------------------
    # Test Case 14: User interface
    # Feature: User interface
    # Expected Outcome: Pages should work correctly and be easy to navigate
    # -------------------------------------------------------------------------
    def test_14_user_interface(self):
        # 1. Dashboard responds OK
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Study Dashboard", res.data)
        self.assertIn(b"All Tasks", res.data)

        # 2. Add Task page responds OK
        res = self.client.get("/add-task")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Add Study Task", res.data)

        # 3. Study Plan page responds OK
        res = self.client.get("/study-plan")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Algorithmic Study Plan", res.data)

    # -------------------------------------------------------------------------
    # Test Case 15: Calendar Export (.ics)
    # -------------------------------------------------------------------------
    def test_15_calendar_export(self):
        database.add_task("Math Exam", "Math", (self.today + timedelta(days=2)).strftime("%Y-%m-%d"), 4, 5, 3.0, db_path=self.db_path)
        res = self.client.get("/export/calendar.ics")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/calendar", res.content_type)
        self.assertIn(b"BEGIN:VCALENDAR", res.data)
        self.assertIn(b"Math Exam", res.data)

    # -------------------------------------------------------------------------
    # Test Case 16: Subtasks Management
    # -------------------------------------------------------------------------
    def test_16_subtask_crud(self):
        t_id = database.add_task("Research Paper", "History", (self.today + timedelta(days=4)).strftime("%Y-%m-%d"), 3, 4, 4.0, db_path=self.db_path)
        sub_id = database.add_subtask(t_id, "Find 5 Sources", db_path=self.db_path)
        subs = database.get_subtasks_for_task(t_id, db_path=self.db_path)
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0]["Is_Completed"], 0)

        # Toggle
        database.toggle_subtask(sub_id, db_path=self.db_path)
        subs_after = database.get_subtasks_for_task(t_id, db_path=self.db_path)
        self.assertEqual(subs_after[0]["Is_Completed"], 1)

        # Delete
        database.delete_subtask(sub_id, db_path=self.db_path)
        self.assertEqual(len(database.get_subtasks_for_task(t_id, db_path=self.db_path)), 0)

    # -------------------------------------------------------------------------
    # Test Case 17: Focus Session & Study Streak
    # -------------------------------------------------------------------------
    def test_17_study_session_logging(self):
        t_id = database.add_task("Session Task", "Biology", (self.today + timedelta(days=2)).strftime("%Y-%m-%d"), 3, 3, 2.0, db_path=self.db_path)
        database.log_study_session(t_id, minutes=25, db_path=self.db_path)
        streak = database.get_study_streak(db_path=self.db_path, current_date=self.today)
        self.assertGreaterEqual(streak, 1)

    # -------------------------------------------------------------------------
    # Test Case 18: What-If Priority Simulator API
    # -------------------------------------------------------------------------
    def test_18_priority_simulator_api(self):
        res = self.client.post("/api/simulate-priority", json={
            "deadline": (self.today + timedelta(days=5)).strftime("%Y-%m-%d"),
            "difficulty": 3,
            "importance": 4,
            "estimated_hours": 2.0,
            "days_shift": -4, # moves deadline from 5 days away to tomorrow (urgency jumps from 3 to 5)
            "hours_shift": 2.0
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("simulated_score", data)
        self.assertGreater(data["simulated_score"], data["original_score"])


if __name__ == "__main__":
    unittest.main()
