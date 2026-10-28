import os, signal, subprocess, threading, uuid
from datetime import datetime,timezone
from pathlib import Path
from .agents import command
from .config import RUNS,LOGS,WORKSPACES,MAX_CONCURRENT,TIMEOUT
from .store import read,write,listing
_lock=threading.RLock(); _processes={}; _slots=threading.BoundedSemaphore(MAX_CONCURRENT)
def now(): return datetime.now(timezone.utc).isoformat()
def get_run(rid): return read(RUNS/f'{rid}.json')
def patch(rid,**fields):
    with _lock:
        x=get_run(rid)
        if not x:return None
        x.update(fields);x['updated_at']=now();write(RUNS/f'{rid}.json',x);return x
def create_run(agent,prompt,label='default'):
    rid=str(uuid.uuid4()); wd=WORKSPACES/rid;wd.mkdir(parents=True)
    rec={'id':rid,'agent':agent,'prompt':prompt,'workspace':label,'status':'queued','pid':None,'exit_code':None,'error':None,'created_at':now(),'updated_at':now(),'started_at':None,'finished_at':None,'log_path':str(LOGS/f'{rid}.log'),'workdir':str(wd)}
    write(RUNS/f'{rid}.json',rec);threading.Thread(target=_launch,args=(rid,),daemon=True).start();return rec
def _kill_owned(proc):
    try: os.killpg(proc.pid,signal.SIGTERM)
    except (ProcessLookupError,PermissionError): return
    try: proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try: os.killpg(proc.pid,signal.SIGKILL)
        except (ProcessLookupError,PermissionError): pass
def _launch(rid):
    if not _slots.acquire(False): patch(rid,status='failed',error='Concurrency limit reached',finished_at=now());return
    proc=None
    try:
        r=get_run(rid);argv=command(r['agent'],r['prompt'])
        with open(r['log_path'],'ab',buffering=0) as log:
            proc=subprocess.Popen(argv,cwd=r['workdir'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=os.environ.copy())
        with _lock:_processes[rid]=proc
        patch(rid,status='running',pid=proc.pid,started_at=now())
        try:
            code=proc.wait(timeout=TIMEOUT);patch(rid,status='completed' if code==0 else 'failed',exit_code=code,finished_at=now())
        except subprocess.TimeoutExpired:
            _kill_owned(proc)
            try:proc.wait(timeout=8)
            except subprocess.TimeoutExpired:pass
            patch(rid,status='timed_out',exit_code=proc.poll(),error=f'Exceeded {TIMEOUT}s timeout',finished_at=now())
    except Exception as e: patch(rid,status='failed',error=f'{type(e).__name__}: {e}',finished_at=now())
    finally:
        with _lock:_processes.pop(rid,None)
        _slots.release()
def stop(rid):
    with _lock:p=_processes.get(rid)
    if p is None:return False
    _kill_owned(p);patch(rid,status='stopped',exit_code=p.poll(),finished_at=now());return True
def runs(limit=100):return listing(RUNS,min(max(limit,1),200))
def recover():
    for r in listing(RUNS,10000):
        if r.get('status') in ('queued','running'):patch(r['id'],status='interrupted',error='Service restarted; process ownership was not re-established',finished_at=now())
