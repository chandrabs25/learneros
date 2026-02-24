import type { User } from "firebase/auth";

const TO_ONBOARDING = "/onboarding/institute";
const PENDING_NEXT_KEY = "learneros:auth:pending_next";
const SAFE_PREFIXES = [
  "/teacher/apply",
  "/onboarding/institute",
  "/profile/settings",
  "/teacher/profile/settings",
];

function defaultRouteForRole(role: string): string {
  if (role === "teacher") return "/teacher/dashboard";
  if (role === "admin" || role === "superadmin") return "/admin/dashboard";
  return TO_ONBOARDING;
}

function sanitizeNextPath(value?: string | null): string | null {
  if (!value) return null;
  const raw = String(value).trim();
  if (!raw) return null;
  if (!raw.startsWith("/") || raw.startsWith("//")) return null;
  if (/^[a-zA-Z][a-zA-Z\d+.-]*:/.test(raw)) return null;

  let parsed: URL;
  try {
    parsed = new URL(raw, "http://localhost");
  } catch {
    return null;
  }
  if (parsed.origin !== "http://localhost") return null;

  const path = parsed.pathname;
  const allowed = SAFE_PREFIXES.some((prefix) => path === prefix || path.startsWith(`${prefix}/`));
  if (!allowed) return null;
  return `${parsed.pathname}${parsed.search}${parsed.hash}`;
}

export function isSafeNextPath(value: string): boolean {
  return sanitizeNextPath(value) !== null;
}

export function setPendingNext(path?: string | null): void {
  if (typeof window === "undefined") return;
  const safe = sanitizeNextPath(path);
  if (!safe) return;
  window.sessionStorage.setItem(PENDING_NEXT_KEY, safe);
}

export function consumePendingNext(): string | null {
  if (typeof window === "undefined") return null;
  const stored = window.sessionStorage.getItem(PENDING_NEXT_KEY);
  if (stored) {
    window.sessionStorage.removeItem(PENDING_NEXT_KEY);
  }
  return sanitizeNextPath(stored);
}

export async function resolvePostLoginRoute(params: {
  user: User;
  nextFromQuery?: string | null;
  nextFromSession?: string | null;
}): Promise<string> {
  const queryNext = sanitizeNextPath(params.nextFromQuery);
  if (queryNext) return queryNext;

  const sessionNext = sanitizeNextPath(params.nextFromSession);
  if (sessionNext) return sessionNext;

  try {
    const tokenResult = await params.user.getIdTokenResult(true);
    const role = String(tokenResult.claims?.role || "student").toLowerCase();
    return defaultRouteForRole(role);
  } catch {
    return TO_ONBOARDING;
  }
}

