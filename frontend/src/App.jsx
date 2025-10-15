import React, { useEffect, useRef, useState } from "react";

/** ---- CONFIG ---- **/
const API_BASE = "http://127.0.0.1:8000";
const WS_URL = `${API_BASE.replace("http", "ws")}/ws/alerts`;
const alertsApi = (limit) => `${API_BASE}/alerts?limit=${limit}`;

/** Hook to manage alerts (WS + fallback polling) */
function useAlerts(initialLimit = 200) {
  const [alerts, setAlerts] = useState([]);
  const [status, setStatus] = useState("connecting"); // connecting | open | closed | error
  const [limit, setLimit] = useState(initialLimit);
  const wsRef = useRef(null);
  const pollRef = useRef(null);
  const pausedRef = useRef(false);

  // initial load + WS connect
  useEffect(() => {
    let shouldStop = false;

    async function fetchLatest() {
      try {
        const r = await fetch(alertsApi(limit));
        if (!r.ok) throw new Error("fetch failed");
        const data = await r.json();
        // newest last → reverse for newest first
        setAlerts(data.reverse());
      } catch {
        // ignore
      }
    }

    function startPolling() {
      if (pollRef.current) return;
      pollRef.current = setInterval(async () => {
        try {
          const r = await fetch(alertsApi(limit));
          if (!r.ok) return;
          const data = await r.json();
          if (!pausedRef.current) setAlerts(data.reverse());
        } catch {
          // ignore
        }
      }, 5000);
    }

    function connectWS() {
      setStatus("connecting");
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.addEventListener("open", () => {
        setStatus("open");
        // when WS is open, stop polling
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      });

      ws.addEventListener("message", (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (pausedRef.current) return;
          setAlerts((prev) => [msg, ...prev].slice(0, limit));
        } catch {
          // ignore malformed
        }
      });

      ws.addEventListener("close", () => {
        setStatus("closed");
        wsRef.current = null;
        if (!shouldStop) startPolling();
      });

      ws.addEventListener("error", () => {
        setStatus("error");
        // close will trigger polling
      });
    }

    // kick off
    fetchLatest();
    connectWS();

    return () => {
      shouldStop = true;
      if (wsRef.current) {
        try { wsRef.current.close(); } catch {}
        wsRef.current = null;
      }
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [limit]); // re-run if the limit changes

  /** Actions exposed to the component */
  const pause = () => (pausedRef.current = true);
  const resume = () => (pausedRef.current = false);
  const clearLocal = () => setAlerts([]);

  const refreshNow = async () => {
    try {
      const r = await fetch(alertsApi(limit));
      if (!r.ok) return;
      const data = await r.json();
      setAlerts(data.reverse());
    } catch {}
  };

  const clearServer = async () => {
    try {
      // delete from backend database
      await fetch(`${API_BASE}/alerts`, { method: "DELETE" });
    } catch {
      // ignore network errors
    }
    // clear local list as well
    clearLocal();
  };

  return {
    alerts,
    status,
    limit,
    setLimit,
    pause,
    resume,
    clearLocal,
    clearServer,
    refreshNow,
  };
}

/** Table row for a single alert */
function AlertRow({ a }) {
  const ts = a.ts ? new Date(a.ts).toLocaleString() : "";
  // details can be a string (JSON) or an object; normalize it for display
  const detailsText =
    typeof a.details === "string" ? a.details : JSON.stringify(a.details ?? {}, null, 2);

  return (
    <tr>
      <td>{a.id}</td>
      <td title={a.ts || ""}>{ts}</td>
      <td>{a.type}</td>
      <td>{a.src || "-"}</td>
      <td><pre className="small-pre">{detailsText}</pre></td>
    </tr>
  );
}

/** Main component */
export default function App() {
  const {
    alerts,
    status,
    limit,
    setLimit,
    pause,
    resume,
    clearServer,
    refreshNow,
  } = useAlerts(200);

  const [paused, setPaused] = useState(false);

  const onTogglePause = () => {
    setPaused((p) => {
      const next = !p;
      next ? pause() : resume();
      return next;
    });
  };

  const onClear = async () => {
    // Optional confirmation; comment this out if you don’t want it
    const ok = window.confirm("Delete all alerts from the database and clear the view?");
    if (!ok) return;
    await clearServer();
    // immediately refresh to show empty state (in case polling or ws refills)
    await refreshNow();
  };

  return (
    <div className="container">
      <header className="topbar">
        <h1>🧠 Intrusion Detection Dashboard</h1>
        <div className={`status ${status}`}>WS: <strong>{status}</strong></div>
      </header>

      <section className="controls">
        <div className="group">
          <label>History limit&nbsp;</label>
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            title="How many recent alerts to keep/show"
          >
            {[50, 100, 200, 500, 1000].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>

        <div className="group">
          <button onClick={onTogglePause}>{paused ? "Resume" : "Pause"}</button>
          <button onClick={refreshNow} title="Fetch latest from server">Refresh</button>
          <button className="danger" onClick={onClear} title="Delete all alerts from DB + UI">
            Clear
          </button>
        </div>

        <div className="group meta">
          <span>Total shown: <strong>{alerts.length}</strong></span>
        </div>
      </section>

      <main>
        <table className="alerts-table">
          <thead>
            <tr>
              <th style={{width:80}}>ID</th>
              <th style={{width:220}}>Time</th>
              <th style={{width:120}}>Type</th>
              <th style={{width:160}}>Source</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {alerts.length === 0 ? (
              <tr><td colSpan={5} style={{textAlign:"center", opacity:0.6}}>No alerts</td></tr>
            ) : (
              alerts.map((a) => <AlertRow key={`${a.id}-${a.ts || ""}`} a={a} />)
            )}
          </tbody>
        </table>
      </main>

      <footer>
        <small>
          API: {API_BASE} &nbsp;|&nbsp; WS: {WS_URL}
        </small>
      </footer>
    </div>
  );
}
