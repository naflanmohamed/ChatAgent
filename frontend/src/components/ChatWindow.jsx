import { useEffect, useRef, useState } from "react";
import { ArrowUp, Bot, Check, ChevronDown, FileText, Loader2, Paperclip, Sparkles, Zap } from "lucide-react";
import ApprovalPanel from "./ApprovalPanel.jsx";
import MessageBubble from "./MessageBubble.jsx";
import Badge from "./Badge.jsx";
import api from "../services/api";
import { getConversation } from "../services/conversationService";
import { uploadDocument } from "../services/documentService";

const quickPrompts = [
  { title: "Research", text: "Research the latest developments on this topic and compare credible sources." },
  { title: "My documents", text: "Search my uploaded documents and explain the most important findings." },
  { title: "Plan a task", text: "Break this goal into the best practical steps and tell me what you need from me." },
  { title: "Email only", text: "Draft a professional meeting invitation email only. Do not create a calendar event." },
];

function modelGroup(models) {
  return models.reduce((acc, item) => { (acc[item.provider] ||= []).push(item); return acc; }, {});
}

export default function ChatWindow({ conversationId, onTitleUpdate, onDocumentsChanged }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [approvalRefreshKey, setApprovalRefreshKey] = useState(0);
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [modelInfo, setModelInfo] = useState(null);
  const [isChangingModel, setIsChangingModel] = useState(false);
  const [runInfo, setRunInfo] = useState(null);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const activeConversationRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    activeConversationRef.current = conversationId;
    if (!conversationId) return;
    let cancelled = false;
    setMessages([]); setRunInfo(null);
    getConversation(conversationId).then((data) => {
      if (cancelled || activeConversationRef.current !== conversationId) return;
      setMessages((data.messages || []).map((m) => ({ role: m.role, content: m.content })));
      setSelectedModel(data.model || "");
    }).catch(() => { if (!cancelled) setMessages([]); });
    return () => { cancelled = true; };
  }, [conversationId]);

  useEffect(() => {
    api.get("/models").then(({ data }) => {
      setModels(data.models || []);
      setSelectedModel((current) => current || data.default || "gemini-2.5-flash");
    }).catch(() => setModels([]));
  }, []);

  useEffect(() => {
    const found = models.find((m) => m.id === selectedModel);
    setModelInfo(found || null);
  }, [models, selectedModel]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages, isSending]);

  useEffect(() => {
    const el = inputRef.current; if (!el) return;
    el.style.height = "auto"; el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [input]);

  async function sendMessage(text) {
    const clean = text.trim();
    if (!clean || isSending || !conversationId) return;
    const requestId = conversationId;
    setMessages((prev) => [...prev, { role: "user", content: clean }]);
    setInput(""); setIsSending(true); setRunInfo({ status: "thinking", toolCount: 0 });
    try {
      const { data } = await api.post("/chat", { conversation_id: requestId, message: clean, model: selectedModel || undefined });
      if (activeConversationRef.current !== requestId) return;
      setSelectedModel(data.model || selectedModel);
      setRunInfo({ status: data.status, toolCount: data.tool_count || 0, provider: data.model_provider });
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
      if (data.approvals?.length) setApprovalRefreshKey((v) => v + 1);
      if (data.title) onTitleUpdate?.(requestId, data.title);
    } catch (error) {
      if (activeConversationRef.current !== requestId) return;
      setMessages((prev) => [...prev, { role: "assistant", content: error.response?.data?.detail || "The assistant could not complete that request." }]);
      setRunInfo({ status: "failed", toolCount: 0 });
    } finally { if (activeConversationRef.current === requestId) setIsSending(false); }
  }

  async function handleModelChange(event) {
    const next = event.target.value;
    const previous = selectedModel;
    setSelectedModel(next); setIsChangingModel(true);
    try { await api.patch(`/conversations/${conversationId}/model`, { model: next }); }
    catch { setSelectedModel(previous); }
    finally { setIsChangingModel(false); }
  }

  function onSubmit(event) { event.preventDefault(); sendMessage(input); }
  function onKeyDown(event) { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(input); } }

  async function handleFileSelected(event) {
    const file = event.target.files?.[0]; event.target.value = "";
    if (!file || !conversationId) return;
    setIsUploading(true);
    try { await uploadDocument(file, conversationId); onDocumentsChanged?.(); setMessages((prev) => [...prev, { role: "system", content: `Uploaded ${file.name} and indexed it for this conversation.` }]); }
    catch (error) { setMessages((prev) => [...prev, { role: "system-error", content: error.response?.data?.detail || "Document upload failed." }]); }
    finally { setIsUploading(false); }
  }

  const groups = modelGroup(models);

  return (
    <div className="chat-window">
      <div className="chat-topbar">
        <div className="chat-context"><div className="context-icon"><Bot size={18}/></div><div><strong>Chat Agent</strong><span>{modelInfo?.description || "Ready to work across your tools and knowledge."}</span></div></div>
        <div className="model-control">
          <span className="model-control-label"><Sparkles size={13}/> Model</span>
          <select value={selectedModel} onChange={handleModelChange} disabled={isChangingModel || !conversationId} aria-label="AI model">
            <optgroup label="Google Gemini">{groups.gemini?.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}</optgroup>
            <optgroup label="Groq">{groups.groq?.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}</optgroup>
          </select>
          {isChangingModel && <Loader2 size={14} className="spin"/>}
        </div>
      </div>

      <div className="chat-log">
        {messages.length === 0 && (
          <div className="chat-empty">
            <div className="hero-orb"><Badge size={62}/><div className="hero-orb-ring"/></div>
            <div className="empty-kicker"><span>PRIVATE AI WORKSPACE</span><span className="empty-kicker-dot"/><span>TOOLS + RAG + MCP</span></div>
            <h2 className="empty-title">What should we get done?</h2>
            <p className="empty-subtitle">Ask naturally. Chat Agent can reason across your conversations, documents, email, calendar, web research and MCP utilities.</p>
            <div className="quick-prompts">{quickPrompts.map((p) => <button key={p.title} className="quick-prompt" onClick={() => { setInput(p.text); inputRef.current?.focus(); }}><strong>{p.title}</strong><span>{p.text}</span></button>)}</div>
          </div>
        )}
        {messages.map((m, i) => {
          if (m.role === "system") return <div className="chat-event" key={i}><Check size={14}/>{m.content}</div>;
          if (m.role === "system-error") return <div className="chat-event chat-event--error" key={i}>{m.content}</div>;
          return <MessageBubble key={i} role={m.role} content={m.content}/>;
        })}
        {isSending && <div className="message-row message-row--assistant"><Badge size={30}/><div className="assistant-thinking"><span className="thinking-pulse"/><div><strong>Working on it</strong><span>{runInfo?.toolCount ? `Using ${runInfo.toolCount} tool${runInfo.toolCount === 1 ? "" : "s"}` : "Reasoning and choosing the right tools"}</span></div></div></div>}
        <div ref={bottomRef}/>
      </div>

      <div className="composer-wrap">
        <ApprovalPanel conversationId={conversationId} refreshKey={approvalRefreshKey}/>
        <form className="chat-composer" onSubmit={onSubmit}>
          <div className="composer-toolbar"><button type="button" className="composer-tool-btn" onClick={() => fileInputRef.current?.click()} disabled={isUploading}><Paperclip size={17}/>{isUploading ? "Uploading" : "Attach"}</button><span className="composer-tip">Enter to send · Shift + Enter for a new line</span><span className="composer-model-tag"><Zap size={12}/>{modelInfo?.provider === "groq" ? "Groq" : "Gemini"}</span></div>
          <div className="composer-input-row"><textarea ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={onKeyDown} placeholder="Tell your agent what you want to accomplish..." rows={1}/><button className="send-btn" type="submit" disabled={isSending || !input.trim()} aria-label="Send"><ArrowUp size={18}/></button></div>
        </form>
        <div className="composer-footnote">The agent asks before sending email or changing your calendar.</div>
      </div>
      <input ref={fileInputRef} type="file" accept=".pdf,.docx,.txt,.md" hidden onChange={handleFileSelected}/>
    </div>
  );
}
