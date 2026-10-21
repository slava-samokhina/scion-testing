#!/usr/bin/env python3
"""
Integration and Unit Tests for Scion Task Board Demo
Tests all API endpoints and static file serving.
"""

import json
import os
import sys
import threading
import time
import unittest
import urllib.request
from pathlib import Path

# Set test environment
TEST_PORT = 8099
os.environ["PORT"] = str(TEST_PORT)
os.environ["HOST"] = "127.0.0.1"

TEST_DB_PATH = Path(__file__).resolve().parent.parent / "test_tasks.db"
import backend.server as server_mod
server_mod.DB_PATH = TEST_DB_PATH


class TestTaskBoardServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.httpd = ReusableTCPServer(("127.0.0.1", TEST_PORT), TaskRequestHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()
        time.sleep(0.5)
        cls.base_url = f"http://127.0.0.1:{TEST_PORT}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        if TEST_DB_PATH.exists():
            try:
                TEST_DB_PATH.unlink()
            except Exception:
                pass

    def _request(self, path, method="GET", data=None):
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}
        req_data = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                status = resp.status
                body = resp.read().decode("utf-8")
                content_type = resp.headers.get("Content-Type", "")
                try:
                    json_body = json.loads(body)
                except Exception:
                    json_body = None
                return status, json_body, body, content_type
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            try:
                json_body = json.loads(body)
            except Exception:
                json_body = None
            return e.code, json_body, body, e.headers.get("Content-Type", "")

    def test_01_health(self):
        status, data, _, _ = self._request("/health")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("version", data)

    def test_02_get_tasks(self):
        status, data, _, _ = self._request("/api/tasks")
        self.assertEqual(status, 200)
        self.assertIn("tasks", data)
        self.assertGreater(data.get("count", 0), 0)

    def test_03_create_task(self):
        new_task = {
            "title": "Automated Test Task",
            "description": "Created by unittest suite",
            "status": "todo",
            "priority": "high"
        }
        status, data, _, _ = self._request("/api/tasks", method="POST", data=new_task)
        self.assertEqual(status, 201)
        self.assertEqual(data.get("title"), new_task["title"])
        self.assertEqual(data.get("status"), "todo")
        self.assertIn("id", data)
        self.__class__.created_id = data["id"]

    def test_04_get_single_task(self):
        task_id = self.__class__.created_id
        status, data, _, _ = self._request(f"/api/tasks/{task_id}")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("id"), task_id)
        self.assertEqual(data.get("title"), "Automated Test Task")

    def test_05_update_task(self):
        task_id = self.__class__.created_id
        update_data = {
            "title": "Updated Test Task",
            "status": "in_progress",
            "priority": "low"
        }
        status, data, _, _ = self._request(f"/api/tasks/{task_id}", method="PUT", data=update_data)
        self.assertEqual(status, 200)
        self.assertEqual(data.get("title"), "Updated Test Task")
        self.assertEqual(data.get("status"), "in_progress")
        self.assertEqual(data.get("priority"), "low")

    def test_06_stats(self):
        status, data, _, _ = self._request("/api/stats")
        self.assertEqual(status, 200)
        self.assertIn("total", data)
        self.assertIn("todo", data)
        self.assertIn("in_progress", data)
        self.assertIn("done", data)

    def test_07_delete_task(self):
        task_id = self.__class__.created_id
        status, data, _, _ = self._request(f"/api/tasks/{task_id}", method="DELETE")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("deleted"), task_id)

        # Verify 404 after deletion
        status404, _, _, _ = self._request(f"/api/tasks/{task_id}")
        self.assertEqual(status404, 404)

    def test_08_serve_frontend_index(self):
        status, _, body, content_type = self._request("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn("<title>Scion Task Board Demo</title>", body)

    def test_09_serve_frontend_css(self):
        status, _, body, content_type = self._request("/style.css")
        self.assertEqual(status, 200)
        self.assertIn("text/css", content_type)
        self.assertIn("--bg-primary", body)

    def test_10_serve_frontend_js(self):
        status, _, body, content_type = self._request("/app.js")
        self.assertEqual(status, 200)
        self.assertTrue("javascript" in content_type or "octet-stream" in content_type)
        self.assertIn("loadTasks", body)


if __name__ == "__main__":
    unittest.main()
