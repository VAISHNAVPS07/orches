# AgentHub v2 — local-first agent workspace

A starter for managing installed CLI agents with JSON/Markdown files only. No database server required.

## Features
- Chat-first React web app with persistent, file-backed conversations and follow-up context
- Operations dashboard for agents, runs/logs, tasks, skills, workflows, and schedules
- Hermes, OpenCode, Claude Code, and Codex adapters configured in `config/agents.json`
- Each run gets a unique working directory and log
- Stop targets only the process group AgentHub started; no `pkill`/`killall`
- Sequential workflows can pass output using `{{previous_output}}`
- Recurring schedules saved in JSON (backend must remain running)
- Markdown skills and notes

## Run on Ubuntu

Terminal 1:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:
```bash
cd frontend
npm install
npm run dev
```
Open the local URL printed by Vite, typically `http://127.0.0.1:5173`.

## Verify Hermes first
Run in the same Ubuntu account/environment used to launch backend:
```bash
command -v hermes
hermes --help
hermes chat --help
```
The default template uses `hermes chat -q "prompt"`; if your installed version differs, edit the Hermes `command_template` in `config/agents.json`. Keep credentials in the normal Hermes credential store/environment; never paste keys into prompts.

## Chat usage
1. Start both the backend and frontend using the commands above.
2. Open the Vite URL and use the Chat page to start a conversation.
3. Choose an installed agent, type a message, and press Enter (Shift+Enter inserts a newline).
4. Follow-up messages include recent conversation history. Conversations are saved as JSON under `data/conversations/`.
5. Use **Operations & workflows** in the left sidebar to access run history, tasks, skills, workflows, and schedules.

The backend starts a new configured CLI process for each reply and passes recent chat history as prompt context. This is not the same as attaching to a pre-existing interactive terminal session; provider-specific session persistence is not currently used.

## Storage
`data/conversations`, `data/runs`, `data/tasks`, `data/memory`, `data/workflows`, `data/schedules`, `logs`, `workspaces` and `skills/` contain ordinary files. Back up by copying the project directory.

## Important limitations
- This is a local development starter, not production-ready corporate software.
- Keep it bound to localhost. Before network/team exposure, add authentication, role-based access, audit logging, secret redaction, quotas, and sandboxing/security review.
- The adapter starts a new CLI process; it does not attach to an existing interactive terminal session. Process isolation reduces accidental interference but cannot guarantee concurrent Hermes sessions are supported by every Hermes build. Test concurrent CLI invocations manually.
- Schedules run only while the backend process is running. Only one backend instance should run against the same file directories.
- CLI flags and output behavior may vary by installed version.
