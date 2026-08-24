import api from "./api";

export async function uploadDocument(file, conversationId) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("conversation_id", conversationId);
  const { data } = await api.post("/documents", formData);
  return data;
}

export async function listDocuments(conversationId) {
  const { data } = await api.get("/documents", { params: { conversation_id: conversationId } });
  return data;
}

export async function deleteDocument(documentId) {
  await api.delete(`/documents/${documentId}`);
}
