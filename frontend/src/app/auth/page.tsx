"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

type Tab = "login" | "signup";

export default function AuthPage() {
    const { signInWithGoogle, signInWithEmail, signUpWithEmail, user, loading, getIdToken } = useAuth();
    const router = useRouter();
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const [tab, setTab] = useState<Tab>("login");
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [busy, setBusy] = useState(false);

    // Redirect authenticated users based on role immediately.
    useEffect(() => {
        let cancelled = false;
        (async () => {
            if (loading || !user) return;
            try {
                const token = await getIdToken();
                if (!token) {
                    if (!cancelled) router.replace("/onboarding/institute");
                    return;
                }
                const res = await fetch(`${API_URL}/auth/me`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                const data = await res.json();
                const role = String(data?.role || "").toLowerCase();
                if (cancelled) return;
                if (role === "teacher") {
                    router.replace("/teacher/dashboard");
                    return;
                }
                if (role === "admin" || role === "superadmin") {
                    router.replace("/admin/dashboard");
                    return;
                }
                router.replace("/onboarding/institute");
            } catch {
                if (!cancelled) router.replace("/onboarding/institute");
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [loading, user, getIdToken, router, API_URL]);

    if (!loading && user) {
        return null;
    }

    const friendlyError = (code: string) => {
        const map: Record<string, string> = {
            "auth/email-already-in-use": "An account with this email already exists.",
            "auth/invalid-email": "Please enter a valid email address.",
            "auth/weak-password": "Password must be at least 6 characters.",
            "auth/user-not-found": "No account found with this email.",
            "auth/wrong-password": "Incorrect password.",
            "auth/invalid-credential": "Invalid email or password.",
            "auth/too-many-requests": "Too many attempts. Please try again later.",
        };
        return map[code] || "Something went wrong. Please try again.";
    };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);
        if (tab === "signup" && password !== confirmPassword) {
            setError("Passwords do not match.");
            return;
        }
        setBusy(true);
        try {
            if (tab === "login") await signInWithEmail(email, password);
            else await signUpWithEmail(name, email, password);
        } catch (err: unknown) {
            const code = typeof err === "object" && err && "code" in err ? String((err as { code?: string }).code || "") : "";
            setError(friendlyError(code));
        } finally {
            setBusy(false);
        }
    };

    const handleGoogle = async () => {
        setError(null);
        setBusy(true);
        try { await signInWithGoogle(); }
        catch (err: unknown) {
            const code = typeof err === "object" && err && "code" in err ? String((err as { code?: string }).code || "") : "";
            setError(friendlyError(code));
        }
        finally { setBusy(false); }
    };

    const isLogin = tab === "login";

    return (
        <div className="gw-root">
            {/* Background effects */}
            <div className="gw-noise" />
            <div className="gw-blob gw-blob-grey" />
            <div className="gw-blob gw-blob-teal" />

            {/* Header */}
            <header className="gw-header">
                <div className="gw-logo-box">
                    <span className="material-symbols-outlined">navigation</span>
                </div>
                <span className="gw-logo-text">The Gateway</span>
            </header>

            {/* Main */}
            <main className="gw-main">
                <div className="gw-card">
                    {/* Title */}
                    <div className="gw-card-heading">
                        <h1>{isLogin ? "Welcome back" : "Create account"}</h1>
                        <p>{isLogin
                            ? "Please enter your details to sign in."
                            : "Start your learning journey today."}</p>
                    </div>

                    {/* Tab switcher */}
                    <div className="gw-tabs">
                        <button
                            type="button"
                            className={`gw-tab ${isLogin ? "gw-tab-active" : ""}`}
                            onClick={() => { setTab("login"); setError(null); }}
                        >Sign In</button>
                        <button
                            type="button"
                            className={`gw-tab ${!isLogin ? "gw-tab-active" : ""}`}
                            onClick={() => { setTab("signup"); setError(null); }}
                        >Sign Up</button>
                    </div>

                    {/* Form */}
                    <form className="gw-form" onSubmit={handleSubmit} noValidate>
                        {!isLogin && (
                            <div className="gw-field">
                                <label htmlFor="gw-name">Full Name</label>
                                <input
                                    id="gw-name"
                                    type="text"
                                    placeholder="Ada Lovelace"
                                    value={name}
                                    onChange={e => setName(e.target.value)}
                                    required
                                    autoComplete="name"
                                />
                            </div>
                        )}

                        <div className="gw-field">
                            <label htmlFor="gw-email">Email Address</label>
                            <input
                                id="gw-email"
                                type="email"
                                placeholder="name@example.com"
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                required
                                autoComplete="email"
                            />
                        </div>

                        <div className="gw-field">
                            <div className="gw-field-row">
                                <label htmlFor="gw-password">Password</label>
                                {isLogin && <a href="#" className="gw-forgot">Forgot Password?</a>}
                            </div>
                            <input
                                id="gw-password"
                                type="password"
                                placeholder="••••••••"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                required
                                autoComplete={isLogin ? "current-password" : "new-password"}
                            />
                        </div>

                        {!isLogin && (
                            <div className="gw-field">
                                <label htmlFor="gw-confirm">Confirm Password</label>
                                <input
                                    id="gw-confirm"
                                    type="password"
                                    placeholder="••••••••"
                                    value={confirmPassword}
                                    onChange={e => setConfirmPassword(e.target.value)}
                                    required
                                    autoComplete="new-password"
                                />
                            </div>
                        )}

                        {error && <div className="gw-error">{error}</div>}

                        <button type="submit" className="gw-submit" disabled={busy}>
                            {busy ? "Please wait..." : isLogin ? "Sign In" : "Create Account"}
                            {!busy && <span className="material-symbols-outlined">arrow_forward</span>}
                        </button>
                    </form>

                    {/* Divider */}
                    <div className="gw-divider"><span>OR</span></div>

                    {/* Google */}
                    <button type="button" className="gw-google" onClick={handleGoogle} disabled={busy}>
                        <svg viewBox="0 0 24 24" width="20" height="20">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                        </svg>
                        <span>Continue with Google</span>
                    </button>

                    {/* Switch tab footer */}
                    <p className="gw-switch-text">
                        {isLogin ? "Don't have an account?" : "Already have an account?"}
                        <button
                            type="button"
                            className="gw-switch-link"
                            onClick={() => { setTab(isLogin ? "signup" : "login"); setError(null); }}
                        >
                            {isLogin ? "Create an Account" : "Sign In"}
                        </button>
                    </p>
                </div>

                {/* Below-card label */}
                <p className="gw-tagline">Visual Interactive Learning Platform</p>
            </main>

            {/* Footer dots */}
            <footer className="gw-footer">
                <div className="gw-dot gw-dot-active" />
                <div className="gw-dot" />
                <div className="gw-dot" />
            </footer>
        </div>
    );
}
