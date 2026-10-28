from pathlib import Path
from fastapi import FastAPI,HTTPException,UploadFile,File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from .config import RUNS,TASKS,MEMORY
from .store import read,write,listing
from .agents import agents
from .runner import create_run,get_run,runs,stop,recover,now
from .orchestration import skills,save_skill,workflows,save_workflow,run_workflow,executions,schedules,save_schedule,toggle_schedule,start_scheduler
from .chat import list_conversations, get_conversation, create_conversation, send_message
from .files import list_files, get_file, save_upload, delete_file
import uuid
app=FastAPI(title='AgentHub Local API',version='2.0')
app.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:5173','http://localhost:5173'],allow_credentials=False,allow_methods=['GET','POST','PUT','DELETE'],allow_headers=['Content-Type'])
class RunIn(BaseModel):agent:str=Field(min_length=1,max_length=40);prompt:str=Field(min_length=1,max_length=20000);workspace:str='default'
class TaskIn(BaseModel):title:str=Field(min_length=1,max_length=200);description:str='';status:str=Field(default='todo',pattern='^(todo|in_progress|done)$')
class SkillIn(BaseModel):name:str;content:str=Field(min_length=1,max_length=20000)
class Step(BaseModel):agent:str;prompt:str=Field(min_length=1,max_length=12000)
class WorkflowIn(BaseModel):name:str;steps:list[Step]=Field(min_length=1,max_length=12)
class ScheduleIn(BaseModel):name:str;workflow_id:str;interval_minutes:int=Field(ge=5,le=10080);enabled:bool=True
class Toggle(BaseModel):enabled:bool
class ConversationIn(BaseModel):agent:str=Field(default='hermes',min_length=1,max_length=40)
class MessageIn(BaseModel):agent:str=Field(default='hermes',min_length=1,max_length=40);content:str=Field(min_length=1,max_length=20000);file_ids:list[str]=Field(default_factory=list,max_length=10)
@app.on_event('startup')
def startup():
 recover();start_scheduler()
@app.get('/api/health')
def health():return {'status':'ok','storage':'local files'}
@app.get('/api/agents')
def get_agents():return agents()

@app.get('/api/files')
def uploaded_files():return list_files()
@app.post('/api/files')
async def upload_file(file:UploadFile=File(...)):
 try:return await save_upload(file)
 except ValueError as e:raise HTTPException(400,str(e))
@app.get('/api/files/{file_id}')
def uploaded_file_detail(file_id):
 item=get_file(file_id)
 if not item:raise HTTPException(404,'File not found')
 return {k:item.get(k) for k in ('id','name','extension','size','uploaded_at','characters','content')}
@app.delete('/api/files/{file_id}')
def remove_uploaded_file(file_id):
 if not delete_file(file_id):raise HTTPException(404,'File not found')
 return {'deleted':True,'id':file_id}

@app.get('/api/conversations')
def get_conversations():return list_conversations()
@app.post('/api/conversations')
def new_conversation(x:ConversationIn):
 if x.agent not in {a['id'] for a in agents()}:raise HTTPException(400,'Unknown agent')
 return create_conversation(x.agent)
@app.get('/api/conversations/{cid}')
def conversation_detail(cid):
 c=get_conversation(cid)
 if not c:raise HTTPException(404,'Conversation not found')
 return c
@app.post('/api/conversations/{cid}/messages')
def conversation_message(cid,x:MessageIn):
 if x.agent not in {a['id'] for a in agents()}:raise HTTPException(400,'Unknown agent')
 try:
  file_context=[]
  remaining=80000
  for fid in x.file_ids:
   item=get_file(fid)
   if not item:raise ValueError(f'Uploaded file not found: {fid}')
   extracted=item.get('content','')[:remaining]
   file_context.append({'name':item['name'],'content':extracted})
   remaining-=len(extracted)
   if remaining<=0:break
  return send_message(cid,x.agent,x.content,file_context)
 except LookupError as e:raise HTTPException(404,str(e))
 except (ValueError,RuntimeError) as e:raise HTTPException(400,str(e))
@app.post('/api/runs')
def launch(x:RunIn):
 if x.agent not in {a['id'] for a in agents()}:raise HTTPException(400,'Unknown agent')
 return create_run(x.agent,x.prompt,x.workspace)
@app.get('/api/runs')
def get_runs(limit:int=50):return runs(limit)
@app.get('/api/runs/{rid}')
def detail(rid):
 x=get_run(rid)
 if not x:raise HTTPException(404,'Run not found')
 return x
@app.post('/api/runs/{rid}/stop')
def stop_endpoint(rid):
 x=get_run(rid)
 if not x:raise HTTPException(404,'Run not found')
 if not stop(rid):raise HTTPException(409,'Run is not owned by this running service; refusing to signal unknown process')
 return {'status':'stopped','run_id':rid}
@app.get('/api/runs/{rid}/logs')
def logs(rid):
 x=get_run(rid)
 if not x:raise HTTPException(404,'Run not found')
 p=Path(x['log_path'])
 if not p.exists():return {'logs':''}
 with p.open('rb') as f:f.seek(max(0,p.stat().st_size-100000));data=f.read().decode('utf8',errors='replace')
 return {'logs':data}
@app.get('/api/tasks')
def get_tasks():return listing(TASKS)
@app.post('/api/tasks')
def add_task(x:TaskIn):
 tid=str(uuid.uuid4());r={'id':tid,**x.model_dump(),'created_at':now(),'updated_at':now()};write(TASKS/f'{tid}.json',r);return r
@app.put('/api/tasks/{tid}')
def edit_task(tid,x:TaskIn):
 p=TASKS/f'{tid}.json';r=read(p)
 if not r:raise HTTPException(404,'Task not found')
 r.update(x.model_dump(),updated_at=now());write(p,r);return r
@app.get('/api/memory')
def get_memory():return [{'name':p.stem,'content':p.read_text(encoding='utf8')} for p in MEMORY.glob('*.md')]
@app.post('/api/memory')
def put_memory(x:SkillIn):
 n=''.join(c for c in x.name if c.isalnum() or c in '-_')[:80]
 if not n:raise HTTPException(400,'Invalid name')
 (MEMORY/f'{n}.md').write_text(x.content,encoding='utf8');return {'name':n,'saved':True}
@app.get('/api/skills')
def get_skills():return skills()
@app.post('/api/skills')
def put_skill(x:SkillIn):
 try:return save_skill(x.name,x.content)
 except ValueError as e:raise HTTPException(400,str(e))
@app.get('/api/workflows')
def get_workflows():return workflows()
@app.post('/api/workflows')
def put_workflow(x:WorkflowIn):
 try:return save_workflow(x.name,[s.model_dump() for s in x.steps])
 except ValueError as e:raise HTTPException(400,str(e))
@app.post('/api/workflows/{wid}/run')
def launch_workflow(wid):
 try:return run_workflow(wid)
 except ValueError as e:raise HTTPException(400,str(e))
@app.get('/api/workflow-executions')
def get_executions():return executions()
@app.get('/api/schedules')
def get_schedules():return schedules()
@app.post('/api/schedules')
def put_schedule(x:ScheduleIn):
 try:return save_schedule(x.name,x.workflow_id,x.interval_minutes,x.enabled)
 except ValueError as e:raise HTTPException(400,str(e))
@app.put('/api/schedules/{sid}')
def edit_schedule(sid,x:Toggle):
 r=toggle_schedule(sid,x.enabled)
 if not r:raise HTTPException(404,'Schedule not found')
 return r
