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

// Separate inner component so useAuth/useRouter only render when header is visible
function HeaderInner() {
    const { user, signOut } = useAuth();
    const router = useRouter();

    const handleProfileClick = () => {
        if (!user) {
            router.push("/auth");
        }
        // If signed in, clicking the avatar could open a menu in future — no-op for now
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
                    <a href="#">Resources</a>
                    <a href="#">Curriculum</a>
                    <a href="#">Support</a>
                </nav>

                {/* Profile / Sign-in area */}
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
