"use client";

import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
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
    const { user, signOut, role, loading } = useAuth();
    const router = useRouter();
    const pathname = usePathname();

    const handleProfileClick = () => {
        if (!user) router.push("/auth");
    };

    const isRoleKnownForNav = !user || !loading;
    const isTeacherRole = role === "teacher";
    const isAdminLike = role === "admin" || role === "superadmin";
    const isStudentLike = !user || role === "student" || loading;
    const profileHref = isStudentLike ? "/profile/settings" : "/teacher/profile/settings";
    const homeHref = !isRoleKnownForNav
        ? "/"
        : isAdminLike
            ? "/admin/dashboard"
            : isTeacherRole
                ? "/teacher/dashboard"
                : "/";

    return (
        <header className="app-header">
            <div className="header-left">
                <Link href={homeHref} className="logo-box">
                    <span className="material-symbols-outlined">navigation</span>
                </Link>
                <h2 className="header-title">The Hub</h2>
            </div>

            <div className="header-right">
                <nav className="header-nav">
                    {isRoleKnownForNav && isStudentLike && (
                        <>
                            <Link href="/" className={pathname === "/" ? "header-nav-active" : ""}>Home</Link>
                            <Link href="/insights" className={pathname.startsWith("/insights") ? "header-nav-active" : ""}>Insights</Link>
                        </>
                    )}
                    {isRoleKnownForNav && isTeacherRole && (
                        <Link href="/teacher/dashboard" className={pathname.startsWith("/teacher/dashboard") ? "header-nav-active" : ""}>Teacher Dashboard</Link>
                    )}
                    {isRoleKnownForNav && isAdminLike && (
                        <Link href="/admin/dashboard" className={pathname.startsWith("/admin/dashboard") ? "header-nav-active" : ""}>Admin Dashboard</Link>
                    )}
                    {isRoleKnownForNav && isStudentLike && (
                        <Link href="/tutor" className={pathname.startsWith("/tutor") ? "header-nav-active" : ""} style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem" }}>
                            <span className="material-symbols-outlined" style={{ fontSize: 17 }}>smart_toy</span>
                            AI Tutor
                        </Link>
                    )}
                </nav>

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
                                <Link
                                    href={profileHref}
                                    className="profile-avatar-circle"
                                    onClick={(e) => e.stopPropagation()}
                                    title="Profile Settings"
                                    style={{ cursor: "pointer", display: "block" }}
                                >
                                    {user.photoURL ? (
                                        <img src={user.photoURL} alt={user.displayName || "Profile"} />
                                    ) : (
                                        <span className="profile-avatar-initials">
                                            {(user.displayName || user.email || "S")[0].toUpperCase()}
                                        </span>
                                    )}
                                </Link>
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
