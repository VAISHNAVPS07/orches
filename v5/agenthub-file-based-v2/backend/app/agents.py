import shutil
from .config import AGENTS_FILE
from .store import read
DEFAULT=[
 {'id':'hermes','label':'Hermes','executable':'hermes','enabled':True,'command_template':['{executable}','chat','-q','{prompt}']},
 {'id':'opencode','label':'OpenCode','executable':'opencode','enabled':True,'command_template':['{executable}','run','{prompt}']},
 {'id':'claude','label':'Claude Code','executable':'claude','enabled':True,'command_template':['{executable}','-p','{prompt}']},
 {'id':'codex','label':'Codex','executable':'codex','enabled':True,'command_template':['{executable}','exec','{prompt}']},
]
def agents():
    cfg=read(AGENTS_FILE,{'agents':DEFAULT})
    return [{**a,'available':bool(a.get('enabled',True) and shutil.which(a.get('executable','')))} for a in cfg.get('agents',DEFAULT)]
def command(agent_id,prompt):
    a=next((x for x in agents() if x['id']==agent_id),None)
    if not a or not a.get('enabled'): raise ValueError('Agent not configured or enabled')
    exe=a.get('executable','')
    if not shutil.which(exe): raise FileNotFoundError(f'{exe} not found in backend PATH')
    template=a.get('command_template')
    if not isinstance(template,list) or not template: raise ValueError('Invalid command_template')
    repl={'{executable}':exe,'{prompt}':prompt}; argv=[]
    for part in template:
        if part in repl: argv.append(repl[part])
        elif '{' in part or '}' in part: raise ValueError(f'Unsupported placeholder: {part}')
        else: argv.append(part)
    if not argv or argv[0]!=exe: raise ValueError('Template must begin with {executable}')
    return argv
