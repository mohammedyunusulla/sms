import { useMemo, useState } from "react";

function normalizeBaseUrl(url) {
  const value = (url || "/api").trim();
  return value.replace(/\/+$/, "");
}

export default function App() {
  const [status, setStatus] = useState("Idle");

  const apiBaseUrl = useMemo(
    () => normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL),
    []
  );

  async function checkHealth() {
    setStatus("Checking...");
    const response = await fetch(`${apiBaseUrl}/health`);
    if (!response.ok) {
      setStatus(`Request failed (${response.status})`);
      return;
    }

    const payload = await response.json();
    setStatus(payload.status === "ok" ? "Backend is healthy" : "Unexpected response");
  }

  return (
    <main style={{ fontFamily: "Arial, sans-serif", margin: "2rem", maxWidth: "700px" }}>
      <h1>School Management System</h1>
      <p>API Base URL: <code>{apiBaseUrl}</code></p>
      <button onClick={checkHealth} type="button">
        Check API Health
      </button>
      <p>Status: {status}</p>
    </main>
  );
}
