import os
from pathlib import Path
BASE = Path(__file__).resolve().parents[2]
DATA = Path(os.getenv('AGENTHUB_DATA_ROOT', BASE / 'data')).resolve()
RUNS = DATA / 'runs'; TASKS = DATA / 'tasks'; MEMORY = DATA / 'memory'; CONVERSATIONS = DATA / 'conversations'
WORKFLOWS = DATA / 'workflows'; SCHEDULES = DATA / 'schedules'
LOGS = Path(os.getenv('AGENTHUB_LOG_ROOT', BASE / 'logs')).resolve()
WORKSPACES = Path(os.getenv('AGENTHUB_WORKSPACE_ROOT', BASE / 'workspaces')).resolve()
UPLOADS = DATA / 'uploads'
CONFIG = BASE / 'config'; AGENTS_FILE = CONFIG / 'agents.json'; SKILLS = BASE / 'skills'
MAX_CONCURRENT = int(os.getenv('AGENTHUB_MAX_CONCURRENT_RUNS', '2'))
TIMEOUT = int(os.getenv('AGENTHUB_RUN_TIMEOUT_SECONDS', '3600'))
for d in [RUNS,TASKS,MEMORY,CONVERSATIONS,WORKFLOWS,SCHEDULES,LOGS,WORKSPACES,UPLOADS,CONFIG,SKILLS]: d.mkdir(parents=True,exist_ok=True)
