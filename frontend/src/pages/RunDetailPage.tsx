import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { artifactFileUrl, fetchTextFile, getRunDetail, RunDetail, RunFile } from "../qf";

function isImage(p: string) {
  const s = p.toLowerCase();
  return s.endsWith(".png") || s.endsWith(".jpg") || s.endsWith(".jpeg") || s.endsWith(".webp");
}

function isText(p: string) {
  const s = p.toLowerCase();
  return s.endsWith(".json") || s.endsWith(".xml") || s.endsWith(".txt") || s.endsWith(".log");
}

type GroupKey = "steps" | "http" | "meta" | "other";

function groupOf(path: string): GroupKey {
  const p = path.toLowerCase();

  // 你现在 steps 是平铺的 step_000.png；未来也可能变成 steps/step_000.png
  if (p.startsWith("steps/") || p.startsWith("step_")) return "steps";

  // smoke/http 等证据
  if (p.startsWith("http/") || p.includes("/http/")) return "http";

  // 元数据文件
  if (p === "summary.json" || p.endsWith("/summary.json") || p === "junit.xml" || p.endsWith("/junit.xml")) return "meta";

  return "other";
}

function groupTitle(g: GroupKey) {
  switch (g) {
    case "steps":
      return "Steps";
    case "http":
      return "HTTP Evidence";
    case "meta":
      return "Meta";
    case "other":
      return "Other";
  }
}

function pickDefaultFile(files: RunFile[]): RunFile | null {
  if (!files.length) return null;

  // 优先 step_000.png
  const step0 = files.find((f) => f.path.toLowerCase() === "step_000.png" || f.path.toLowerCase().endsWith("/step_000.png"));
  if (step0) return step0;

  // 其次 step_001.png
  const step1 = files.find((f) => f.path.toLowerCase() === "step_001.png" || f.path.toLowerCase().endsWith("/step_001.png"));
  if (step1) return step1;

  return files[0];
}

export default function RunDetailPage() {
  const { runId } = useParams();
  const rid = runId ? decodeURIComponent(runId) : "";

  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const [selected, setSelected] = useState<RunFile | null>(null);
  const [textPreview, setTextPreview] = useState<string>("");

  // 分组折叠状态（默认展开）
  const [open, setOpen] = useState<Record<GroupKey, boolean>>({
    steps: true,
    http: true,
    meta: true,
    other: true,
  });

  useEffect(() => {
    if (!rid) return;
    let alive = true;

    getRunDetail(rid)
      .then((d) => {
        if (!alive) return;
        setDetail(d);
        setErr(null);
        setSelected(pickDefaultFile(d.files));
      })
      .catch((e) => {
        if (!alive) return;
        setErr(String(e));
      });

    return () => {
      alive = false;
    };
  }, [rid]);

  const grouped = useMemo(() => {
    const files = detail?.files ?? [];
    const buckets: Record<GroupKey, RunFile[]> = { steps: [], http: [], meta: [], other: [] };

    for (const f of files) buckets[groupOf(f.path)].push(f);

    // 组内排序：steps 按 step_000/001…；其它按路径字典序
    buckets.steps.sort((a, b) => a.path.localeCompare(b.path));
    buckets.http.sort((a, b) => a.path.localeCompare(b.path));
    buckets.meta.sort((a, b) => a.path.localeCompare(b.path));
    buckets.other.sort((a, b) => a.path.localeCompare(b.path));

    return buckets;
  }, [detail]);

  const selectedUrl = useMemo(() => {
    if (!selected) return "";
    return artifactFileUrl(rid, selected.path);
  }, [rid, selected]);

  useEffect(() => {
    if (!selected) return;

    if (!isText(selected.path)) {
      setTextPreview("");
      return;
    }

    fetchTextFile(rid, selected.path)
      .then((t) => {
        // JSON 美化
        if (selected.path.toLowerCase().endsWith(".json")) {
          try {
            const obj = JSON.parse(t);
            setTextPreview(JSON.stringify(obj, null, 2));
            return;
          } catch {
            // ignore
          }
        }
        setTextPreview(t);
      })
      .catch((e) => setTextPreview(String(e)));
  }, [rid, selected]);

  function renderFileButton(f: RunFile) {
    const active = selected?.path === f.path;
    return (
      <div key={f.path} style={{ marginBottom: 8 }}>
        <button
          style={{
            width: "100%",
            textAlign: "left",
            padding: 8,
            border: "1px solid #444",
            background: active ? "#222" : "transparent",
            cursor: "pointer",
          }}
          onClick={() => setSelected(f)}
        >
          {f.path} <span style={{ opacity: 0.7 }}>({f.size})</span>
        </button>
      </div>
    );
  }

  function renderGroup(g: GroupKey, files: RunFile[]) {
    if (!files.length) return null;

    return (
      <div style={{ marginBottom: 12 }}>
        <button
          style={{
            width: "100%",
            textAlign: "left",
            padding: "8px 10px",
            border: "1px solid #333",
            background: "transparent",
            cursor: "pointer",
            fontWeight: 600,
          }}
          onClick={() => setOpen((s) => ({ ...s, [g]: !s[g] }))}
        >
          {open[g] ? "▼" : "▶"} {groupTitle(g)} <span style={{ opacity: 0.7 }}>({files.length})</span>
        </button>

        {open[g] && <div style={{ padding: "8px 0" }}>{files.map(renderFileButton)}</div>}
      </div>
    );
  }

  return (
    <div style={{ padding: 16, display: "grid", gridTemplateColumns: "360px 1fr", gap: 16 }}>
      <div>
        <div style={{ marginBottom: 12 }}>
          <Link to="/runs">← Back</Link>
        </div>

        <h3 style={{ margin: "8px 0" }}>{rid}</h3>
        {err && <div style={{ color: "crimson" }}>{err}</div>}

        {detail && (
          <div style={{ fontSize: 12, opacity: 0.9, lineHeight: 1.6 }}>
            <div>kind: {detail.summary.kind}</div>
            <div>ok: {detail.summary.ok === null ? "-" : String(detail.summary.ok)}</div>
            <div>started_at: {detail.summary.started_at ?? "-"}</div>
            <div>files: {detail.files.length}</div>
          </div>
        )}

        <hr />

        <div style={{ maxHeight: "72vh", overflow: "auto" }}>
          {renderGroup("steps", grouped.steps)}
          {renderGroup("http", grouped.http)}
          {renderGroup("meta", grouped.meta)}
          {renderGroup("other", grouped.other)}
        </div>
      </div>

      <div>
        <h3 style={{ marginTop: 0 }}>Preview</h3>

        {!selected && <div>no file selected</div>}

        {selected && (
          <div style={{ marginBottom: 8 }}>
            <a href={selectedUrl} target="_blank" rel="noreferrer">
              open / download
            </a>
          </div>
        )}

        {selected && isImage(selected.path) && (
          <img src={selectedUrl} alt={selected.path} style={{ maxWidth: "100%" }} />
        )}

        {selected && isText(selected.path) && (
          <pre style={{ whiteSpace: "pre-wrap", border: "1px solid #444", padding: 12, margin: 0 }}>
            {textPreview || "loading..."}
          </pre>
        )}

        {selected && !isImage(selected.path) && !isText(selected.path) && (
          <div style={{ opacity: 0.8 }}>no inline preview for this file type</div>
        )}
      </div>
    </div>
  );
}
