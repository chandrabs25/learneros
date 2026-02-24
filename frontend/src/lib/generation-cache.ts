const DEFAULT_TTL_MS = 15 * 60 * 1000;
const inflight = new Map<string, Promise<unknown>>();

type CacheEnvelope<T> = {
  expiresAt: number;
  payload: T;
};

function canUseSessionStorage(): boolean {
  return typeof window !== "undefined" && typeof window.sessionStorage !== "undefined";
}

function readCached<T>(key: string): T | null {
  if (!canUseSessionStorage()) return null;
  try {
    const raw = window.sessionStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as CacheEnvelope<T>;
    if (!parsed || typeof parsed.expiresAt !== "number") return null;
    if (Date.now() > parsed.expiresAt) {
      window.sessionStorage.removeItem(key);
      return null;
    }
    return parsed.payload;
  } catch {
    return null;
  }
}

function writeCached<T>(key: string, payload: T, ttlMs: number): void {
  if (!canUseSessionStorage()) return;
  try {
    const envelope: CacheEnvelope<T> = {
      expiresAt: Date.now() + Math.max(1000, ttlMs),
      payload,
    };
    window.sessionStorage.setItem(key, JSON.stringify(envelope));
  } catch {
    // Ignore quota/storage errors.
  }
}

export async function fetchGenerationJSON<T>(
  url: string,
  options: RequestInit = {},
  ttlMs: number = DEFAULT_TTL_MS
): Promise<T> {
  const key = `gen:${url}`;
  const cached = readCached<T>(key);
  if (cached !== null) return cached;

  const existing = inflight.get(key);
  if (existing) return existing as Promise<T>;

  const req = fetch(url, options).then(async (res) => {
    const data = await res.json();
    if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
    writeCached(key, data, ttlMs);
    return data as T;
  }).finally(() => {
    inflight.delete(key);
  });

  inflight.set(key, req);
  return req as Promise<T>;
}

