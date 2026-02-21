"use client";

import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const HIDDEN_NAV_ROUTES = ["/auth", "/onboarding"];

export function Header() {
    const pathname = usePathname();
    const hide = HIDDEN_NAV_ROUTES.some(
        (r) => pathname === r || pathname.startsWith(r + "/")
    ) || pathname.endsWith("/concepts");
    if (hide) return null;

    return <HeaderInner />;
}

function HeaderInner() {
    const { user, signOut } = useAuth();
    const router = useRouter();
    const pathname = usePathname();

    const handleProfileClick = () => {
        if (!user) router.push("/auth");
    };

    return (
        <header className="app-header">
            <div className="header-left">
                <a href="/" className="logo-box">
                    <span className="material-symbols-outlined">navigation</span>
                </a>
                <h2 className="header-title">The Hub</h2>
            </div>

            <div className="header-right">
                <nav className="header-nav">
                    <a href="#" className={pathname === "/resources" ? "header-nav-active" : ""}>Resources</a>
                    <a href="#" className={pathname === "/curriculum" ? "header-nav-active" : ""}>Curriculum</a>
                    <a href="/insights" className={pathname.startsWith("/insights") ? "header-nav-active" : ""}>Insights</a>
                    <a href="#" className={pathname === "/support" ? "header-nav-active" : ""}>Support</a>
                </nav>

                <button
                    onClick={() => router.push("/tutor")}
                    style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.4rem",
                        border: pathname.startsWith("/tutor") ? "1px solid #fb923c" : "none",
                        borderRadius: 10,
                        background: pathname.startsWith("/tutor") ? "#fff7ed" : "#ff7f50",
                        color: pathname.startsWith("/tutor") ? "#c2410c" : "white",
                        padding: "0.55rem 0.8rem",
                        fontWeight: 700,
                        cursor: "pointer",
                        fontFamily: "var(--font-display)",
                        fontSize: "0.82rem",
                    }}
                >
                    <span className="material-symbols-outlined" style={{ fontSize: 17 }}>smart_toy</span>
                    AI Tutor
                </button>

                <div
                    className={`header-profile-group ${!user ? "header-profile-clickable" : ""}`}
                    onClick={handleProfileClick}
                    title={!user ? "Sign in" : undefined}
                >
                    {user ? (
                        <>
                            <div className="profile-text">
                                <p className="profile-name">{user.displayName || "Student"}</p>
                                <p className="profile-role">
                                    <button
                                        className="header-signout-btn"
                                        onClick={(e) => { e.stopPropagation(); signOut(); }}
                                    >
                                        Sign Out
                                    </button>
                                </p>
                            </div>
                            <div className="profile-avatar-wrapper">
                                <div className="profile-avatar-circle">
                                    {user.photoURL ? (
                                        <img src={user.photoURL} alt={user.displayName || "Profile"} />
                                    ) : (
                                        <span className="profile-avatar-initials">
                                            {(user.displayName || user.email || "S")[0].toUpperCase()}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </>
                    ) : (
                        <>
                            <div className="profile-text">
                                <p className="profile-name">Sign In</p>
                                <p className="profile-role">to personalise</p>
                            </div>
                            <div className="profile-avatar-wrapper">
                                <div className="profile-avatar-circle profile-avatar-guest">
                                    <span className="material-symbols-outlined">person</span>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </header>
    );
}
