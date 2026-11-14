import { useCallback, useEffect, useMemo, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, token, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Request failed");
  return data;
}

function formatTime(value) {
  if (!value) return "Never";
  return new Date(value).toLocaleString();
}

function MetricBar({ label, value }) {
  const amount = Number(value || 0);
  const tone = amount >= 90 ? "danger" : amount >= 75 ? "warning" : "good";
  return (
    <div className="metric">
      <div className="metric-label"><span>{label}</span><strong>{amount.toFixed(0)}%</strong></div>
      <div className="track"><div className={`fill ${tone}`} style={{ width: `${Math.min(amount, 100)}%` }} /></div>
    </div>
  );
}

function Sparkline({ points = [], field }) {
  const values = points.map((point) => Number(point[field] || 0));
  if (!values.length) return <div className="empty-chart">Waiting for agent data</div>;
  const max = Math.max(100, ...values);
  const coords = values.map((value, index) => {
    const x = values.length === 1 ? 50 : (index / (values.length - 1)) * 100;
    return `${x},${32 - (value / max) * 28}`;
  }).join(" ");
  return <svg className="sparkline" viewBox="0 0 100 36" preserveAspectRatio="none" aria-label={`${field} trend`}>
    <polyline points={coords} fill="none" stroke="currentColor" strokeWidth="2" vectorEffect="non-scaling-stroke" />
  </svg>;
}

function AuthScreen({ onLogin }) {
  const [signup, setSignup] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await request(`/api/auth/${signup ? "signup" : "login"}`, null, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      onLogin(result);
    } catch (issue) {
      setError(issue.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-brand"><div className="brand-mark">A</div><span>AutoHeal<span className="brand-x">X</span></span></div>
      <section className="auth-card">
        <div className="eyebrow">INFRASTRUCTURE CONTROL PLANE</div>
        <h1>{signup ? "Create your workspace" : "Welcome back"}</h1>
        <p className="muted">{signup ? "Start monitoring your Linux fleet in minutes." : "Sign in to see what's happening across your fleet."}</p>
        <form onSubmit={submit}>
          <label>Email address<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@company.com" /></label>
          <label>Password<input type="password" autoComplete={signup ? "new-password" : "current-password"} minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" /></label>
          {error && <div className="form-error">{error}</div>}
          <button className="button primary full" disabled={busy}>{busy ? "Please wait…" : signup ? "Create account" : "Sign in"} <span aria-hidden="true">→</span></button>
        </form>
        <div className="auth-switch">{signup ? "Already have an account?" : "New to AutoHealX?"} <button onClick={() => { setSignup(!signup); setError(""); }}>{signup ? "Sign in" : "Create account"}</button></div>
      </section>
      <div className="auth-foot">Monitor. Detect. Recover.</div>
    </main>
  );
}

function AddServerModal({ token, onClose, onCreated }) {
  const [name, setName] = useState("");
  const [host, setHost] = useState("");
  const [environment, setEnvironment] = useState("production");
  const [created, setCreated] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const server = await request("/api/servers", token, {
        method: "POST",
        body: JSON.stringify({ name, host, environment }),
      });
      setCreated(server);
      onCreated();
    } catch (issue) {
      setError(issue.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="modal">
        <button className="modal-close" onClick={onClose} aria-label="Close">×</button>
        {created ? <>
          <div className="eyebrow">SERVER REGISTERED</div><h2>Connect your agent</h2>
          <p className="muted">Copy this API key now. It is only shown once.</p>
          <div className="key-block"><span>Server ID</span><code>{created.id}</code><span>API key</span><code>{created.api_key}</code></div>
          <button className="button primary full" onClick={onClose}>Done</button>
        </> : <>
          <div className="eyebrow">FLEET MANAGEMENT</div><h2>Add a server</h2>
          <p className="muted">Register a host, then install the Linux agent.</p>
          <form onSubmit={submit}>
            <label>Server name<input required value={name} onChange={(event) => setName(event.target.value)} placeholder="web-prod-01" /></label>
            <label>Host or IP<input required value={host} onChange={(event) => setHost(event.target.value)} placeholder="10.0.0.12" /></label>
            <label>Environment<select value={environment} onChange={(event) => setEnvironment(event.target.value)}><option>production</option><option>staging</option><option>development</option></select></label>
            {error && <div className="form-error">{error}</div>}
            <button className="button primary full" disabled={busy}>{busy ? "Registering…" : "Register server"}</button>
          </form>
        </>}
      </section>
    </div>
  );
}

function Dashboard({ token, user, onLogout }) {
  const [data, setData] = useState(null);
  const [tab, setTab] = useState("overview");
  const [showAdd, setShowAdd] = useState(false);
  const [error, setError] = useState("");
  const [updatedAt, setUpdatedAt] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const result = await request("/api/dashboard", token);
      setData(result);
      setUpdatedAt(new Date());
      setError("");
    } catch (issue) {
      setError(issue.message);
    }
  }, [token]);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 15000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const summary = data?.summary || { total: 0, online: 0, offline: 0, active_alerts: 0 };
  const nav = useMemo(() => [["overview", "Overview"], ["alerts", "Alerts"], ["recoveries", "Recovery logs"]], []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand"><div className="brand-mark">A</div><span>AutoHeal<span className="brand-x">X</span></span></div>
        <div className="side-label">WORKSPACE</div>
        <nav>{nav.map(([key, label]) => <button key={key} className={`nav-item ${tab === key ? "selected" : ""}`} onClick={() => setTab(key)}><span className="nav-glyph">{key === "overview" ? "▦" : key === "alerts" ? "◉" : "↻"}</span>{label}{key === "alerts" && summary.active_alerts > 0 && <span className="nav-count">{summary.active_alerts}</span>}</button>)}</nav>
        <div className="sidebar-bottom"><div className="user-avatar">{user.email.slice(0, 1).toUpperCase()}</div><div className="user-info"><strong>{user.email}</strong><span>Workspace owner</span></div><button className="logout" title="Sign out" onClick={onLogout}>↗</button></div>
      </aside>
      <main className="main-content">
        <header className="topbar"><div><span className="breadcrumb">AutoHealX</span><span className="crumb-sep">/</span><span>{nav.find(([key]) => key === tab)?.[1]}</span></div><div className="top-actions"><span className="refresh-status"><i /> Live · refreshes every 15s</span><button className="button primary" onClick={() => setShowAdd(true)}><span>＋</span> Add server</button></div></header>
        <section className="page">
          <div className="page-heading"><div><div className="eyebrow">FLEET MONITORING</div><h1>{tab === "overview" ? "Infrastructure overview" : tab === "alerts" ? "Alerts" : "Recovery logs"}</h1><p className="muted">{tab === "overview" ? "A live view of your Linux infrastructure health." : tab === "alerts" ? "Issues detected by your monitoring agents." : "Automated and configured recovery actions."}</p></div><div className="last-updated">Updated {updatedAt ? updatedAt.toLocaleTimeString() : "—"}</div></div>
          {error && <div className="notice error-notice">{error} <button onClick={refresh}>Retry</button></div>}
          {tab === "overview" && <>
            <div className="summary-grid">
              <article className="summary-card"><span className="summary-icon green">▦</span><span className="summary-label">Total servers</span><strong>{summary.total}</strong><small>Registered in your fleet</small></article>
              <article className="summary-card"><span className="summary-icon green">⌁</span><span className="summary-label">Online</span><strong>{summary.online}<small className="of-total"> / {summary.total}</small></strong><small>Reporting within 90 seconds</small></article>
              <article className="summary-card"><span className="summary-icon orange">◉</span><span className="summary-label">Offline</span><strong>{summary.offline}</strong><small>Require attention</small></article>
              <article className="summary-card"><span className="summary-icon purple">!</span><span className="summary-label">Recent alerts</span><strong>{summary.active_alerts}</strong><small>Latest 50 events</small></article>
            </div>
            <div className="section-title"><div><h2>Servers</h2><span>{data?.servers?.length || 0} hosts</span></div><button className="text-button" onClick={() => setShowAdd(true)}>＋ Register server</button></div>
            <div className="server-grid">{data?.servers?.length ? data.servers.map((server) => {
              const metrics = server.latest_metrics || {};
              const points = data.trends?.[server.id] || [];
              return <article className="server-card" key={server.id}>
                <div className="server-card-head"><div className="server-ident"><div className="server-icon">⌘</div><div><h3>{server.name}</h3><span>{server.host} · {server.environment}</span></div></div><span className={`status-pill ${server.status}`}><i />{server.status}</span></div>
                <div className="server-meta">{server.hostname || "Awaiting agent"} <span>Last seen {formatTime(server.last_seen)}</span></div>
                <div className="metrics-grid"><MetricBar label="CPU" value={metrics.cpu_percent} /><MetricBar label="Memory" value={metrics.memory_percent} /><MetricBar label="Disk" value={metrics.disk_percent} /></div>
                <div className="trend-row"><span>CPU TREND</span><Sparkline points={points} field="cpu_percent" /><b>{metrics.cpu_percent == null ? "—" : `${Number(metrics.cpu_percent).toFixed(0)}%`}</b></div>
              </article>;
            }) : <div className="empty-state"><div>⌘</div><h3>Your fleet starts here</h3><p>Register a Linux server to start collecting health and performance metrics.</p><button className="button primary" onClick={() => setShowAdd(true)}>＋ Add your first server</button></div>}</div>
          </>}
          {tab === "alerts" && <EventTable kind="alerts" items={data?.alerts || []} />}
          {tab === "recoveries" && <EventTable kind="recoveries" items={data?.healing_logs || []} />}
        </section>
      </main>
      {showAdd && <AddServerModal token={token} onClose={() => setShowAdd(false)} onCreated={refresh} />}
    </div>
  );
}

