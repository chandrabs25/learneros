const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Make an authenticated API call to the backend.
 * Automatically attaches the Firebase ID token.
 */
export async function apiFetch(
    path: string,
    options: RequestInit = {},
    idToken?: string | null
): Promise<Response> {
    const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...(options.headers as Record<string, string>),
    };

    if (idToken) {
        headers["Authorization"] = `Bearer ${idToken}`;
    }

    return fetch(`${API_URL}${path}`, {
        ...options,
        headers,
    });
}
