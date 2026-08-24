import api from "./api";

export async function getPendingApprovals(conversationId) {
  const { data } = await api.get("/approvals", { params: { conversation_id: conversationId } });
  return data;
}

export async function approveAction(id, editedPayload) {
  const { data } = await api.post(`/approvals/${id}/approve`, { edited_payload: editedPayload || undefined });
  return data;
}

export async function rejectAction(id, note = "Rejected by user") {
  const { data } = await api.post(`/approvals/${id}/reject`, { note });
  return data;
}
