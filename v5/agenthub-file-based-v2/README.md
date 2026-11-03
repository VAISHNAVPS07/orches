# AgentHub — Local-first multi-agent workspace

AgentHub is a local web control plane inspired by the workflows and feature set of [Agentic OS](https://github.com/modimihir07/agentic-os), adapted to your requirements: **Hermes + OpenCode + Claude Code + Codex**, local files only, and no database.

It is an independent implementation, not a fork or a pixel-for-pixel copy. The reference project currently documents a FastAPI dashboard, multi-agent routing, skills, persistent memory, scheduler, task board, audit/cost/health features, backups and chat attachments. AgentHub implements the core local workspace and keeps its data in ordinary files.

## Included in this rebuild

- Chat-first web UI with conversation history, local attachments and agent selection.
- Automatic task routing (keyword-based recommendation) plus manual agent selection.
- Agent fleet availability checks against the backend process PATH.
- Four configurable CLI adapters: Hermes, OpenCode, Claude Code and Codex.
- Operations workspace: run history/logs, stop owned runs, task board, Markdown skills, sequential workflows and interval schedules.
- File-based memory notes with search across memory and skills Markdown.
- Dashboard overview with agent, conversation, run, task, skill, workflow and schedule counts.
- PDF, TXT, Markdown, CSV, XLSX, DOCX and JSON uploads stored under `data/uploads/`.
- Atomic JSON writes, per-run workspaces, run logs and restart recovery markers.

## Architecture

```text
React + Vite dashboard
       | HTTP API
FastAPI orchestration layer
       |-- smart router
       |-- agent CLI adapters (Hermes / OpenCode / Claude Code / Codex)
       |-- chat, runs, tasks, skills, workflows, schedules
       |-- file uploads and Markdown memory search
       |
Local filesystem (JSON + Markdown + uploaded originals + logs)
```

No SQL/NoSQL database, hosted service, or vector database is used. JSON files are the source of truth. Schedules execute only while the backend is running. The router is deliberately transparent and keyword-based; it does not claim to be an LLM classifier.

## Run on Ubuntu / WSL

Use the same Ubuntu/WSL account for the backend that has the agent CLIs installed. If Hermes is installed in Ubuntu, do not run the backend from Windows PowerShell because Windows will not see the WSL `hermes` executable.

Backend terminal:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend terminal (Node.js 22 LTS recommended):

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL, typically `http://127.0.0.1:5173`.

## Configure agent CLIs

Edit `config/agents.json`. The default adapters are:

| Agent | Executable | Default invocation |
|---|---|---|
| Hermes | `hermes` | `hermes chat -q "prompt"` |
| OpenCode | `opencode` | `opencode run "prompt"` |
| Claude Code | `claude` | `claude -p "prompt"` |
| Codex | `codex` | `codex exec "prompt"` |

Check each installed CLI's actual syntax with its `--help` output. CLI flags and authentication vary by version. Update the corresponding `command_template` if needed. Keep API keys in each CLI's normal credential store or environment, never in prompts or committed config.

The dashboard reports whether an executable is found in the backend PATH. An installed CLI is not necessarily authenticated or licensed; availability only confirms that the executable can be located.

## Smart routing

Choose **Auto route** in chat to use the built-in transparent keyword router. Current defaults:

- Memory, scheduling, reminders, and skills → Hermes
- Coding, debugging, terminal, Git, and deployment → OpenCode
- Research, comparison, and analysis → Claude Code
- Codex remains available for manual selection

These are defaults, not hard restrictions. You can always choose an agent manually. Edit `/api/router/suggest` in `backend/app/main.py` to tune the routing rules.

## File uploads

Drop files into the chat upload area or use Browse files. Uploaded files stay under `data/uploads/`; select them in Manage files to include extracted text in the next prompt. Maximum size is 10 MB per file. Scanned/image-only PDFs require OCR, which is not bundled. Spreadsheet data is converted to text before it is passed to the agent.

## File storage map

- `data/conversations/*.json` — conversations and messages
- `data/runs/*.json` — run state and metadata
- `data/tasks/*.json` — task board items
- `data/memory/*.md` — persistent notes
- `data/workflows/*.json` — sequential workflows
- `data/schedules/*.json` — recurring schedules
- `data/uploads/` — original uploaded files and extracted text metadata
- `logs/*.log` — CLI output
- `workspaces/<run-id>/` — per-run working directories
- `skills/*.md` — executable skill instructions

Back up the project folder (or at least these data folders) while the backend is stopped. Do not delete `data/` when updating application code.

## API additions

- `GET /api/stats` — dashboard counters
- `POST /api/router/suggest` — suggest an agent for a prompt
- `GET /api/memory/search?q=...` — search Markdown memory and skills
- Existing chat, file, run, task, skill, workflow and schedule endpoints remain available.

## Important boundaries

This is a local development workspace, not a hardened corporate multi-user deployment. Keep it bound to localhost. Before exposing it to a LAN or the internet, add authentication, role-based access, CSRF protections, audit retention, secret redaction, quotas, secure file scanning and a sandbox policy for CLI execution. Agent CLIs can execute powerful local actions. Review each CLI's permissions and working-directory behavior.

This rebuild was syntax-checked on the Python backend. The frontend dependency install/build and live agent CLI integrations still need to be verified on your Windows/WSL machine because the CLIs and your authentication are environment-specific.
