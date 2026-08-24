import api from "./api";

export async function createConversation() {
  const { data } = await api.post("/conversations");
  return data;
}
export async function listConversations() {
  const { data } = await api.get("/conversations");
  return data;
}
export async function getConversation(conversationId) {
  const { data } = await api.get(`/conversations/${conversationId}`);
  return data;
}
export async function updateConversationModel(conversationId, model) {
  const { data } = await api.patch(`/conversations/${conversationId}/model`, { model });
  return data;
}
export async function deleteConversation(conversationId) {
  await api.delete(`/conversations/${conversationId}`);
}
