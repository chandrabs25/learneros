"use client";

import {
    createContext,
    useContext,
    useEffect,
    useState,
    type ReactNode,
} from "react";
import {
    onAuthStateChanged,
    signInWithPopup,
    signInWithRedirect,
    getRedirectResult,
    getAdditionalUserInfo,
    signOut as firebaseSignOut,
    GoogleAuthProvider,
    createUserWithEmailAndPassword,
    signInWithEmailAndPassword,
    updateProfile,
    type User,
} from "firebase/auth";
import { auth } from "@/lib/firebase";
import { useRouter } from "next/navigation";
import {
    consumePendingNext,
    resolvePostLoginRoute,
    setPendingNext,
} from "@/lib/auth-redirect";

interface AuthContextType {
    user: User | null;
    loading: boolean;
    role: string;
    signInWithGoogle: (nextPath?: string) => Promise<void>;
    signInWithEmail: (email: string, password: string, nextPath?: string) => Promise<void>;
    signUpWithEmail: (name: string, email: string, password: string, nextPath?: string) => Promise<void>;
    signOut: () => Promise<void>;
    getIdToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | null>(null);
const googleProvider = new GoogleAuthProvider();
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function provisionGraphIdentity(user: User): Promise<void> {
    const token = await user.getIdToken(true);
    const response = await fetch(`${API_URL}/auth/provision`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
        throw new Error(`Account provisioning failed (${response.status})`);
    }
}

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const [role, setRole] = useState("");
    const router = useRouter();

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (u) => {
            setUser(u);
            setLoading(false);
        });
        return unsubscribe;
    }, []);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            if (!user) {
                if (!cancelled) setRole("");
                return;
            }
            try {
                const tokenResult = await user.getIdTokenResult(true);
                if (!cancelled) setRole(String(tokenResult.claims?.role || "student").toLowerCase());
            } catch {
                if (!cancelled) setRole("student");
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [user]);

    useEffect(() => {
        // Handle Google redirect flow completion (popup fallback path).
        getRedirectResult(auth)
            .then(async (result) => {
                if (result?.user) {
                    if (getAdditionalUserInfo(result)?.isNewUser) {
                        await provisionGraphIdentity(result.user);
                    }
                    const route = await resolvePostLoginRoute({
                        user: result.user,
                        nextFromSession: consumePendingNext(),
                    });
                    router.replace(route);
                }
            })
            .catch(() => {
                // Ignore; normal auth state listener still governs UI.
            });
    }, [router]);

    const signInWithGoogle = async (nextPath?: string) => {
        if (nextPath) setPendingNext(nextPath);
        try {
            const result = await signInWithPopup(auth, googleProvider);
            if (result.user) {
                if (getAdditionalUserInfo(result)?.isNewUser) {
                    await provisionGraphIdentity(result.user);
                }
                const route = await resolvePostLoginRoute({
                    user: result.user,
                    nextFromQuery: nextPath || null,
                    nextFromSession: consumePendingNext(),
                });
                router.replace(route);
            }
        } catch (e: unknown) {
            const code = typeof e === "object" && e && "code" in e ? String((e as { code?: string }).code || "") : "";
            // Browsers can block/limit popup close/opener behavior (COOP). Redirect is more reliable.
            if (
                code.includes("popup") ||
                code.includes("cancelled") ||
                code.includes("operation-not-supported")
            ) {
                await signInWithRedirect(auth, googleProvider);
                return;
            }
            throw e;
        }
    };

    const signInWithEmail = async (email: string, password: string, nextPath?: string) => {
        if (nextPath) setPendingNext(nextPath);
        const result = await signInWithEmailAndPassword(auth, email, password);
        if (result.user) {
            const route = await resolvePostLoginRoute({
                user: result.user,
                nextFromQuery: nextPath || null,
                nextFromSession: consumePendingNext(),
            });
            router.replace(route);
        }
    };

    const signUpWithEmail = async (name: string, email: string, password: string, nextPath?: string) => {
        if (nextPath) setPendingNext(nextPath);
        const result = await createUserWithEmailAndPassword(auth, email, password);
        if (result.user) {
            await updateProfile(result.user, { displayName: name });
            await provisionGraphIdentity(result.user);
            const route = await resolvePostLoginRoute({
                user: result.user,
                nextFromQuery: nextPath || null,
                nextFromSession: consumePendingNext(),
            });
            router.replace(route);
        }
    };

    const signOut = async () => {
        await firebaseSignOut(auth);
        router.push("/");
    };

    const getIdToken = async (): Promise<string | null> => {
        if (!auth.currentUser) return null;
        return auth.currentUser.getIdToken();
    };

    return (
        <AuthContext.Provider
            value={{ user, loading, role, signInWithGoogle, signInWithEmail, signUpWithEmail, signOut, getIdToken }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) throw new Error("useAuth must be used within an AuthProvider");
    return context;
}
