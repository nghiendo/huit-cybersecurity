import { useEffect, useRef, useState } from "react";
import {
  BarChart3,
  BrainCircuit,
  Database,
  LayoutPanelLeft,
  RefreshCw,
  Shield,
  ShieldCheck,
  Sparkles,
  TerminalSquare
} from "lucide-react";

const tabs = [
  { id: "overview", label: "Overview", icon: BarChart3 },
  { id: "controls", label: "Controls", icon: Shield },
  { id: "users", label: "Users", icon: Database },
  { id: "comments", label: "Comments", icon: Sparkles },
  { id: "logs", label: "Logs", icon: BrainCircuit },
  { id: "terminal", label: "Terminal", icon: TerminalSquare }
];

function AdminPage({ navigate }) {
  const [activeTab, setActiveTab] = useState("overview");
  const [settings, setSettings] = useState(null);
  const [stats, setStats] = useState(null);
  const [tableState, setTableState] = useState({
    resource: "users",
    rows: [],
    pagination: null
  });
  const [loading, setLoading] = useState(true);
  const [tableLoading, setTableLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [terminalOutput, setTerminalOutput] = useState("backend-terminal> awaiting_stream");
  const adminToken = new URLSearchParams(window.location.search).get("token") ?? "";

  useEffect(() => {
    if (!adminToken) {
      setError("Missing admin token. Open this page with /admin?token=YOUR_TOKEN.");
      setLoading(false);
      return;
    }
    void loadAdminPanel("users", 0);
  }, [adminToken]);

  useEffect(() => {
    if (!adminToken) {
      return;
    }

    if (activeTab === "users" || activeTab === "comments" || activeTab === "logs") {
      const resource = activeTab === "logs" ? "labLogs" : activeTab;
      void loadAdminTable(resource, 0);
    }
  }, [activeTab, adminToken]);

  useEffect(() => {
    if (!adminToken || activeTab !== "terminal") {
      return undefined;
    }

    let isMounted = true;
    let socket;

    async function loadTerminalSnapshot() {
      try {
        const response = await fetch(`/api/admin/terminal?token=${encodeURIComponent(adminToken)}`);
        if (!response.ok) {
          throw new Error("Terminal snapshot failed");
        }

        const payload = await response.json();
        if (isMounted) {
          setTerminalOutput(payload.output || "backend-terminal> no_output_yet");
        }
      } catch {
        if (isMounted) {
          setTerminalOutput("backend-terminal> snapshot_unavailable");
        }
      }

      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(
        `${protocol}://${window.location.host}/api/admin/terminal-ws?token=${encodeURIComponent(adminToken)}`
      );
      socket.onmessage = (event) => {
        if (!isMounted) {
          return;
        }

        setTerminalOutput((current) => {
          const next = current ? `${current}\n${event.data}` : event.data;
          const lines = next.split("\n");
          return lines.slice(-250).join("\n");
        });
      };
    }

    void loadTerminalSnapshot();

    return () => {
      isMounted = false;
      if (socket) {
        socket.close();
      }
    };
  }, [activeTab, adminToken]);

  async function loadAdminPanel(defaultResource, defaultOffset) {
    if (!adminToken) {
      return;
    }

    setLoading(true);
    setError("");

    try {
      const [settingsResponse, statsResponse] = await Promise.all([
        fetch(`/api/admin/settings?token=${encodeURIComponent(adminToken)}`),
        fetch(`/api/admin/stats?token=${encodeURIComponent(adminToken)}`)
      ]);

      if (!settingsResponse.ok || !statsResponse.ok) {
        throw new Error("Unauthorized");
      }

      const [settingsData, statsData] = await Promise.all([settingsResponse.json(), statsResponse.json()]);

      setSettings(settingsData.settings);
      setStats(statsData);
      await loadAdminTable(defaultResource, defaultOffset, true);
    } catch {
      setError("Admin data could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  async function loadAdminTable(resource, offset = 0, silent = false) {
    if (!adminToken) {
      return;
    }

    if (!silent) {
      setTableLoading(true);
    }

    try {
      const response = await fetch(
        `/api/admin/data?resource=${encodeURIComponent(resource)}&limit=10&offset=${offset}&token=${encodeURIComponent(adminToken)}`
      );

      if (!response.ok) {
        throw new Error("Table load failed");
      }

      const payload = await response.json();
      setTableState(payload.data);
    } catch {
      setError("Admin table data could not be loaded.");
    } finally {
      if (!silent) {
        setTableLoading(false);
      }
    }
  }

  function updateSetting(key, value) {
    setSettings((current) => ({
      ...current,
      [key]: value
    }));
  }

  async function saveSettings() {
    if (!settings) {
      return;
    }

    setSaving(true);
    setError("");

    try {
      const response = await fetch(`/api/admin/settings?token=${encodeURIComponent(adminToken)}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          protectionEnabled: settings.protection_enabled,
          mlEnabled: settings.ml_enabled,
          dlEnabled: settings.dl_enabled,
          blockThreshold: Number(settings.block_threshold)
        })
      });

      if (!response.ok) {
        throw new Error("Save failed");
      }

      const payload = await response.json();
      setSettings(payload.settings);
      await loadAdminPanel(tableState.resource, tableState.pagination?.offset ?? 0);
    } catch {
      setError("Security settings could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="admin-shell">
      <header className="admin-topbar">
        <div>
          <p className="admin-kicker">Admin Panel</p>
          <h1>Website security control center</h1>
        </div>
        <div className="admin-actions">
          <button className="admin-button ghost" type="button" onClick={() => navigate("lab")}>
            <LayoutPanelLeft size={18} />
            <span>Lab</span>
          </button>
          <button
            className="admin-button"
            type="button"
            onClick={() => void loadAdminPanel(tableState.resource, tableState.pagination?.offset ?? 0)}
          >
            <RefreshCw size={18} />
            <span>Refresh</span>
          </button>
        </div>
      </header>

      <nav className="admin-tabs" aria-label="Admin sections">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={`admin-tab ${activeTab === tab.id ? "is-active" : ""}`}
              type="button"
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon size={16} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>

      {error ? <p className="admin-error">{error}</p> : null}

      {loading ? (
        <section className="admin-panel">
          <p className="admin-muted">Loading admin data...</p>
        </section>
      ) : (
        <>
          {activeTab === "overview" ? <OverviewPanel settings={settings} stats={stats} /> : null}
          {activeTab === "controls" ? (
            <ControlsPanel
              saving={saving}
              settings={settings}
              onChange={updateSetting}
              onSave={saveSettings}
            />
          ) : null}
          {activeTab === "users" ? (
            <TablePanel
              columns={["id", "username", "password", "role"]}
              loading={tableLoading}
              pagination={tableState.pagination}
              resource="users"
              rows={tableState.resource === "users" ? tableState.rows : []}
              onPageChange={loadAdminTable}
              title="Users"
            />
          ) : null}
          {activeTab === "comments" ? (
            <TablePanel
              columns={["id", "author", "content", "created_at"]}
              loading={tableLoading}
              pagination={tableState.pagination}
              resource="comments"
              rows={tableState.resource === "comments" ? tableState.rows : []}
              onPageChange={loadAdminTable}
              title="Comments"
            />
          ) : null}
          {activeTab === "logs" ? (
            <TablePanel
              columns={[
                "id",
                "input",
                "detected_type",
                "blocked",
                "model_score",
                "model_time_ms",
                "endpoint_time_ms",
                "created_at"
              ]}
              loading={tableLoading}
              pagination={tableState.pagination}
              resource="labLogs"
              rows={tableState.resource === "labLogs" ? tableState.rows : []}
              onPageChange={loadAdminTable}
              title="Attack logs"
            />
          ) : null}
          {activeTab === "terminal" ? <TerminalPanel output={terminalOutput} /> : null}
        </>
      )}
    </main>
  );
}

function OverviewPanel({ settings, stats }) {
  const attackSummary = stats?.attackSummary ?? {};
  const tableCounts = stats?.tableCounts ?? {};

  return (
    <section className="admin-panel admin-grid">
      <article className="admin-card">
        <div className="admin-card-head">
          <ShieldCheck size={18} />
          <h2>Security posture</h2>
        </div>
        <div className="metric-grid">
          <Metric label="Mode" value={settings?.labMode ?? "unknown"} />
          <Metric label="Protection" value={settings?.protection_enabled ? "On" : "Off"} />
          <Metric label="ML detector" value={settings?.ml_enabled ? "Enabled" : "Disabled"} />
          <Metric label="DL detector" value={settings?.dl_enabled ? "Enabled" : "Disabled"} />
        </div>
      </article>

      <article className="admin-card">
        <div className="admin-card-head">
          <BarChart3 size={18} />
          <h2>Attack summary</h2>
        </div>
        <div className="metric-grid">
          <Metric label="Total attacks" value={attackSummary.totalAttacks ?? 0} />
          <Metric label="Blocked" value={attackSummary.blocked ?? 0} />
          <Metric label="Allowed" value={attackSummary.allowed ?? 0} />
          <Metric label="Avg model ms" value={attackSummary.avgModelTimeMs ?? 0} />
        </div>
      </article>

      <article className="admin-card">
        <div className="admin-card-head">
          <Database size={18} />
          <h2>Data inventory</h2>
        </div>
        <div className="metric-grid">
          <Metric label="Users" value={tableCounts.users ?? 0} />
          <Metric label="Comments" value={tableCounts.comments ?? 0} />
          <Metric label="Logs" value={tableCounts.labLogs ?? 0} />
          <Metric label="Requests" value={attackSummary.totalRequests ?? 0} />
        </div>
      </article>
    </section>
  );
}

function ControlsPanel({ settings, onChange, onSave, saving }) {
  if (!settings) {
    return null;
  }

  return (
    <section className="admin-panel admin-grid">
      <article className="admin-card">
        <div className="admin-card-head">
          <Shield size={18} />
          <h2>Protection controls</h2>
        </div>
        <div className="toggle-stack">
          <ToggleRow
            checked={settings.protection_enabled}
            description="Block payloads when detector score exceeds threshold."
            label="Website protection"
            onChange={(checked) => onChange("protection_enabled", checked)}
          />
          <ToggleRow
            checked={settings.ml_enabled}
            description="Use the lightweight ML detector in classification."
            label="Machine learning detector"
            onChange={(checked) => onChange("ml_enabled", checked)}
          />
          <ToggleRow
            checked={settings.dl_enabled}
            description="Use the deep learning placeholder detector in classification."
            label="Deep learning detector"
            onChange={(checked) => onChange("dl_enabled", checked)}
          />
        </div>
      </article>

      <article className="admin-card">
        <div className="admin-card-head">
          <BrainCircuit size={18} />
          <h2>Threshold</h2>
        </div>
        <div className="range-stack">
          <label className="range-label" htmlFor="block-threshold">
            Block threshold
          </label>
          <input
            id="block-threshold"
            className="range-input"
            max="1"
            min="0"
            onChange={(event) => onChange("block_threshold", Number(event.target.value))}
            step="0.01"
            type="range"
            value={settings.block_threshold}
          />
          <p className="range-value">{Number(settings.block_threshold).toFixed(2)}</p>
        </div>
        <button className="admin-button save" disabled={saving} type="button" onClick={() => void onSave()}>
          <span>{saving ? "Saving..." : "Save changes"}</span>
        </button>
      </article>
    </section>
  );
}

function ToggleRow({ checked, description, label, onChange }) {
  return (
    <label className="toggle-row">
      <div>
        <strong>{label}</strong>
        <p>{description}</p>
      </div>
      <input checked={checked} onChange={(event) => onChange(event.target.checked)} type="checkbox" />
    </label>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric-box">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function TablePanel({ columns, rows, title, resource, pagination, onPageChange, loading }) {
  return (
    <section className="admin-panel">
      <div className="admin-card-head table-head">
        <Database size={18} />
        <h2>{title}</h2>
      </div>
      <div className="table-toolbar">
        <p className="admin-muted">
          {pagination ? `Page ${pagination.page} of ${pagination.pageCount} | ${pagination.total} records` : "Loading table metadata..."}
        </p>
        <div className="table-pagination">
          <button
            className="admin-button ghost"
            disabled={!pagination?.hasPrevious || loading}
            type="button"
            onClick={() => onPageChange(resource, Math.max(0, (pagination?.offset ?? 0) - (pagination?.limit ?? 10)))}
          >
            Previous
          </button>
          <button
            className="admin-button ghost"
            disabled={!pagination?.hasNext || loading}
            type="button"
            onClick={() => onPageChange(resource, (pagination?.offset ?? 0) + (pagination?.limit ?? 10))}
          >
            Next
          </button>
        </div>
      </div>
      <div className="table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td className="empty-table" colSpan={columns.length}>
                  Loading records...
                </td>
              </tr>
            ) : rows.length ? (
              rows.map((row) => (
                <tr key={`${title}-${row.id}`}>
                  {columns.map((column) => (
                    <td key={`${row.id}-${column}`}>{String(row[column])}</td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td className="empty-table" colSpan={columns.length}>
                  No records available.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function TerminalPanel({ output }) {
  const terminalRef = useRef(null);

  useEffect(() => {
    if (!terminalRef.current) {
      return;
    }

    terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
  }, [output]);

  return (
    <section className="admin-panel">
      <div className="admin-card-head table-head">
        <TerminalSquare size={18} />
        <h2>Backend terminal</h2>
      </div>
      <div className="terminal-panel" ref={terminalRef}>
        <pre>{output}</pre>
      </div>
    </section>
  );
}

export default AdminPage;
