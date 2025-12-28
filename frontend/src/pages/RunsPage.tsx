import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { listRuns, RunSummary } from "../qf";

export default function RunsPage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [q, setQ] = useState("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;

    listRuns(200, 0)
      .then((data) => {
        if (!alive) return;
        setRuns(data);
        setErr(null); // 关键：成功后清除错误
      })
      .catch((e) => {
        if (!alive) return;
        setErr(`Error: ${String(e)}`);
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
      <h2 style={{ marginTop: 0 }}>Runs</h2>

      <div style={{ margin: "12px 0" }}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search run_id..."
          style={{ width: 360, padding: 8 }}
        />
      </div>

      {err && <div style={{ color: "crimson", marginBottom: 12 }}>{err}</div>}

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid #333" }}>
            <th align="left">run_id</th>
            <th align="left">kind</th>
            <th align="left">ok</th>
            <th align="left">started_at</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((r) => (
            <tr key={r.run_id} style={{ borderTop: "1px solid #333" }}>
              <td style={{ padding: "8px 0" }}>
                <Link to={`/runs/${encodeURIComponent(r.run_id)}`}>{r.run_id}</Link>
              </td>
              <td>{r.kind}</td>
              <td>{r.ok === null ? "-" : r.ok ? "true" : "false"}</td>
              <td>{r.started_at ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
