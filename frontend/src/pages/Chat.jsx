import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { LogOut, Menu, PanelLeftClose, PanelLeftOpen, Sparkles } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import ChatWindow from "../components/ChatWindow.jsx";
import ConversationSidebar from "../components/ConversationSidebar.jsx";
import Badge from "../components/Badge.jsx";
import ThemeToggle from "../components/ThemeToggle.jsx";
import { createConversation, deleteConversation, listConversations } from "../services/conversationService";
import { deleteDocument, listDocuments, uploadDocument } from "../services/documentService";
import "./Chat.css";

export default function Chat() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { conversationId } = useParams();
  const [conversations, setConversations] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [activeId, setActiveId] = useState(conversationId || null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isBooting, setIsBooting] = useState(true);
  const [globalError, setGlobalError] = useState("");
  const fileInputRef = useRef(null);

  const loadDocuments = useCallback(async (id) => {
    if (!id) { setDocuments([]); return; }
    try { setDocuments(await listDocuments(id)); } catch { setDocuments([]); }
  }, []);

  const bootWorkspace = useCallback(async () => {
    setIsBooting(true);
    setGlobalError("");
    try {
      let rows = await listConversations();
      if (!rows.length) rows = [await createConversation()];
      setConversations(rows);
      const preferred = conversationId && rows.some((c) => c.id === conversationId) ? conversationId : rows[0].id;
      setActiveId(preferred);
      if (!conversationId || preferred !== conversationId) {
        navigate(`/chat/${preferred}`, { replace: true });
      }
    } catch (error) {
      setGlobalError(
        error.friendlyMessage ||
        error.response?.data?.detail ||
        "Could not load your workspace. Make sure the backend, PostgreSQL, and Redis are running."
      );
    } finally {
      setIsBooting(false);
    }
  }, [conversationId, navigate]);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      await bootWorkspace();
      if (cancelled) return;
    };
    run();
    return () => { cancelled = true; };
  }, [bootWorkspace]);

  useEffect(() => {
    if (conversationId && conversations.some((c) => c.id === conversationId)) {
      setActiveId(conversationId);
      loadDocuments(conversationId);
    }
  }, [conversationId, conversations, loadDocuments]);

  const selectConversation = (id) => navigate(`/chat/${id}`);

  async function handleNewChat() {
    const fresh = await createConversation();
    setConversations((prev) => [fresh, ...prev]);
    navigate(`/chat/${fresh.id}`);
  }

  function handleTitleUpdate(id, title) {
    setConversations((prev) => prev.map((c) => c.id === id ? { ...c, title } : c));
  }

  async function handleDelete(id) {
    await deleteConversation(id);
    const remaining = conversations.filter((c) => c.id !== id);
    if (!remaining.length) {
      const fresh = await createConversation();
      setConversations([fresh]);
      navigate(`/chat/${fresh.id}`);
      return;
    }
    setConversations(remaining);
    if (activeId === id) navigate(`/chat/${remaining[0].id}`);
  }

  function openUpload() { fileInputRef.current?.click(); }

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !activeId) return;
    try {
      await uploadDocument(file, activeId);
      await loadDocuments(activeId);
    } catch (error) {
      setGlobalError(error.response?.data?.detail || "Document upload failed.");
    }
  }

  async function handleDeleteDocument(id) {
    try {
      await deleteDocument(id);
      await loadDocuments(activeId);
    } catch (error) {
      setGlobalError(error.response?.data?.detail || "Could not delete the document.");
    }
  }

  if (isBooting) {
    return (
      <div className="workspace-loading" role="status" aria-live="polite">
        <div className="loading-orb"><Sparkles size={20}/></div>
        <strong>Loading your workspace</strong>
        <span>Restoring chats and knowledge...</span>
        <small>Checking your conversations and connected data.</small>
      </div>
    );
  }

  return (
    <div className="chat-page">
      <header className="chat-header">
        <div className="header-left">
          <button className="icon-btn mobile-menu" onClick={() => setSidebarOpen((v) => !v)} aria-label="Open navigation"><Menu size={18}/></button>
          <button className="icon-btn desktop-sidebar-toggle" onClick={() => setSidebarOpen((v) => !v)} aria-label="Toggle sidebar">{sidebarOpen ? <PanelLeftClose size={18}/> : <PanelLeftOpen size={18}/>}</button>
          <Link to="/chat" className="chat-header-brand"><Badge size={32}/><div><h1 className="chat-header-title">Chat Agent</h1><span className="chat-header-status"><span className="status-dot"/> AI Workspace</span></div></Link>
        </div>
        <div className="header-right">
          <div className="header-user-chip"><div className="header-avatar">{user?.picture ? <img src={user.picture} alt=""/> : (user?.name || user?.email || "U").charAt(0).toUpperCase()}</div><div className="header-user-copy"><strong>{user?.name || "User"}</strong><span>{user?.email}</span></div></div>
          <ThemeToggle />
          <button className="logout-btn" onClick={logout}><LogOut size={15}/><span>Sign out</span></button>
        </div>
      </header>
      <div className="workspace-body">
        <div className={`sidebar-overlay ${sidebarOpen ? "sidebar-overlay--visible" : ""}`} onClick={() => setSidebarOpen(false)} />
        <aside className={`sidebar-wrap ${sidebarOpen ? "sidebar-wrap--open" : "sidebar-wrap--closed"}`}>
          {sidebarOpen && <ConversationSidebar conversations={conversations} activeId={activeId} documents={documents} onSelect={selectConversation} onNewChat={handleNewChat} onDelete={handleDelete} onUpload={openUpload} onDeleteDocument={handleDeleteDocument}/>} 
        </aside>
        <main className="chat-main">
          {globalError && (
            <div className="workspace-error" role="alert">
              <span>{globalError}</span>
              <div className="workspace-error-actions">
                <button onClick={bootWorkspace}>Retry</button>
                <button onClick={() => setGlobalError("")}>Dismiss</button>
              </div>
            </div>
          )}
          <ChatWindow conversationId={activeId} onTitleUpdate={handleTitleUpdate} onDocumentsChanged={() => loadDocuments(activeId)} fileInputRef={fileInputRef}/>
          <input ref={fileInputRef} type="file" accept=".pdf,.docx,.txt,.md" hidden onChange={handleUpload}/>
        </main>
      </div>
    </div>
  );
}
