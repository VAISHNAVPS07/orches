import {useCallback, useEffect, useRef, useState} from 'react';
import Operations from './Operations';

const API='http://127.0.0.1:8000/api';
type Agent={id:string;label:string;available:boolean};
type Conversation={id:string;title:string;updated_at:string;message_count:number;agent:string};
type Message={id:string;role:'user'|'assistant';content:string;status?:string;agent?:string;created_at:string;run_id?:string};
type Detail={id:string;title:string;agent:string;messages:Message[]};

async function request(path:string, method='GET', body?:unknown){
 const r=await fetch(API+path,{method,headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
 const data=await r.json().catch(()=>({detail:'Invalid response from backend'}));
 if(!r.ok)throw new Error(data.detail||`Request failed (${r.status})`);
 return data;
}

export default function App(){
 const [page,setPage]=useState<'chat'|'operations'>('chat');
 const [agents,setAgents]=useState<Agent[]>([]),[conversations,setConversations]=useState<Conversation[]>([]);
 const [activeId,setActiveId]=useState(''),[detail,setDetail]=useState<Detail|null>(null);
 const [agent,setAgent]=useState('hermes'),[draft,setDraft]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const bottom=useRef<HTMLDivElement>(null);
 const loadConversations=useCallback(async()=>{const rows=await request('/conversations');setConversations(rows);return rows as Conversation[]},[]);
 const loadDetail=useCallback(async(id:string)=>{if(!id)return;const d=await request(`/conversations/${id}`);setDetail(d);setAgent(d.agent||'hermes');return d as Detail},[]);
 useEffect(()=>{let alive=true;(async()=>{try{const [a,c]=await Promise.all([request('/agents'),request('/conversations')]);if(!alive)return;setAgents(a);setConversations(c);if(c.length){setActiveId(c[0].id);setDetail(await request(`/conversations/${c[0].id}`));setAgent(c[0].agent||'hermes')}}catch(e){if(alive)setError(`Cannot connect to AgentHub backend. Start FastAPI on port 8000. ${String(e)}`)}})();return()=>{alive=false}},[]);
 useEffect(()=>{if(!activeId)return;let alive=true;const refresh=async()=>{try{const d=await request(`/conversations/${activeId}`);if(alive){setDetail(d);if(!d.messages?.some((m:Message)=>m.status==='pending'))loadConversations().catch(()=>{})}}catch(e){if(alive)setError(String(e))}};refresh();const timer=window.setInterval(refresh,1600);return()=>{alive=false;window.clearInterval(timer)}},[activeId,loadConversations]);
 useEffect(()=>{bottom.current?.scrollIntoView({behavior:'smooth',block:'end'})},[detail?.messages?.length,detail?.messages?.[detail.messages.length-1]?.content]);
 async function newChat(){try{setError('');const c=await request('/conversations','POST',{agent});await loadConversations();setActiveId(c.id);setDetail(c);setPage('chat')}catch(e){setError(String(e))}}
 async function send(e:React.FormEvent){e.preventDefault();const content=draft.trim();if(!content||busy)return;setBusy(true);setError('');try{let cid=activeId;if(!cid){const c=await request('/conversations','POST',{agent});cid=c.id;setActiveId(cid);setDetail(c)}await request(`/conversations/${cid}/messages`,'POST',{agent,content});setDraft('');await loadConversations();await loadDetail(cid)}catch(e){setError(String(e))}finally{setBusy(false)}}
 const selectedAgent=agents.find(a=>a.id===agent);
 return <div className="app-shell">
  <aside className="sidebar">
   <div className="brand"><div className="brand-mark">A</div><div><b>AgentHub</b><small>LOCAL AGENT WORKSPACE</small></div></div>
   <button className="new-chat" onClick={newChat}><span>＋</span> New chat</button>
   <div className="side-label">RECENT CONVERSATIONS</div>
   <div className="conversation-list">{conversations.map(c=><button key={c.id} className={`conversation-link ${activeId===c.id?'active':''}`} onClick={()=>{setActiveId(c.id);setPage('chat');setError('')}}><span className="conversation-dot">◌</span><span className="conversation-title">{c.title||'New chat'}</span></button>)}{!conversations.length&&<p className="empty-history">Your conversations will appear here.</p>}</div>
   <div className="sidebar-bottom"><div className="local-status"><span className="status-dot"/> Local backend</div><button className={`nav-link ${page==='chat'?'nav-selected':''}`} onClick={()=>setPage('chat')}>◫ <span>Chat</span></button><button className={`nav-link ${page==='operations'?'nav-selected':''}`} onClick={()=>setPage('operations')}>⌘ <span>Operations & workflows</span></button><small>File-based storage · No database</small></div>
  </aside>
  <main className="main-area">
   {page==='operations'?<div className="operations-wrap"><div className="topbar"><div><span className="eyebrow">AGENT MANAGEMENT</span><h1>Operations</h1></div><button className="secondary" onClick={()=>setPage('chat')}>← Back to chat</button></div><Operations/></div>:<>
    <header className="chat-topbar"><div><span className="eyebrow">YOUR AI WORKSPACE</span><h1>{detail?.title||'New conversation'}</h1></div><div className="agent-select-wrap"><span className="online-indicator"/><label htmlFor="chat-agent">Agent</label><select id="chat-agent" value={agent} onChange={e=>setAgent(e.target.value)}>{agents.map(a=><option key={a.id} value={a.id}>{a.label}{a.available?'':' (CLI not found)'}</option>)}</select></div></header>
    {error&&<div className="chat-error">{error}<button onClick={()=>setError('')}>Dismiss</button></div>}
    <section className="chat-stage">
     {!detail?.messages?.length?<div className="welcome"><div className="welcome-orb">✳</div><h2>What can we work on?</h2><p>Ask your agent a question, explore an idea, or get help with a project. Your conversations are saved locally.</p><div className="prompt-suggestions"><button onClick={()=>setDraft('Review my project structure and suggest the highest-impact improvements. Do not modify any files.')}>Review a project <span>↗</span></button><button onClick={()=>setDraft('Help me break a complex task into clear, actionable steps.')}>Plan a task <span>↗</span></button><button onClick={()=>setDraft('Explain how this agent workspace works and what I can automate.')}>Explore AgentHub <span>↗</span></button></div></div>:<div className="messages">{detail.messages.map((m,i)=><div className={`message-row ${m.role==='user'?'from-user':'from-assistant'}`} key={m.id}><div className={`avatar ${m.role==='assistant'?'agent-avatar':'user-avatar'}`}>{m.role==='assistant'?'✳':'You'}</div><div className="message-content"><div className="message-meta"><b>{m.role==='assistant'?(agents.find(a=>a.id===(m.agent||detail.agent))?.label||'Agent'):'You'}</b>{m.role==='assistant'&&m.status==='pending'&&<span className="thinking"><i/> Working…</span>}{m.role==='assistant'&&m.status==='failed'&&<span className="failed-tag">Run failed</span>}</div><div className="message-text">{m.status==='pending'&&!m.content?<div className="typing"><i/><i/><i/></div>:m.content}</div>{m.run_id&&<small className="run-ref">Run {m.run_id.slice(0,8)}</small>}</div></div>)}<div ref={bottom}/></div>}
    </section>
    <div className="composer-area"><form className="composer" onSubmit={send}><textarea value={draft} onChange={e=>setDraft(e.target.value)} placeholder={`Message ${agents.find(a=>a.id===agent)?.label||'your agent'}…`} rows={1} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();(e.currentTarget.form as HTMLFormElement)?.requestSubmit()}}}/><div className="composer-bottom"><span>Enter to send · Shift + Enter for a new line</span><button type="submit" disabled={!draft.trim()||busy||!selectedAgent?.available}>{busy?'Sending…':< >Send <span>↑</span></>}</button></div></form><p className="privacy-note">AgentHub runs your configured local CLI. Verify outputs before acting on them.</p></div>
   </>}
  </main>
 </div>
}
