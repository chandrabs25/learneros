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
    signInWithGoogle: () => Promise<void>;
    signInWithEmail: (email: string, password: string) => Promise<void>;
    signUpWithEmail: (name: string, email: string, password: string) => Promise<void>;
    signOut: () => Promise<void>;
    getIdToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | null>(null);
const googleProvider = new GoogleAuthProvider();

const TO_ONBOARDING = "/onboarding/institute";

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (u) => {
            setUser(u);
            setLoading(false);
        });
        return unsubscribe;
    }, []);

    const signInWithGoogle = async () => {
        const result = await signInWithPopup(auth, googleProvider);
        if (result.user) router.push(TO_ONBOARDING);
    };

    const signInWithEmail = async (email: string, password: string) => {
        const result = await signInWithEmailAndPassword(auth, email, password);
        if (result.user) router.push(TO_ONBOARDING);
    };

    const signUpWithEmail = async (name: string, email: string, password: string) => {
        const result = await createUserWithEmailAndPassword(auth, email, password);
        if (result.user) {
            await updateProfile(result.user, { displayName: name });
            router.push(TO_ONBOARDING);
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
            value={{ user, loading, signInWithGoogle, signInWithEmail, signUpWithEmail, signOut, getIdToken }}
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