function EventTable({ kind, items }) {
  if (!items.length) return <div className="empty-state event-empty"><div>{kind === "alerts" ? "◉" : "↻"}</div><h3>No {kind === "alerts" ? "alerts" : "recovery actions"} yet</h3><p>Events will show up here when your agents report them.</p></div>;
  return <div className="event-list">{items.map((item) => <article className="event-card" key={item.id}>
    <div className={`event-icon ${kind === "alerts" ? item.severity : item.result}`}>{kind === "alerts" ? "!" : item.result === "success" ? "✓" : "↻"}</div>
    <div className="event-main"><div className="event-title">{kind === "alerts" ? item.title : item.issue}<span className={`event-tag ${kind === "alerts" ? item.severity : item.result}`}>{kind === "alerts" ? item.severity : item.result}</span></div><p>{kind === "alerts" ? item.message : `${item.action}${item.details ? ` — ${item.details}` : ""}`}</p><small>{item.server_name || "Server"} · {formatTime(item.created_at)}</small></div>
  </article>)}</div>;
}

export default function App() {
  const [session, setSession] = useState(() => {
    try { return JSON.parse(localStorage.getItem("autohealx_session")); } catch { return null; }
  });
  function login(result) {
    const next = { token: result.access_token, user: result.user };
    localStorage.setItem("autohealx_session", JSON.stringify(next));
    setSession(next);
  }
  function logout() {
    localStorage.removeItem("autohealx_session");
    setSession(null);
  }
  if (!session?.token) return <AuthScreen onLogin={login} />;
  return <Dashboard key={session.token} token={session.token} user={session.user} onLogout={logout} />;
}
