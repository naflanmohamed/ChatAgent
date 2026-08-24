import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  timeout: 15000,
  headers: { Accept: "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === "ECONNABORTED" || error.message === "Network Error") {
      error.friendlyMessage = "The backend is not responding. Make sure FastAPI is running on port 8000.";
    }
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      error.friendlyMessage = "Your session expired. Please sign in again.";
    }
    return Promise.reject(error);
  },
);

export default api;
