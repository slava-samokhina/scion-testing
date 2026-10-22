# Scion Task Board Demo Application

A lightweight, full-stack Task Board demo application built with a Python backend and modern vanilla frontend. Designed for Scion agent orchestration demonstrations with live port exposure via `sciontool expose`.

## Architecture & Components

- **Backend (`backend/server.py`)**:
  - Zero-dependency Python server using standard library `http.server` and `sqlite3`.
  - Serves REST API endpoints for full CRUD task management under `/api/tasks`.
  - Computes task metrics under `/api/stats`.
  - Provides health checks at `/health`.
  - Serves static frontend Single Page Application (SPA) assets at `/`.
- **Frontend (`frontend/`)**:
  - `index.html`: Responsive Kanban task board layout with To Do, In Progress, and Completed columns.
  - `style.css`: Clean, dark-mode styling with subtle animations and status badges.
  - `app.js`: Interactive client logic with live polling, task creation/editing modal, status movement, and search/filter.
  - Configured with relative API paths (`api/tasks`) to seamlessly support reverse proxying through Scion Hub.
- **Automated Tests (`tests/test_server.py`)**:
  - Comprehensive unit and integration test suite covering API CRUD, health check, and static file delivery.

## Running Locally

```bash
# Start backend server on port 8000
python3 backend/server.py

# Run test suite
python3 -m unittest tests/test_server.py
```

## Exposing via Scion Tool

```bash
# Register port 8000 with the Scion Hub reverse proxy
sciontool expose 8000 --label demo-task-board

# List exposed ports and view the live Hub proxy URL
sciontool expose --list
```

<!-- codeowners validation: dev PR should not be gated -->
