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
    signOut as firebaseSignOut,
    GoogleAuthProvider,
    createUserWithEmailAndPassword,
    signInWithEmailAndPassword,
    updateProfile,
    type User,
} from "firebase/auth";
import { auth } from "@/lib/firebase";
import { useRouter } from "next/navigation";

interface AuthContextType {
    user: User | null;
    loading: boolean;
    role: string;
    signInWithGoogle: () => Promise<void>;
    signInWithEmail: (email: string, password: string) => Promise<void>;
    signUpWithEmail: (name: string, email: string, password: string) => Promise<void>;
    signOut: () => Promise<void>;
    getIdToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | null>(null);
const googleProvider = new GoogleAuthProvider();

const TO_ONBOARDING = "/onboarding/institute";

async function getPostLoginRoute(user: User): Promise<string> {
    try {
        const tokenResult = await user.getIdTokenResult(true);
        const role = String(tokenResult.claims?.role || "student").toLowerCase();
        if (role === "teacher") return "/teacher/dashboard";
        if (role === "admin" || role === "superadmin") return "/admin/dashboard";
        return TO_ONBOARDING;
    } catch {
        return TO_ONBOARDING;
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
                    router.replace(await getPostLoginRoute(result.user));
                }
            })
            .catch(() => {
                // Ignore; normal auth state listener still governs UI.
            });
    }, [router]);

    const signInWithGoogle = async () => {
        try {
            const result = await signInWithPopup(auth, googleProvider);
            if (result.user) router.replace(await getPostLoginRoute(result.user));
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

    const signInWithEmail = async (email: string, password: string) => {
        const result = await signInWithEmailAndPassword(auth, email, password);
        if (result.user) router.replace(await getPostLoginRoute(result.user));
    };

    const signUpWithEmail = async (name: string, email: string, password: string) => {
        const result = await createUserWithEmailAndPassword(auth, email, password);
        if (result.user) {
            await updateProfile(result.user, { displayName: name });
            router.replace(await getPostLoginRoute(result.user));
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
