"""Local file uploads and text extraction for AgentHub."""
from pathlib import Path
from datetime import datetime, timezone
import json, uuid, csv, io
from fastapi import UploadFile, HTTPException
from .config import UPLOADS
from .store import read, write

MAX_BYTES = 10 * 1024 * 1024
ALLOWED = {'.pdf', '.txt', '.md', '.csv', '.xlsx', '.docx', '.json'}


def _metadata_path(file_id: str) -> Path | None:
    try: canonical = str(uuid.UUID(file_id))
    except (ValueError, TypeError, AttributeError): return None
    return UPLOADS / f'{canonical}.json'


def list_files():
    items=[]
    for p in UPLOADS.glob('*.json'):
        item=read(p)
        if item: items.append({k:item.get(k) for k in ('id','name','extension','size','uploaded_at','characters')})
    return sorted(items, key=lambda x:x.get('uploaded_at') or '', reverse=True)


def get_file(file_id: str):
    p=_metadata_path(file_id)
    return read(p) if p else None


def _extract(ext: str, data: bytes) -> str:
    if ext in {'.txt','.md'}:
        return data.decode('utf-8-sig', errors='replace')
    if ext == '.json':
        try: return json.dumps(json.loads(data.decode('utf-8-sig')), ensure_ascii=False, indent=2)
        except Exception as e: raise ValueError(f'Invalid JSON file: {e}')
    if ext == '.csv':
        text=data.decode('utf-8-sig', errors='replace')
        try:
            rows=list(csv.reader(io.StringIO(text)))
            return '\n'.join(' | '.join(cell for cell in row) for row in rows)
        except Exception: return text
    if ext == '.pdf':
        try:
            from pypdf import PdfReader
            reader=PdfReader(io.BytesIO(data))
            return '\n\n'.join(page.extract_text() or '' for page in reader.pages)
        except ImportError: raise ValueError('PDF support is not installed. Run: pip install -r requirements.txt')
        except Exception as e: raise ValueError(f'Could not read PDF: {e}')
    if ext == '.xlsx':
        try:
            from openpyxl import load_workbook
            book=load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            parts=[]
            for sheet in book.worksheets:
                parts.append(f'Sheet: {sheet.title}')
                for row in sheet.iter_rows(values_only=True):
                    values=[str(v) if v is not None else '' for v in row]
                    if any(values): parts.append(' | '.join(values))
            book.close()
            return '\n'.join(parts)
        except ImportError: raise ValueError('XLSX support is not installed. Run: pip install -r requirements.txt')
        except Exception as e: raise ValueError(f'Could not read XLSX: {e}')
    if ext == '.docx':
        try:
            from docx import Document
            doc=Document(io.BytesIO(data))
            parts=[para.text for para in doc.paragraphs if para.text.strip()]
            for table in doc.tables:
                for row in table.rows: parts.append(' | '.join(cell.text for cell in row.cells))
            return '\n'.join(parts)
        except ImportError: raise ValueError('DOCX support is not installed. Run: pip install -r requirements.txt')
        except Exception as e: raise ValueError(f'Could not read DOCX: {e}')
    raise ValueError('Unsupported file type')


async def save_upload(upload: UploadFile):
    name=Path(upload.filename or 'upload').name
    ext=Path(name).suffix.lower()
    if ext not in ALLOWED: raise ValueError('Unsupported file type. Allowed: PDF, TXT, MD, CSV, XLSX, DOCX, JSON.')
    data=await upload.read(MAX_BYTES+1)
    if not data: raise ValueError('The uploaded file is empty.')
    if len(data)>MAX_BYTES: raise ValueError('File exceeds the 10 MB upload limit.')
    content=_extract(ext,data)
    file_id=str(uuid.uuid4())
    # Keep both original bytes and extracted text under a generated ID; never trust the supplied filename as a path.
    original=UPLOADS/f'{file_id}{ext}'
    original.write_bytes(data)
    item={'id':file_id,'name':name,'extension':ext,'size':len(data),'uploaded_at':datetime.now(timezone.utc).isoformat(),'characters':len(content),'content':content,'stored_name':original.name}
    write(UPLOADS/f'{file_id}.json',item)
    return {k:item[k] for k in ('id','name','extension','size','uploaded_at','characters')}


def delete_file(file_id: str):
    p=_metadata_path(file_id)
    item=read(p) if p else None
    if not item: return False
    stored=item.get('stored_name')
    if stored:
        original=UPLOADS/Path(stored).name
        if original.exists(): original.unlink()
    p.unlink(missing_ok=True)
    return True
