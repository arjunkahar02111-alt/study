"""
SYNTRIQ 3.1 - Time Intelligence & Academic Productivity Verification Suite
Tests all 12 core requirements:
1. Task creation without mandatory estimated duration
2. Neutral workload formula fallback (workload 3.0 = 0.3)
3. Starting tracking session creates ActiveSession
4. Live active session retrieval via API
5. Single active session enforcement with conflict detection
6. Conflict resolution via force switch
7. Session pause without drift or loss of accumulated seconds
8. Session resume
9. Stopping tracking session persists total focus duration in task
10. Completing task auto-stops active session and records Completed_At
11. Dedicated Time Intelligence dashboard (/time-intelligence) renders real metrics
12. Task session history retrieval via API
"""

import unittest
import time
import os
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
import database as db
import priority_calculator as pc

class TestTimeIntelligenceEngine(unittest.TestCase):
    def setUp(self):
        # Create unique temp db
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()
        db.init_db(self.db_path)

        # Set Flask testing client
        app.config["TESTING"] = True
        app.config["DB_FILE"] = self.db_path
        self.app = app.test_client()
        # Override default db for app context
        self._orig_db_path = db.DEFAULT_DB_PATH
        db.DEFAULT_DB_PATH = self.db_path

    def tearDown(self):
        import gc
        gc.collect()
        db.DEFAULT_DB_PATH = self._orig_db_path
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_01_task_creation_without_estimated_duration(self):
        """Criterion 1: Task creation must NOT require estimated hours."""
        task_id = db.add_task(
            title="Calculus Problem Set",
            subject="Mathematics",
            deadline=(date.today() + timedelta(days=5)).strftime("%Y-%m-%d"),
            difficulty=4,
            importance=5,
            estimated_hours=None,
            db_path=self.db_path
        )
        task = db.get_task_by_id(task_id, self.db_path)
        self.assertIsNotNone(task)
        self.assertIsNone(task["Estimated_Hours"])
        self.assertEqual(task["total_tracked_seconds"], 0)
        self.assertEqual(task["tracked_time_formatted"], "0m")

    def test_02_neutral_workload_fallback(self):
        """Criterion 2: Optional target duration uses transparent neutral workload 3.0."""
        # When omitted: Workload = 3.0 -> 0.1 * 3 = 0.3
        workload_none = pc.calculate_workload(None)
        self.assertEqual(workload_none, 3)

        deadline = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        score_neutral = pc.calculate_priority(deadline, 3, 3, estimated_hours=None)
        # Urgency: 2 days left -> 4. 0.4*4 + 0.3*3 + 0.2*3 + 0.1*3 = 1.6 + 0.9 + 0.6 + 0.3 = 3.4
        self.assertAlmostEqual(score_neutral, 3.4, places=2)

    def test_03_start_tracking_session(self):
        """Criterion 3: Starting tracking creates ActiveSession and starts clock."""
        task_id = db.add_task("Physics Lab Report", "Physics", "2026-11-30", 3, 4, db_path=self.db_path)
        res = db.start_tracking_session(task_id, self.db_path)
        self.assertEqual(res["status"], "started")
        self.assertEqual(res["task_id"], task_id)

        active = db.get_active_session(self.db_path)
        self.assertIsNotNone(active)
        self.assertTrue(active["has_active"])
        self.assertEqual(active["task_id"], task_id)
        self.assertFalse(active["is_paused"])
        self.assertGreaterEqual(active["elapsed_seconds"], 0)

    def test_04_active_session_api(self):
        """Criterion 4: Live active session endpoint /api/active-session returns correct JSON."""
        task_id = db.add_task("History Essay", "History", "2026-12-01", 3, 3, db_path=self.db_path)
        db.start_tracking_session(task_id, self.db_path)

        response = self.app.get("/api/active-session")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["has_active"])
        self.assertEqual(data["task_title"], "History Essay")
        self.assertEqual(data["task_subject"], "History")

    def test_05_single_active_session_conflict_enforcement(self):
        """Criterion 5: Only one active session allowed system-wide; conflict detected without force."""
        task1 = db.add_task("Task Alpha", "CS", "2026-11-28", 4, 4, db_path=self.db_path)
        task2 = db.add_task("Task Beta", "CS", "2026-11-29", 3, 3, db_path=self.db_path)

        db.start_tracking_session(task1, self.db_path)

        # Attempt to start task 2 without force switch
        conflict = db.start_tracking_session(task2, force_switch=False, db_path=self.db_path)
        self.assertTrue(conflict.get("has_conflict"))
        self.assertEqual(conflict["running_task"]["task_id"], task1)

        # Active session must remain task1
        active = db.get_active_session(self.db_path)
        self.assertEqual(active["task_id"], task1)

    def test_06_conflict_resolution_force_switch(self):
        """Criterion 6: Force switch cleanly stops task 1 and starts task 2."""
        task1 = db.add_task("Task Alpha", "CS", "2026-11-28", 4, 4, db_path=self.db_path)
        task2 = db.add_task("Task Beta", "CS", "2026-11-29", 3, 3, db_path=self.db_path)

        db.start_tracking_session(task1, self.db_path)
        time.sleep(1.05)

        # Force switch to task2
        res = db.start_tracking_session(task2, force_switch=True, db_path=self.db_path)
        self.assertEqual(res["status"], "started")
        self.assertEqual(res["task_id"], task2)

        # Active session is now task2
        active = db.get_active_session(self.db_path)
        self.assertEqual(active["task_id"], task2)

        # Task 1 must have its recorded session
        sessions1 = db.get_task_sessions(task1, self.db_path)
        self.assertGreaterEqual(len(sessions1), 1)
        self.assertGreaterEqual(sessions1[0]["duration_seconds"], 1)

    def test_07_pause_and_resume_session(self):
        """Criteria 7 & 8: Pause preserves accumulated duration and stops drift; resume continues."""
        task_id = db.add_task("Biology Quiz Prep", "Biology", "2026-11-27", 3, 3, db_path=self.db_path)
        db.start_tracking_session(task_id, self.db_path)
        time.sleep(1.05)

        # Pause
        pause_res = db.pause_tracking_session(self.db_path)
        self.assertTrue(pause_res["is_paused"])
        accum = pause_res["accumulated_seconds"]
        self.assertGreaterEqual(accum, 1)

        # Verify active session reflects paused state
        active = db.get_active_session(self.db_path)
        self.assertTrue(active["is_paused"])
        self.assertEqual(active["elapsed_seconds"], accum)

        # Resume
        resume_res = db.resume_tracking_session(self.db_path)
        self.assertFalse(resume_res["is_paused"])

        active_resumed = db.get_active_session(self.db_path)
        self.assertFalse(active_resumed["is_paused"])

    def test_09_stop_session_updates_task_total(self):
        """Criterion 9: Stopping session persists total tracked seconds into task."""
        task_id = db.add_task("Literature Review", "English", "2026-11-28", 2, 4, db_path=self.db_path)
        db.start_tracking_session(task_id, self.db_path)
        time.sleep(1.1)

        stop_res = db.stop_tracking_session(self.db_path)
        self.assertEqual(stop_res["status"], "stopped")
        self.assertGreaterEqual(stop_res["duration_seconds"], 1)

        # Active session is now None
        active = db.get_active_session(self.db_path)
        self.assertIsNone(active)

        # Task total tracked seconds updated
        task = db.get_task_by_id(task_id, self.db_path)
        self.assertGreaterEqual(task["Total_Tracked_Seconds"], 1)
        self.assertIsNotNone(task["First_Tracked_At"])

    def test_10_complete_task_finalizes_session(self):
        """Criterion 10: Completing a task auto-finalizes any active session and sets Completed_At."""
        task_id = db.add_task("Chemistry Problem Set", "Chemistry", "2026-11-26", 4, 5, db_path=self.db_path)
        db.start_tracking_session(task_id, self.db_path)
        time.sleep(1.05)

        # Complete task
        db.complete_task(task_id, self.db_path)

        # Active session cleared
        active = db.get_active_session(self.db_path)
        self.assertIsNone(active)

        # Task is completed and has Completed_At
        task = db.get_task_by_id(task_id, self.db_path)
        self.assertEqual(task["Task_Status"], "Completed")
        self.assertIsNotNone(task["Completed_At"])
        self.assertGreaterEqual(task["Total_Tracked_Seconds"], 1)

    def test_11_time_intelligence_dashboard_renders(self):
        """Criterion 11: Dedicated dashboard /time-intelligence renders with 200 OK and metrics."""
        task_id = db.add_task("Data Structures Project", "CS", "2026-11-27", 5, 5, db_path=self.db_path)
        db.start_tracking_session(task_id, self.db_path)
        time.sleep(1.05)
        db.stop_tracking_session(self.db_path)

        response = self.app.get("/time-intelligence")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Time Intelligence", html)
        self.assertIn("Data Structures Project", html)
        self.assertIn("Subject-Wise Time Distribution", html)
        self.assertIn("Focus Session History", html)

    def test_12_task_sessions_api(self):
        """Criterion 12: GET /api/tasks/<id>/sessions returns logged sessions."""
        task_id = db.add_task("Linear Algebra Quiz", "Math", "2026-11-29", 3, 4, db_path=self.db_path)
        db.start_tracking_session(task_id, self.db_path)
        time.sleep(1.05)
        db.stop_tracking_session(self.db_path)

        response = self.app.get(f"/api/tasks/{task_id}/sessions")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["task_id"], task_id)
        self.assertGreaterEqual(data["total_sessions"], 1)
        self.assertGreaterEqual(len(data["sessions"]), 1)

if __name__ == "__main__":
    unittest.main()
