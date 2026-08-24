import { useMemo, useState } from "react";
import { FileText, MessageSquare, Plus, Search, Trash2, X } from "lucide-react";

export default function ConversationSidebar({ conversations, activeId, documents, onSelect, onNewChat, onDelete, onUpload, onDeleteDocument }) {
  const [search, setSearch] = useState("");
  const [confirmingId, setConfirmingId] = useState(null);
  const filtered = useMemo(() => conversations.filter((c) => (c.title || "New Chat").toLowerCase().includes(search.toLowerCase())), [conversations, search]);

  function deleteChat(event, id) {
    event.stopPropagation();
    if (confirmingId === id) {
      onDelete(id);
      setConfirmingId(null);
    } else {
      setConfirmingId(id);
    }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand-row">
        <div className="sidebar-section-title">Workspace</div>
      </div>
      <button className="new-chat-btn" onClick={onNewChat}><Plus size={17} /> New chat</button>
      <div className="sidebar-search"><Search size={15}/><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search chats" /></div>
      <div className="sidebar-label">Chats</div>
      <div className="conversation-list">
        {filtered.length === 0 && <div className="sidebar-empty">{search ? "No chats match your search" : "Start a new conversation"}</div>}
        {filtered.map((c) => (
          <button key={c.id} className={`conversation-item ${c.id === activeId ? "conversation-item--active" : ""}`} onClick={() => onSelect(c.id)}>
            <MessageSquare size={15} className="conversation-item-icon" />
            <span className="conversation-item-title">{c.title || "New Chat"}</span>
            <span className="conversation-item-delete" onClick={(e) => deleteChat(e, c.id)} title={confirmingId === c.id ? "Click again to delete" : "Delete chat"}>
              {confirmingId === c.id ? <X size={14}/> : <Trash2 size={14}/>} 
            </span>
          </button>
        ))}
      </div>
      <div className="knowledge-panel">
        <div className="sidebar-label knowledge-label-row"><span>Knowledge</span><button className="mini-icon-btn" onClick={onUpload} title="Upload document"><Plus size={14}/></button></div>
        <div className="document-list">
          {documents.length === 0 ? <div className="document-empty">No documents in this chat.</div> : documents.map((doc) => (
            <div className="document-item" key={doc.id}>
              <FileText size={15} className="document-item-icon" />
              <div className="document-item-copy"><strong title={doc.filename}>{doc.filename}</strong><span>{doc.chunk_count} chunks</span></div>
              <button className="mini-icon-btn document-delete" onClick={() => onDeleteDocument(doc.id)} title="Delete document"><Trash2 size={13}/></button>
            </div>
          ))}
        </div>
        <button className="upload-doc-btn" onClick={onUpload}><FileText size={15}/> Add document</button>
      </div>
    </aside>
  );
}
