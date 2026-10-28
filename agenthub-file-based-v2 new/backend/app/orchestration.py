import threading,time,uuid
from datetime import datetime,timezone
from pathlib import Path
from .config import SKILLS,WORKFLOWS,SCHEDULES,MEMORY,TIMEOUT
from .store import read,write,listing
from .agents import agents
from .runner import create_run,get_run
_sched_lock=threading.Lock();_sched_started=False
def now():return datetime.now(timezone.utc).isoformat()
def safe(s):return ''.join(c for c in s if c.isalnum() or c in '-_')[:80]
def skills():return [{'name':p.stem,'content':p.read_text(encoding='utf8')} for p in SKILLS.glob('*.md')]
def save_skill(name,content):
 n=safe(name)
 if not n:raise ValueError('Name must contain letters/numbers')
 (SKILLS/f'{n}.md').write_text(content,encoding='utf8');return {'name':n,'saved':True}
def workflows():return [x for x in listing(WORKFLOWS) if 'steps' in x and 'workflow_id' not in x]
def workflow(wid):return read(WORKFLOWS/f'{safe(wid)}.json')
def save_workflow(name,steps):
 n=safe(name);valid={x['id'] for x in agents()}
 if not n:raise ValueError('Invalid workflow name')
 if not steps or len(steps)>12:raise ValueError('Workflow requires 1-12 steps')
 out=[]
 for i,s in enumerate(steps):
  if s['agent'] not in valid:raise ValueError(f'Unknown agent in step {i+1}')
  p=s['prompt']
  if not p.strip() or len(p)>12000:raise ValueError(f'Invalid prompt in step {i+1}')
  out.append({'agent':s['agent'],'prompt':p.strip()})
 rec={'id':n,'name':n,'steps':out,'created_at':now(),'updated_at':now()};write(WORKFLOWS/f'{n}.json',rec);return rec
def executions():return [x for x in listing(WORKFLOWS) if 'workflow_id' in x]
def run_workflow(wid):
 wf=workflow(wid)
 if not wf or 'steps' not in wf:raise ValueError('Workflow not found')
 eid=str(uuid.uuid4());rec={'id':eid,'workflow_id':wid,'name':wf['name'],'status':'running','current_step':0,'steps':[],'created_at':now(),'finished_at':None,'error':None};write(WORKFLOWS/f'execution-{eid}.json',rec)
 threading.Thread(target=_execute,args=(eid,wf),daemon=True).start();return rec
def _execute(eid,wf):
 path=WORKFLOWS/f'execution-{eid}.json';rec=read(path);previous=''
 try:
  for i,s in enumerate(wf['steps'],1):
   run=create_run(s['agent'],s['prompt'].replace('{{previous_output}}',previous[-12000:]),f'workflow-{eid}-{i}')
   step={'step':i,'agent':s['agent'],'run_id':run['id'],'status':'queued'};rec['current_step']=i;rec['steps'].append(step);write(path,rec)
   deadline=time.time()+TIMEOUT+60
   while time.time()<deadline:
    latest=get_run(run['id'])
    if latest and latest.get('status') not in ('queued','running'):break
    time.sleep(1)
   else:raise TimeoutError(f'Workflow step {i} timed out')
   latest=get_run(run['id']);step['status']=latest['status']
   if latest['status']!='completed':raise RuntimeError(latest.get('error') or f"Step {i}: {latest['status']}")
   lp=Path(latest['log_path']);previous=lp.read_text(encoding='utf8',errors='replace')[-12000:] if lp.exists() else '';write(path,rec)
  rec.update(status='completed',finished_at=now());write(path,rec)
 except Exception as e:rec.update(status='failed',error=f'{type(e).__name__}: {e}',finished_at=now());write(path,rec)
def schedules():return listing(SCHEDULES)
def save_schedule(name,wid,minutes,enabled=True):
 n=safe(name)
 if not n:raise ValueError('Invalid schedule name')
 if minutes<5 or minutes>10080:raise ValueError('Interval must be 5 to 10080 minutes')
 if not workflow(wid):raise ValueError('Workflow not found')
 rec={'id':n,'name':n,'workflow_id':wid,'interval_minutes':minutes,'enabled':enabled,'next_run_at':now(),'created_at':now(),'updated_at':now()};write(SCHEDULES/f'{n}.json',rec);return rec
def toggle_schedule(sid,enabled):
 p=SCHEDULES/f'{safe(sid)}.json';r=read(p)
 if not r:return None
 r.update(enabled=enabled,updated_at=now());write(p,r);return r
def _scheduler():
 while True:
  current=datetime.now(timezone.utc)
  for s in schedules():
   if not s.get('enabled'):continue
   try:
    due=datetime.fromisoformat(s['next_run_at'])
    if due.tzinfo is None:due=due.replace(tzinfo=timezone.utc)
    if due<=current:
     run_workflow(s['workflow_id']);s['next_run_at']=datetime.fromtimestamp(current.timestamp()+s['interval_minutes']*60,timezone.utc).isoformat();s['updated_at']=now();write(SCHEDULES/f"{s['id']}.json",s)
   except Exception:pass
  time.sleep(15)
def start_scheduler():
 global _sched_started
 with _sched_lock:
  if not _sched_started:_sched_started=True;threading.Thread(target=_scheduler,daemon=True).start()
