import { useEffect, useState } from "react";
import { CalendarDays, Check, Clock3, Mail, ShieldCheck, X } from "lucide-react";
import { approveAction, getPendingApprovals, rejectAction } from "../services/approvalService";

const titleMap = { send_email: "Send email", reply_to_email: "Reply to email", create_calendar_event: "Create calendar event", send_meeting_invite_email: "Send meeting invite by email" };

function prettyDate(value) {
  if (!value) return "";
  try { return new Date(value).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }); } catch { return value; }
}

export default function ApprovalPanel({ conversationId, refreshKey = 0 }) {
  const [items, setItems] = useState([]);
  const [busyId, setBusyId] = useState(null);

  async function refresh() {
    if (!conversationId) return;
    try { setItems(await getPendingApprovals(conversationId)); } catch { setItems([]); }
  }

  useEffect(() => { refresh(); }, [conversationId, refreshKey]);

  async function decide(id, approve) {
    setBusyId(id);
    try {
      if (approve) await approveAction(id); else await rejectAction(id);
      await refresh();
    } finally { setBusyId(null); }
  }

  if (!items.length) return null;

  return (
    <div className="approval-stack">
      {items.map((item) => {
        const isMail = item.action_type.includes("email") || item.action_type.includes("reply");
        const isCalendar = item.action_type.includes("calendar");
        const payload = item.payload || {};
        return (
          <article className="approval-card" key={item.id}>
            <div className="approval-card-head">
              <div className="approval-icon">{isCalendar ? <CalendarDays size={17}/> : <Mail size={17}/>}</div>
              <div><strong>{titleMap[item.action_type] || item.action_type}</strong><span><Clock3 size={12}/> {prettyDate(item.created_at)}</span></div>
              <ShieldCheck size={18} className="approval-shield"/>
            </div>
            <div className="approval-card-body">
              {payload.to && <div><label>To</label><p>{payload.to}</p></div>}
              {payload.subject && <div><label>Subject</label><p>{payload.subject}</p></div>}
              {payload.meeting_title && <div><label>Meeting</label><p>{payload.meeting_title}</p></div>}
              {payload.start_time && <div><label>Time</label><p>{payload.start_time} · {payload.duration_minutes || 60} min</p></div>}
              {payload.body && <div><label>Message</label><p className="approval-message">{payload.body}</p></div>}
              {isCalendar && <div className="approval-warning">Calendar changes are external actions. Review before approving.</div>}
              {item.action_type === "send_meeting_invite_email" && <div className="approval-note">Email only. This request will not create a calendar event.</div>}
            </div>
            <div className="approval-actions">
              <button disabled={busyId === item.id} className="approval-reject" onClick={() => decide(item.id, false)}><X size={15}/> Reject</button>
              <button disabled={busyId === item.id} className="approval-approve" onClick={() => decide(item.id, true)}><Check size={15}/> Approve & execute</button>
            </div>
          </article>
        );
      })}
    </div>
  );
}
