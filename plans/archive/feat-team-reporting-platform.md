# ARS Team Reporting Platform — Improvement Plan

## Problem Statement

The ARS pipeline is currently a single-user tool hardcoded to one developer's OneDrive paths. To serve the full CSM team, it needs:
- Centralized path configuration (no hardcoded OneDrive paths)
- Shared deployment so multiple CSMs can run reports simultaneously
- Role-based views (CSM sees their clients, manager sees all)
- Team-friendly UX (notifications, progress tracking, history)

---

## Phase 1: Eliminate Hardcoded Paths (Foundation)

**Goal:** Every path resolves from `ars_config.py` so the app works on any machine.

### Files with hardcoded paths to fix

| File | Line(s) | Current Hardcoded Path | Fix |
|------|---------|----------------------|-----|
| `pipeline.py` | ~260-263 | `OneDrive/.../Presentations/...` | Use `ars_config.PRESENTATIONS_PATH` and `ars_config.ARCHIVE_PATH` |
| `run_tracker.py` | ~17-19 | `OneDrive/.../run_tracker.json` | Use `ars_config.TRACKER_PATH` |
| `deck_builder.py` | ~145 | `OneDrive/.../Template12.25.pptx` | Use `ars_config.TEMPLATE_PATH` |
| `folder_watcher.py` | ~30-32 | `OneDrive/.../Ready for Analysis` | Use `ars_config.WATCH_ROOT` |
| `folder_watcher.py` | ~209 | `M:\ARS\test-Reports` | Use `ars_config.TEST_REPORTS_DIR` |

### How it works

`ars_config.py` already has the right constants defined. Each file just needs its hardcoded string replaced with the import. The resolution chain (env var > toml > default) means:
- On the shared Windows server: defaults to `M:\ARS Reports`
- On a dev Mac: `ars_config.toml` overrides to local paths
- In CI/testing: `ARS_BASE` env var overrides everything

### Acceptance criteria
- [ ] Zero hardcoded OneDrive paths remain in the codebase
- [ ] `grep -r "OneDrive" *.py` returns nothing
- [ ] App runs on a clean Windows machine with only `M:` drive access
- [ ] Dev override via `ars_config.toml` still works on Mac

---

## Phase 2: Shared Deployment on File Server

**Goal:** Run the Streamlit app as a Windows Service accessible to the team at `http://fileserver:8501`.

### Deployment approach

1. **Install Python + dependencies** on the Windows file server (or a VM with M: drive access)
2. **Use NSSM (Non-Sucking Service Manager)** to run Streamlit as a Windows Service:
   ```
   nssm install ARS-Pipeline "C:\Python311\python.exe" "-m" "streamlit" "run" "app.py" "--server.port=8501" "--server.address=0.0.0.0"
   nssm set ARS-Pipeline AppDirectory "M:\ARS\Scripts\ars_analysis-jupyter"
   nssm set ARS-Pipeline Start SERVICE_AUTO_START
   ```
3. **Firewall rule** to allow port 8501 from the internal network
4. **Auto-restart** on crash (NSSM handles this by default)

### Streamlit server config (`.streamlit/config.toml`)

```toml
[server]
port = 8501
address = "0.0.0.0"
maxUploadSize = 200       # MB, for large ODD files
enableXsrfProtection = true

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
```

### Acceptance criteria
- [ ] App accessible at `http://<server>:8501` from any team machine
- [ ] Service auto-starts on server reboot
- [ ] Service auto-restarts on crash
- [ ] M: drive paths resolve correctly from the service context

---

## Phase 3: User Identity + Authentication

**Goal:** Know who is running reports. Gate access to authorized CSMs.

### Approach: `streamlit-authenticator`

Lightweight YAML-based auth — no database required.

```yaml
# .streamlit/credentials.yaml
credentials:
  usernames:
    jgilmore:
      name: James Gilmore
      password: $2b$12$...  # bcrypt hash
      role: admin
    gmiller:
      name: Gregg Miller
      password: $2b$12$...
      role: csm
    aburgard:
      name: A Burgard
      password: $2b$12$...
      role: csm
```

### What user identity enables
- **Run history**: "Gregg ran 1453 on Feb 3" instead of anonymous entries
- **CSM auto-filter**: Gregg logs in and sees only his clients by default
- **Audit trail**: Who ran what, when, from where
- **Role-based views**: Admin sees everything, CSM sees their portfolio

### CSM-to-client mapping

Add a `csm_assignments` section to the config:
```json
{
  "csm_assignments": {
    "gmiller": ["1147", "1453", "1776"],
    "aburgard": ["2001", "2045"],
    "jberkowitz": ["3010", "3022"]
  }
}
```

This maps login usernames to client IDs so the app can auto-filter.

