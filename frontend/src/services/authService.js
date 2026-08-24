import api from "./api";

export async function loginWithGoogleCode(code) {
  const { data } = await api.post("/auth/google", { code });
  return data;
}

export async function fetchCurrentUser() {
  const { data } = await api.get("/auth/me");
  return data;
}

export function logout() {
  localStorage.removeItem("access_token");
}
