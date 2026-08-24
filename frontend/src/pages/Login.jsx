import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useGoogleLogin } from "@react-oauth/google";
import { useAuth } from "../context/AuthContext.jsx";
import Badge from "../components/Badge.jsx";
import "./Login.css";

// Space-separated, matching SCOPES in the backend's google_client.py.
// Must stay in sync -- if you add a new tool that needs a new permission,
// add the scope here too, or Google will simply never grant it.
const GOOGLE_SCOPES = [
  "openid",
  "email",
  "profile",
  "https://www.googleapis.com/auth/gmail.send",
  "https://www.googleapis.com/auth/gmail.readonly",
  "https://www.googleapis.com/auth/calendar.events",
  "https://www.googleapis.com/auth/calendar.readonly",
].join(" ");

export default function Login() {
  const { loginWithGoogleAuthCode } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // flow: "auth-code" gets us a one-time CODE instead of an ID token.
  // Only the backend (which has the client secret) can turn that code
  // into real, usable Gmail/Calendar access tokens.
  const googleLogin = useGoogleLogin({
    flow: "auth-code",
    scope: GOOGLE_SCOPES,
    onSuccess: async (codeResponse) => {
      setError("");
      setIsLoading(true);
      try {
        await loginWithGoogleAuthCode(codeResponse.code);
        navigate("/chat", { replace: true });
      } catch (err) {
        setError("Sign-in failed. Please try again.");
      } finally {
        setIsLoading(false);
      }
    },
    onError: () => setError("Google sign-in was cancelled or failed."),
  });

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-badge-wrap">
          <Badge size={44} />
        </div>
        <h1 className="login-title">Welcome back</h1>
        <p className="login-subtitle">
          Sign in with Google to chat, and let the assistant read/send email
          and manage your calendar when you ask it to.
        </p>

        <div className="login-google-wrap">
          <button
            type="button"
            className="google-signin-btn"
            onClick={() => googleLogin()}
            disabled={isLoading}
          >
            <GoogleGlyph />
            {isLoading ? "Signing in..." : "Continue with Google"}
          </button>
        </div>

        {error && <p className="login-error">{error}</p>}

      </div>
    </div>
  );
}

// Standard multi-color Google "G" mark, drawn from the official public
// SVG paths -- used per Google's own branding guidelines for sign-in buttons.
function GoogleGlyph() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.57 2.7-3.88 2.7-6.62z" />
      <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.98v2.33A9 9 0 0 0 9 18z" />
      <path fill="#FBBC05" d="M3.95 10.7A5.4 5.4 0 0 1 3.67 9c0-.59.1-1.17.28-1.7V4.97H.98A9 9 0 0 0 0 9c0 1.45.35 2.83.98 4.03l2.97-2.33z" />
      <path fill="#EA4335" d="M9 3.58c1.32 0 2.51.46 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .98 4.97l2.97 2.33C4.66 5.17 6.65 3.58 9 3.58z" />
    </svg>
  );
}
