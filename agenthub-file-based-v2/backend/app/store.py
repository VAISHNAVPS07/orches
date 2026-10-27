import json, os, tempfile, threading
from pathlib import Path
_lock = threading.RLock()
def read(path, default=None):
    try: return json.loads(Path(path).read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError, OSError): return default
def write(path, data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(data,f,ensure_ascii=False,indent=2); f.flush(); os.fsync(f.fileno())
        with _lock: os.replace(tmp,path)
    finally:
        try: os.unlink(tmp)
        except FileNotFoundError: pass
def listing(directory, limit=200):
    out=[]
    for p in sorted(Path(directory).glob('*.json'),key=lambda x:x.stat().st_mtime,reverse=True):
        obj=read(p)
        if isinstance(obj,dict): out.append(obj)
        if len(out)>=limit: break
    return out
