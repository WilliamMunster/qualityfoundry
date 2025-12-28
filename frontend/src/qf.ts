export type RunSummary = {
  run_id: string;
  kind: string;
  artifact_dir: string;
  ok: boolean | null;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
};

export type RunFile = { path: string; size: number };

export type RunDetail = {
  summary: RunSummary;
  files: RunFile[];
};

const API_BASE = "/api/v1";

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

async function fetchJsonWithRetry<T>(
  url: string,
  opts?: { retries?: number; backoffMs?: number }
): Promise<T> {
  const retries = opts?.retries ?? 3;
  const backoffMs = opts?.backoffMs ?? 250;

  let lastErr: unknown = null;

  for (let i = 0; i <= retries; i++) {
    try {
      const resp = await fetch(url);

      // 对 500/502/503/504 做重试（开发期热重载窗口很常见）
      if (!resp.ok) {
        const retryable = [500, 502, 503, 504].includes(resp.status);
        if (retryable && i < retries) {
          await sleep(backoffMs * (i + 1));
          continue;
        }
        throw new Error(`HTTP ${resp.status}`);
      }

      return (await resp.json()) as T;
    } catch (e) {
      lastErr = e;
      // 网络错误（ECONNRESET）也重试
      if (i < retries) {
        await sleep(backoffMs * (i + 1));
        continue;
      }
    }
  }

  throw lastErr instanceof Error ? lastErr : new Error(String(lastErr));
}

async function fetchTextWithRetry(
  url: string,
  opts?: { retries?: number; backoffMs?: number }
): Promise<string> {
  const retries = opts?.retries ?? 3;
  const backoffMs = opts?.backoffMs ?? 250;

  let lastErr: unknown = null;

  for (let i = 0; i <= retries; i++) {
    try {
      const resp = await fetch(url);
      if (!resp.ok) {
        const retryable = [500, 502, 503, 504].includes(resp.status);
        if (retryable && i < retries) {
          await sleep(backoffMs * (i + 1));
          continue;
        }
        throw new Error(`HTTP ${resp.status}`);
      }
      return await resp.text();
    } catch (e) {
      lastErr = e;
      if (i < retries) {
        await sleep(backoffMs * (i + 1));
        continue;
      }
    }
  }

  throw lastErr instanceof Error ? lastErr : new Error(String(lastErr));
}

export async function listRuns(limit = 50, offset = 0): Promise<RunSummary[]> {
  return fetchJsonWithRetry<RunSummary[]>(
    `${API_BASE}/runs?limit=${limit}&offset=${offset}`,
    { retries: 4, backoffMs: 200 }
  );
}

export async function getRunDetail(runId: string): Promise<RunDetail> {
  return fetchJsonWithRetry<RunDetail>(
    `${API_BASE}/runs/${encodeURIComponent(runId)}`,
    { retries: 4, backoffMs: 200 }
  );
}

export function artifactFileUrl(runId: string, path: string): string {
  return `${API_BASE}/runs/${encodeURIComponent(runId)}/file?path=${encodeURIComponent(path)}`;
}

export async function fetchTextFile(runId: string, path: string): Promise<string> {
  return fetchTextWithRetry(artifactFileUrl(runId, path), { retries: 4, backoffMs: 200 });
}
