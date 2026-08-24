import { Component } from "react";

export default class AppErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, message: error?.message || "Unexpected application error" };
  }

  componentDidCatch(error) {
    console.error("[AppErrorBoundary]", error);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 24, background: "#f7f8fa", color: "#111318", fontFamily: "Inter, system-ui, sans-serif" }}>
        <div style={{ maxWidth: 520, textAlign: "center", border: "1px solid #e3e6eb", borderRadius: 18, padding: 28, background: "#fff", boxShadow: "0 16px 40px rgba(17,19,24,.08)" }}>
          <h2 style={{ margin: "0 0 8px" }}>Chat Agent could not render this page</h2>
          <p style={{ color: "#5e6470", lineHeight: 1.6 }}>Try refreshing the page. The application captured the rendering failure instead of leaving a blank screen.</p>
          <small style={{ color: "#8b919c" }}>{this.state.message}</small>
          <div style={{ marginTop: 18 }}><button onClick={() => window.location.reload()} style={{ border: 0, borderRadius: 10, padding: "10px 14px", background: "#111318", color: "white", cursor: "pointer" }}>Reload</button></div>
        </div>
      </div>
    );
  }
}
