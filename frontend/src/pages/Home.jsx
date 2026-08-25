import { Link, Navigate } from "react-router-dom";
import { ArrowRight, FileText, Shield, Zap } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import Badge from "../components/Badge.jsx";
import "./Home.css";

const features = [
  { icon: Zap, label: "Tools + MCP" },
  { icon: FileText, label: "Your documents" },
  { icon: Shield, label: "Asks before acting" },
];

export default function Home() {
  const { isAuthenticated, isLoading } = useAuth();

  // Already logged in? Skip the landing page entirely.
  if (!isLoading && isAuthenticated) {
    return <Navigate to="/chat" replace />;
  }

  return (
    <div className="home-screen">
      <div className="home-kicker">
        <span className="home-kicker-dot" />
        <span>Private AI workspace</span>
      </div>
      <div className="home-badge-wrap">
        <Badge size={56} />
      </div>
      <h1 className="home-title">
        A Chat Agent that <span>understands you</span>
      </h1>
      <p className="home-subtitle">
        Sign in with Google and start a conversation. Every chat is saved, so
        you can pick up right where you left off.
      </p>
      <div className="home-features">
        {features.map(({ icon: Icon, label }) => (
          <span className="home-feature-chip" key={label}>
            <Icon size={13} />
            {label}
          </span>
        ))}
      </div>
      <Link to="/login" className="home-cta">
        Get started
        <ArrowRight size={16} />
      </Link>
      <p className="home-footnote">No credit card needed. Sign in takes a few seconds.</p>
    </div>
  );
}
