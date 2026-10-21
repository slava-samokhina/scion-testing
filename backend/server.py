#!/usr/bin/env python3
"""
Scion Task Board Demo - Backend Server
Provides a REST API for task management and serves the frontend SPA.
Zero external dependencies (uses standard library http.server + sqlite3).
"""

import http.server
import json
import mimetypes
import os
import re
import socketserver
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PORT = int(os.environ.get("PORT", 8000))
HOST = os.environ.get("HOST", "0.0.0.0")
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DB_PATH = BASE_DIR / "tasks.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'todo',
            priority TEXT NOT NULL DEFAULT 'medium',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    # Seed initial demo tasks if table is empty
    cursor.execute("SELECT COUNT(*) FROM tasks")
    if cursor.fetchone()[0] == 0:
        now = datetime.now(timezone.utc).isoformat()
        sample_tasks = [
            ("Explore Scion Expose Tool", "Verify port forwarding through Hub proxy endpoint", "done", "high", now, now),
            ("Build Full-Stack Demo App", "Implement clean REST API and modern interactive frontend", "in_progress", "high", now, now),
            ("Test Real-Time Updates", "Add interactive tasks and watch the board update dynamically", "in_progress", "medium", now, now),
            ("Document Orchestration Flow", "Record coordinator state and workflow in scratchpad", "todo", "low", now, now),
            ("Prepare Final Walkthrough", "Summarize test coverage and live proxy URLs", "todo", "medium", now, now),
        ]
        cursor.executemany("""
            INSERT INTO tasks (title, description, status, priority, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_tasks)
    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class TaskRequestHandler(http.server.BaseHTTPRequestHandler):
    server_version = "ScionTaskServer/1.0"

    def log_message(self, format, *args):
        # Format clean log messages
        sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]} - {args[1]} {args[2]}\n")

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(204)

    def _read_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return None

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"

        # Health Check
        if path == "/health":
            self._set_headers(200)
            self.wfile.write(json.dumps({
                "status": "ok",
                "app": "Scion Task Board Demo",
                "version": "1.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }).encode("utf-8"))
            return

        # API: List all tasks
        if path == "/api/tasks":
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks ORDER BY id ASC")
            tasks = [dict(row) for row in cursor.fetchall()]
            conn.close()
            self._set_headers(200)
            self.wfile.write(json.dumps({"tasks": tasks, "count": len(tasks)}).encode("utf-8"))
            return

        # API: Get single task
        match = re.match(r"^/api/tasks/(\d+)$", path)
        if match:
            task_id = int(match.group(1))
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                self._set_headers(200)
                self.wfile.write(json.dumps(dict(row)).encode("utf-8"))
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": f"Task {task_id} not found"}).encode("utf-8"))
            return

        # API: Statistics
        if path == "/api/stats":
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
            counts = dict(cursor.fetchall())
            cursor.execute("SELECT COUNT(*) FROM tasks")
            total = cursor.fetchone()[0]
            conn.close()
            stats = {
                "total": total,
                "todo": counts.get("todo", 0),
                "in_progress": counts.get("in_progress", 0),
                "done": counts.get("done", 0)
            }
            self._set_headers(200)
            self.wfile.write(json.dumps(stats).encode("utf-8"))
            return

        # Serve static frontend files
        self._serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # API: Create Task
        if path == "/api/tasks":
            data = self._read_json_body()
            if data is None:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode("utf-8"))
                return

            title = data.get("title", "").strip()
            if not title:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Title is required"}).encode("utf-8"))
                return

            description = data.get("description", "").strip()
            status = data.get("status", "todo")
            if status not in ("todo", "in_progress", "done"):
                status = "todo"
            priority = data.get("priority", "medium")
            if priority not in ("low", "medium", "high"):
                priority = "medium"

            now = datetime.now(timezone.utc).isoformat()
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (title, description, status, priority, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, description, status, priority, now, now))
            new_id = cursor.lastrowid
            conn.commit()

            cursor.execute("SELECT * FROM tasks WHERE id = ?", (new_id,))
            created_task = dict(cursor.fetchone())
            conn.close()

            self._set_headers(201)
            self.wfile.write(json.dumps(created_task).encode("utf-8"))
            return

        # API: Reset demo data
        if path == "/api/reset":
            init_db()
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "reset", "message": "Demo data reset"}).encode("utf-8"))
            return

        self._set_headers(404)
        self.wfile.write(json.dumps({"error": "Not found"}).encode("utf-8"))

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        match = re.match(r"^/api/tasks/(\d+)$", path)
        if match:
            task_id = int(match.group(1))
            data = self._read_json_body()
            if data is None:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode("utf-8"))
                return

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            existing = cursor.fetchone()
            if not existing:
                conn.close()
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": f"Task {task_id} not found"}).encode("utf-8"))
                return

            title = data.get("title", existing["title"])
            description = data.get("description", existing["description"])
            status = data.get("status", existing["status"])
            priority = data.get("priority", existing["priority"])
            now = datetime.now(timezone.utc).isoformat()

            cursor.execute("""
                UPDATE tasks
                SET title = ?, description = ?, status = ?, priority = ?, updated_at = ?
                WHERE id = ?
            """, (title, description, status, priority, now, task_id))
            conn.commit()

            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            updated_task = dict(cursor.fetchone())
            conn.close()

            self._set_headers(200)
            self.wfile.write(json.dumps(updated_task).encode("utf-8"))
            return

        self._set_headers(404)
        self.wfile.write(json.dumps({"error": "Not found"}).encode("utf-8"))

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        match = re.match(r"^/api/tasks/(\d+)$", path)
        if match:
            task_id = int(match.group(1))
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            if not cursor.fetchone():
                conn.close()
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": f"Task {task_id} not found"}).encode("utf-8"))
                return

            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            conn.close()

            self._set_headers(200)
            self.wfile.write(json.dumps({"deleted": task_id, "status": "ok"}).encode("utf-8"))
            return

        self._set_headers(404)
        self.wfile.write(json.dumps({"error": "Not found"}).encode("utf-8"))

    def _serve_static(self, path):
        if path == "/":
            rel_path = "index.html"
        else:
            rel_path = path.lstrip("/")

        file_path = FRONTEND_DIR / rel_path

        # Security check against path traversal
        try:
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(FRONTEND_DIR.resolve())):
                self._set_headers(403)
                self.wfile.write(b"Forbidden")
                return
        except Exception:
            self._set_headers(404)
            self.wfile.write(b"Not Found")
            return

        # Fallback to index.html for SPA client-side routing
        if not file_path.exists() or file_path.is_dir():
            file_path = FRONTEND_DIR / "index.html"

        if file_path.exists() and file_path.is_file():
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                mime_type = "application/octet-stream"

            with open(file_path, "rb") as f:
                content = f.read()

            self._set_headers(200, content_type=mime_type)
            self.wfile.write(content)
        else:
            self._set_headers(404)
            self.wfile.write(b"File not found")


class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def run_server():
    init_db()
    print(f"Database initialized at {DB_PATH}")
    with ReusableTCPServer((HOST, PORT), TaskRequestHandler) as httpd:
        print(f"Task Board Server listening on http://{HOST}:{PORT}")
        print(f"Serving frontend from {FRONTEND_DIR}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.shutdown()


if __name__ == "__main__":
    run_server()