### Acceptance criteria
- [ ] Login screen appears before any app content
- [ ] `st.session_state['username']` and `st.session_state['role']` available everywhere
- [ ] CSMs see only their clients by default (with option to see all)
- [ ] Admins see all clients and all CSMs

---

## Phase 4: Multi-Page App with Role-Based Views

**Goal:** Replace the single-page app with a tabbed/multi-page layout.

### Page structure (using `st.navigation` + `st.Page`)

```
ARS Pipeline
  |-- Run Reports        (all users)
  |-- My History          (CSM: their runs; Admin: all runs)
  |-- Client Config       (admin only)
  |-- Dashboard           (admin only — summary stats)
```

### Run Reports page improvements
- CSM login auto-selects their clients
- Batch select: "Run all my pending clients"
- Progress bar per client during batch run
- Completion summary with pass/fail per client

### My History page
- Table of past runs: client, date, status, who ran it, duration
- Click to view executive report
- Download links for Excel + PPTX outputs
- Filter by date range, client, status

### Client Config page (admin only)
- View/edit `clients_config.json` through the UI
- Add new client wizard
- Validate config on save (catch JSON errors before they cause runtime failures)
- Show which clients are missing ICRate, NSF_OD_Fee, BranchMapping

### Dashboard page (admin only)
- How many clients processed this month vs total
- Which CSMs have completed their reports
- Average processing time trends
- Error rate and common failure reasons

### Acceptance criteria
- [ ] Navigation works with `st.navigation` (Streamlit 1.36+)
- [ ] Role-based page visibility
- [ ] Each page is a separate `.py` file in a `pages/` folder
- [ ] Shared state via `st.session_state`

---

## Phase 5: Enhanced Team Features

### 5A. SQLite Run Tracker

Replace `run_tracker.json` with SQLite for concurrent multi-user access.

```sql
CREATE TABLE runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL,
    client_name TEXT,
    month TEXT NOT NULL,
    username TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'running',  -- running | completed | failed
    error_message TEXT,
    duration_seconds REAL,
    slides_generated INTEGER,
    output_path TEXT
);
```

Benefits over JSON:
- No file-locking issues with concurrent users
- Query history efficiently
- Survives partial writes (ACID)

### 5B. Teams / Email Notifications

When a report completes or fails, notify the CSM:

```python
import requests

def notify_teams(webhook_url: str, client_id: str, status: str, username: str):
    card = {
        "@type": "MessageCard",
        "summary": f"ARS Report: {client_id}",
        "sections": [{
            "activityTitle": f"Report {status}: {client_id}",
            "activitySubtitle": f"By {username}",
            "facts": [
                {"name": "Status", "value": status},
                {"name": "Client", "value": client_id},
            ]
        }]
    }
    requests.post(webhook_url, json=card)
```

### 5C. Background Processing Queue

For batch runs, use a simple queue so the UI stays responsive:

- User selects 5 clients and clicks "Run All"
- Each job goes into a queue (SQLite table or `queue.Queue`)
- A background thread processes one at a time
- UI polls for status updates via `st.session_state` + `st.rerun()`

### 5D. Config File Locking

For concurrent config edits on a network drive:

```python
from filelock import FileLock

lock = FileLock(str(CONFIG_PATH) + ".lock", timeout=10)
with lock:
    cfg = json.loads(CONFIG_PATH.read_text())
    cfg[client_id] = new_entry
    CONFIG_PATH.write_text(json.dumps(cfg, indent=4))
```

### Acceptance criteria
- [ ] SQLite tracker works with multiple concurrent users
- [ ] Teams notification fires on report completion
- [ ] Batch runs don't freeze the UI
- [ ] Config edits are safe under concurrent access

---

## Implementation Order

```
Phase 1 (hardcoded paths)     ~1 session    ← do first, unblocks everything
Phase 2 (Windows Service)     ~1 session    ← team can start using it
Phase 3 (authentication)      ~1 session    ← know who is who
Phase 4 (multi-page app)      ~2 sessions   ← role-based UX
Phase 5 (enhanced features)   ~2-3 sessions ← polish and power features
```

Phases 1-2 deliver immediate value: the team can use the tool from their desks. Phases 3-5 add progressively more team-friendly features.

---

## Risk / Considerations

| Risk | Mitigation |
|------|-----------|
| M: drive latency for large ODD files | Cache reads with `st.cache_data`; process locally if needed |
| Service crashes mid-report | NSSM auto-restart + SQLite tracker preserves state |
| Config JSON corruption | File locking (Phase 5D) + validation UI (Phase 4) |
| Streamlit concurrent user limits | Single-threaded by default; use `--server.maxMessageSize` and test with 3-4 concurrent users |
| CSM assignment changes | Admin UI to reassign clients without editing JSON |
