import { createContext, useContext, useEffect, useState } from "react";
import { loginWithGoogleCode, fetchCurrentUser, logout as clearSession } from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setIsLoading(false);
      return;
    }
    fetchCurrentUser()
      .then(setUser)
      .catch(() => localStorage.removeItem("access_token"))
      .finally(() => setIsLoading(false));
  }, []);

  async function loginWithGoogleAuthCode(code) {
    const { access_token, user: loggedInUser } = await loginWithGoogleCode(code);
    localStorage.setItem("access_token", access_token);
    setUser(loggedInUser);
  }

  function logout() {
    clearSession();
    setUser(null);
  }

  const value = {
    user,
    isAuthenticated: Boolean(user),
    isLoading,
    loginWithGoogleAuthCode,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
