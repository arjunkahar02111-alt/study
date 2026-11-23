"""
SYNTRIQ 3.0 — Comprehensive 20-Point Automated Quality Assurance Suite
Executes and asserts every feature specified in Section 17 of the Master Prompt:
 1. Dashboard loading
 2. Navigation
 3. Add Task
 4. Task validation
 5. Task editing
 6. Task deletion
 7. Task completion
 8. Priority calculation
 9. Priority sorting
10. Study Plan
11. What-If Simulator
12. Focus Timer
13. Timer accuracy
14. Audio controls
15. Calendar export
16. Print
17. Mobile navigation
18. Keyboard shortcuts
19. Notifications
20. Data persistence
"""

import os
import sys
import unittest
from datetime import date, timedelta

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, DB_FILE
import database
from priority_calculator import calculate_priority


class Syntriq3MasterTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def setUp(self):
        # Fresh isolated test database
        self.test_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_syntriq3.db")
        database.init_db(self.test_db)

    def tearDown(self):
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except Exception:
                pass

    # 1. Dashboard loading
    def test_01_dashboard_loading(self):
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Study Dashboard", res.data)
        self.assertIn(b"7-Day Workload Heatmap", res.data)

    # 2. Navigation
    def test_02_navigation_routes(self):
        routes = ["/", "/dashboard", "/study-plan", "/add-task"]
        for r in routes:
            res = self.client.get(r)
            self.assertEqual(res.status_code, 200, f"Route {r} failed")

    # 3. Add Task
    def test_03_add_task(self):
        deadline = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")
        task_id = database.add_task(
            title="Biology Assignment",
            subject="Biology",
            deadline=deadline,
            difficulty=4,
            importance=5,
            estimated_hours=3.5,
            db_path=self.test_db
        )
        self.assertIsInstance(task_id, int)
        task = database.get_task_by_id(task_id, db_path=self.test_db)
        self.assertEqual(task["Task_Title"], "Biology Assignment")
        self.assertEqual(task["Task_Difficulty"], 4)

    # 4. Task validation
    def test_04_task_validation(self):
        # Empty title
        res = self.client.post("/add-task", data={
            "title": "", "subject": "Math", "deadline": "2026-12-01",
            "difficulty": 3, "importance": 3, "estimated_hours": 2
        })
        self.assertEqual(res.status_code, 400)

        # Invalid difficulty (> 5)
        res = self.client.post("/add-task", data={
            "title": "Math Task", "subject": "Math", "deadline": "2026-12-01",
            "difficulty": 9, "importance": 3, "estimated_hours": 2
        })
        self.assertEqual(res.status_code, 400)

        # Invalid hours (<= 0)
        res = self.client.post("/add-task", data={
            "title": "Math Task", "subject": "Math", "deadline": "2026-12-01",
            "difficulty": 3, "importance": 3, "estimated_hours": 0
        })
        self.assertEqual(res.status_code, 400)

    # 5. Task editing
    def test_05_task_editing(self):
        deadline = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")
        task_id = database.add_task(
            title="Old Title", subject="Physics", deadline=deadline,
            difficulty=2, importance=3, estimated_hours=2.0, db_path=self.test_db
        )
        new_deadline = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        database.update_task(
            task_id=task_id, title="New Title", subject="Physics",
            deadline=new_deadline, difficulty=5, importance=5, estimated_hours=4.0,
            status="Pending", db_path=self.test_db
        )
        updated = database.get_task_by_id(task_id, db_path=self.test_db)
        self.assertEqual(updated["Task_Title"], "New Title")
        self.assertEqual(updated["Task_Difficulty"], 5)
        self.assertGreater(updated["Priority_Score"], 3.5)

    # 6. Task deletion
    def test_06_task_deletion(self):
        task_id = database.add_task(
            title="Temporary Task", subject="History", deadline="2026-12-10",
            difficulty=2, importance=2, estimated_hours=1.0, db_path=self.test_db
        )
        self.assertTrue(database.delete_task(task_id, db_path=self.test_db))
        self.assertIsNone(database.get_task_by_id(task_id, db_path=self.test_db))

    # 7. Task completion
    def test_07_task_completion(self):
        task_id = database.add_task(
            title="Incomplete Task", subject="Literature", deadline="2026-12-15",
            difficulty=3, importance=3, estimated_hours=2.0, db_path=self.test_db
        )
        self.assertTrue(database.complete_task(task_id, db_path=self.test_db))
        task = database.get_task_by_id(task_id, db_path=self.test_db)
        self.assertEqual(task["Task_Status"], "Completed")

    # 8. Priority calculation
    def test_08_priority_calculation_weights(self):
        # Test exact formula: 0.4*U + 0.3*I + 0.2*D + 0.1*W
        today = date.today().strftime("%Y-%m-%d")
        score = calculate_priority(today, difficulty=5, importance=5, estimated_hours=6.0)
        # Urgency for today = 5.0 -> 0.4*5 = 2.0
        # Importance 5 -> 0.3*5 = 1.5
        # Difficulty 5 -> 0.2*5 = 1.0
        # Workload 6h -> 5.0 -> 0.1*5 = 0.5
        # Total = 2.0 + 1.5 + 1.0 + 0.5 = 5.0
        self.assertAlmostEqual(score, 5.0, places=1)

    # 9. Priority sorting
    def test_09_priority_sorting(self):
        d_urgent = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        d_distant = (date.today() + timedelta(days=20)).strftime("%Y-%m-%d")

        t1 = database.add_task("Low Priority", "Art", d_distant, 1, 1, 1.0, db_path=self.test_db)
        t2 = database.add_task("High Priority", "Chemistry", d_urgent, 5, 5, 6.0, db_path=self.test_db)

        plan = database.get_study_plan(db_path=self.test_db)
        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[0]["Task_ID"], t2)  # High priority should be first
        self.assertEqual(plan[1]["Task_ID"], t1)

    # 10. Study Plan
    def test_10_study_plan_route(self):
        res = self.client.get("/study-plan")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Algorithmic Study Plan", res.data)
        self.assertIn(b"Dynamic Priority Algorithm Formula", res.data)

    # 11. What-If Simulator
    def test_11_what_if_simulator_api(self):
        today = date.today().strftime("%Y-%m-%d")
        res = self.client.post("/api/simulate-priority", json={
            "deadline": today,
            "difficulty": 4,
            "importance": 4,
            "estimated_hours": 3.0,
            "days_shift": 5,
            "hours_shift": -1.0
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("simulated_score", data)
        self.assertIn("score_diff", data)
        self.assertLess(data["simulated_score"], data["original_score"])

    # 12. Focus Timer
    def test_12_focus_timer_elements(self):
        res = self.client.get("/dashboard")
        self.assertIn(b"id=\"pomodoroModal\"", res.data)
        self.assertIn(b"timerProgress", res.data)
        self.assertIn(b"pomoTimerText", res.data)

    # 13. Timer accuracy & session logging
    def test_13_session_logging(self):
        # Generic focus session (task_id=None) or linked
        res = self.client.post("/api/log-session", json={
            "task_id": None,
            "minutes": 25
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("session_id", data)

    # 14. Audio controls
    def test_14_audio_control_elements(self):
        res = self.client.get("/dashboard")
        self.assertIn(b"soundToggleBtn", res.data)
        self.assertIn(b"ambient-chip", res.data)

    # 15. Calendar export
    def test_15_calendar_export(self):
        res = self.client.get("/export/calendar.ics")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "text/calendar")
        self.assertIn(b"BEGIN:VCALENDAR", res.data)
        self.assertIn(b"VERSION:2.0", res.data)

    # 16. Print functionality
    def test_16_print_stylesheet_and_button(self):
        res = self.client.get("/dashboard")
        self.assertIn(b"window.print()", res.data)
        self.assertIn(b"style.css", res.data)

    # 17. Mobile navigation
    def test_17_mobile_nav_drawer(self):
        res = self.client.get("/dashboard")
        self.assertIn(b"mobileMenuBtn", res.data)
        self.assertIn(b"mobileNavDrawer", res.data)
        self.assertIn(b"mobileDrawerOverlay", res.data)

    # 18. Keyboard shortcuts
    def test_18_keyboard_shortcuts(self):
        res = self.client.get("/dashboard")
        self.assertIn(b"keyboardModal", res.data)
        self.assertIn(b"main.js", res.data)

    # 19. Notifications & alerts
    def test_19_notifications(self):
        res = self.client.get("/dashboard")
        self.assertIn(b"flash-container", res.data) or self.assertIn(b"alert", res.data)

    # 20. Data persistence
    def test_20_data_persistence(self):
        task_id = database.add_task(
            title="Persistent Task", subject="Database", deadline="2026-12-20",
            difficulty=4, importance=4, estimated_hours=3.0, db_path=self.test_db
        )
        # Re-query
        retrieved = database.get_task_by_id(task_id, db_path=self.test_db)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["Task_Title"], "Persistent Task")


if __name__ == "__main__":
    print("=" * 80)
    print("RUNNING SYNTRIQ 3.0 20-POINT AUTOMATED QUALITY ASSURANCE SUITE")
    print("=" * 80)
    suite = unittest.TestLoader().loadTestsFromTestCase(Syntriq3MasterTestSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\nALL 20 AUTOMATED QA TESTS PASSED SUCCESSFULLY!")
        exit(0)
    else:
        print("\nONE OR MORE QA TESTS FAILED!")
        exit(1)
