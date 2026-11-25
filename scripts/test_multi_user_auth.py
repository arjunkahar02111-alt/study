"""
SYNTRIQ Mandatory Multi-User Authentication & Data Isolation Security Suite
Verifies TEST 1 through TEST 9 plus unauthenticated route protection,
Firebase token verification, cross-UID rejection, and legacy data quarantine.
"""

import gc
import os
import sys
import tempfile
import time
import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
import database as db
import firebase_auth
import firestore_store


class TestMultiUserAuthIsolation(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()
        db.init_db(self.db_path)

        # Force local UID-isolated SQLite store in offline unit/integration tests even when .env exists
        self._fb_patcher = patch.object(firebase_auth, "is_firebase_configured", return_value=False)
        self._fb_patcher.start()

        app.config["TESTING"] = True
        app.config["DB_FILE"] = self.db_path
        self._orig_db_path = db.DEFAULT_DB_PATH
        db.DEFAULT_DB_PATH = self.db_path

        self.client_a = app.test_client()
        self.client_b = app.test_client()
        self.anon_client = app.test_client()

        self.user_a = {
            "uid": "uid_alice_001",
            "email": "alice@gmail.com",
            "name": "Alice Kahar",
            "picture": "https://example.com/alice.png",
        }
        self.user_b = {
            "uid": "uid_bob_002",
            "email": "bob@gmail.com",
            "name": "Bob Student",
            "picture": "https://example.com/bob.png",
        }

    def tearDown(self):
        self._fb_patcher.stop()
        gc.collect()
        db.DEFAULT_DB_PATH = self._orig_db_path
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def _login_client(self, client, user_claims):
        with patch.object(firebase_auth, "verify_firebase_id_token", return_value={**user_claims, "email_verified": True, "exp": int(time.time()) + 3600}):
            with patch.object(firebase_auth, "is_firebase_configured", return_value=False):
                res = client.post("/auth/session", json={"idToken": f"mock_token_{user_claims['uid']}"})
                self.assertEqual(res.status_code, 200)
                return res

    def test_00_unauthenticated_routes_blocked(self):
        """Protected HTML routes redirect to /login; protected APIs return 401."""
        for route in ["/", "/dashboard", "/study-plan", "/add-task", "/time-intelligence", "/routines", "/settings"]:
            res = self.anon_client.get(route)
            self.assertEqual(res.status_code, 302, f"{route} should redirect when unauthenticated")
            self.assertIn("/login", res.headers.get("Location", ""))

        for api_route in ["/api/active-session", "/api/time-intelligence"]:
            res = self.anon_client.get(api_route)
            self.assertEqual(res.status_code, 401)

        login_res = self.anon_client.get("/login")
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b"Continue with Google", login_res.data)

    def test_01_to_05_user_a_logout_user_b_empty_and_restore(self):
        """
        TEST 1: User A logs in and creates a study routine & task.
        TEST 2: User A logs out.
        TEST 3: User B logs in and sees an empty personal workspace (never User A's data).
        TEST 4: User B creates their own schedule.
        TEST 5: User A logs in again and sees their original routine without User B's data.
        """
        # TEST 1: User A logs in and creates routine + task
        res_a = self._login_client(self.client_a, self.user_a)
        self.assertTrue(res_a.get_json()["is_new_user"])

        self.client_a.post("/routines/add", data={
            "title": "Alice Morning Physics Block",
            "subject": "Physics",
            "day_of_week": "Monday",
            "start_time": "07:00",
            "end_time": "08:30",
            "focus_goal": "Wave optics",
        })
        self.client_a.post("/add-task", data={
            "title": "Alice Physics IA Draft",
            "subject": "Physics",
            "deadline": (date.today() + timedelta(days=2)).strftime("%Y-%m-%d"),
            "difficulty": "5",
            "importance": "5",
            "estimated_hours": "4.0",
        })
        dash_a = self.client_a.get("/dashboard")
        self.assertIn(b"Alice Physics IA Draft", dash_a.data)

        # TEST 2: User A logs out
        logout_a = self.client_a.post("/auth/logout", json={})
        self.assertEqual(logout_a.status_code, 200)
        self.assertEqual(self.client_a.get("/dashboard").status_code, 302)

        # TEST 3: User B logs in -> must see empty workspace
        res_b = self._login_client(self.client_b, self.user_b)
        self.assertTrue(res_b.get_json()["is_new_user"])

        dash_b = self.client_b.get("/dashboard")
        self.assertEqual(dash_b.status_code, 200)
        self.assertNotIn(b"Alice Physics IA Draft", dash_b.data)
        self.assertIn(b"Your study space is clear", dash_b.data)

        routines_b = self.client_b.get("/routines")
        self.assertNotIn(b"Alice Morning Physics Block", routines_b.data)

        # TEST 4: User B creates their own schedule
        self.client_b.post("/routines/add", data={
            "title": "Bob Evening Economics",
            "subject": "Economics",
            "day_of_week": "Tuesday",
            "start_time": "19:00",
            "end_time": "20:00",
        })
        self.assertIn(b"Bob Evening Economics", self.client_b.get("/routines").data)

        # TEST 5: User A logs back in -> sees original routine, zero User B leakage
        res_a2 = self._login_client(self.client_a, self.user_a)
        self.assertFalse(res_a2.get_json()["is_new_user"])
        routines_a2 = self.client_a.get("/routines").data
        self.assertIn(b"Alice Morning Physics Block", routines_a2)
        self.assertNotIn(b"Bob Evening Economics", routines_a2)

        dash_a2 = self.client_a.get("/dashboard").data
        self.assertIn(b"Alice Physics IA Draft", dash_a2)

    def test_06_cross_uid_access_rejected(self):
        """
        TEST 6: Attempting to read, edit, complete, delete, or track User B's task
        using User A's authenticated session is rejected, and Firestore 403 triggers PermissionError.
        """
        self._login_client(self.client_a, self.user_a)
        self._login_client(self.client_b, self.user_b)

        b_task_id = db.add_task(
            "Bob Secret Exam Prep",
            "Chemistry",
            (date.today() + timedelta(days=3)).strftime("%Y-%m-%d"),
            4,
            5,
            user_uid=self.user_b["uid"],
            db_path=self.db_path,
        )

        # User A cannot view/edit/complete/delete/track User B's task
        edit_res = self.client_a.get(f"/edit-task/{b_task_id}", follow_redirects=True)
        self.assertIn(b"Task not found", edit_res.data)
        self.assertNotIn(b"Bob Secret Exam Prep", edit_res.data)

        del_res = self.client_a.post(f"/delete-task/{b_task_id}", follow_redirects=True)
        self.assertIn(b"Task not found", del_res.data)
        self.assertIsNotNone(db.get_task_by_id(b_task_id, db_path=self.db_path, user_uid=self.user_b["uid"]))

        track_res = self.client_a.post("/api/time-tracking/start", json={"task_id": b_task_id})
        self.assertEqual(track_res.status_code, 400)

        # Firestore REST client raises FirestorePermissionError when Rules return 403 PERMISSION_DENIED
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.ok = False
        mock_resp.text = "Missing or insufficient permissions."
        with patch.dict(os.environ, {"FIREBASE_PROJECT_ID": "test-proj"}):
            with patch("firestore_store.requests.get", return_value=mock_resp):
                with self.assertRaises(firestore_store.FirestorePermissionError):
                    firestore_store.get_all_tasks(self.user_b["uid"], "user_a_id_token")

    def test_07_and_08_multi_device_and_account_switch_isolation(self):
        """
        TEST 7 & 8: Two independent sessions for the same UID see synced data;
        switching accounts cleanly resets session identity and never leaks stale state.
        """
        device1 = app.test_client()
        device2 = app.test_client()

        self._login_client(device1, self.user_a)
        self._login_client(device2, self.user_a)

        device1.post("/add-task", data={
            "title": "Cross-Device Synced Task",
            "subject": "Math",
            "deadline": (date.today() + timedelta(days=4)).strftime("%Y-%m-%d"),
            "difficulty": "3",
            "importance": "4",
        })
        self.assertIn(b"Cross-Device Synced Task", device2.get("/dashboard").data)

        # Refresh / switch device1 to User B
        device1.post("/auth/logout", json={})
        self._login_client(device1, self.user_b)
        me_res = device1.get("/auth/me").get_json()
        self.assertEqual(me_res["uid"], self.user_b["uid"])
        self.assertNotIn(b"Cross-Device Synced Task", device1.get("/dashboard").data)

    def test_09_logout_while_timer_running_preserves_session(self):
        """
        TEST 9: Logging out while a timer is running preserves User A's active study session
        without leaking its state to User B, and restores it when User A logs back in.
        """
        self._login_client(self.client_a, self.user_a)
        tid_a = db.add_task(
            "Alice Timed Essay",
            "English",
            (date.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
            4,
            4,
            user_uid=self.user_a["uid"],
            db_path=self.db_path,
        )
        start_res = self.client_a.post("/api/time-tracking/start", json={"task_id": tid_a})
        self.assertEqual(start_res.status_code, 200)
        self.assertTrue(start_res.get_json()["has_active"])

        # User A logs out while timer is actively running
        self.client_a.post("/auth/logout", json={})

        # User B logs in -> must have NO active session
        self._login_client(self.client_b, self.user_b)
        active_b = self.client_b.get("/api/active-session").get_json()
        self.assertFalse(active_b.get("has_active", False))

        # User A logs back in -> active session is preserved
        self._login_client(self.client_a, self.user_a)
        active_a = self.client_a.get("/api/active-session").get_json()
        self.assertTrue(active_a.get("has_active"))
        self.assertEqual(active_a["task_title"], "Alice Timed Essay")

    def test_10_legacy_data_quarantine_and_explicit_migration(self):
        """Pre-auth __legacy__ data is hidden from new users until explicitly migrated once."""
        # Insert a legacy pre-auth record
        db.add_task(
            "Pre-Auth Legacy Task",
            "History",
            (date.today() + timedelta(days=5)).strftime("%Y-%m-%d"),
            3,
            3,
            user_uid="__legacy__",
            db_path=self.db_path,
        )

        # User A logs in -> does NOT automatically see legacy task in their task list
        self._login_client(self.client_a, self.user_a)
        dash_a = self.client_a.get("/dashboard").data
        self.assertIn(b"Local Study Data Detected", dash_a)
        self.assertNotIn(b"Pre-Auth Legacy Task", dash_a)

        # User A explicitly confirms migration
        mig_res = self.client_a.post("/api/migrate-legacy-data", json={})
        self.assertEqual(mig_res.status_code, 200)
        self.assertEqual(mig_res.get_json()["migrated_count"], 1)
        self.assertIn(b"Pre-Auth Legacy Task", self.client_a.get("/dashboard").data)

        # User B logs in -> legacy banner is gone and User B never receives User A's migrated data
        self._login_client(self.client_b, self.user_b)
        dash_b = self.client_b.get("/dashboard").data
        self.assertNotIn(b"Local Study Data Detected", dash_b)
        self.assertNotIn(b"Pre-Auth Legacy Task", dash_b)

    def test_11_invalid_firebase_token_rejected(self):
        """Invalid or expired Firebase ID tokens are rejected with 401."""
        with patch.object(firebase_auth, "verify_firebase_id_token", side_effect=ValueError("Token expired")):
            res = self.anon_client.post("/auth/session", json={"idToken": "bad_token"})
            self.assertEqual(res.status_code, 401)


if __name__ == "__main__":
    unittest.main()
