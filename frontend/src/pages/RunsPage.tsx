import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import orchestrationsApi, { RunSummary } from "../api/orchestrations";

/**
 * Runs 列表页面
 * 
 * 使用 Orchestrations API (UUID runs) 作为数据源
 * Legacy runs (run_<TS>) 已废弃
 */
export default function RunsPage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [q, setQ] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;

    orchestrationsApi.listRuns({ limit: 200, offset: 0 })
      .then((data) => {
        if (!alive) return;
        setRuns(data.runs);
        setErr(null);
      })
      .catch((e) => {
        if (!alive) return;
        setErr(`Error: ${String(e)}`);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });

    return () => {
      alive = false;
    };
  }, []);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return runs
      .filter((r) => (needle ? r.run_id.toLowerCase().includes(needle) : true))
      .sort((a, b) => (b.started_at ?? b.run_id).localeCompare(a.started_at ?? a.run_id));
  }, [runs, q]);

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ marginTop: 0 }}>Orchestration Runs</h2>

      <div style={{ margin: "12px 0" }}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search run_id..."
          style={{ width: 360, padding: 8 }}
        />
      </div>

      {err && <div style={{ color: "crimson", marginBottom: 12 }}>{err}</div>}
      {loading && <div style={{ color: "#888" }}>Loading...</div>}

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid #333" }}>
            <th align="left">run_id</th>
            <th align="left">decision</th>
            <th align="left">tools</th>
            <th align="left">started_at</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((r) => (
            <tr key={r.run_id} style={{ borderTop: "1px solid #333" }}>
              <td style={{ padding: "8px 0" }}>
                <Link to={`/runs/${encodeURIComponent(r.run_id)}`}>{r.run_id.slice(0, 8)}...</Link>
              </td>
              <td>
                <span style={{
                  color: r.decision === "PASS" ? "green" : r.decision === "FAIL" ? "red" : "#888"
                }}>
                  {r.decision ?? "-"}
                </span>
              </td>
              <td>{r.tool_count}</td>
              <td>{r.started_at ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

