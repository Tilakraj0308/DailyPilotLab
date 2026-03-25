import React, { createContext, useContext, useEffect, useState } from "react";
import { Session, User } from "@supabase/supabase-js";
import { supabase } from "../lib/supabase";

interface AuthContextType {
    session: Session | null;
    user: User | null;
    isLoading: boolean;
    signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
    session: null,
    user: null,
    isLoading: true,
    signOut: async () => { },
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [session, setSession] = useState<Session | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        // Get the initial session
        supabase.auth.getSession().then(({ data: { session } }) => {
            setSession(session);
            if (session) syncProfile(session);
            setIsLoading(false);
        });

        // Listen to auth state changes (login, logout, token refresh)
        const {
            data: { subscription },
        } = supabase.auth.onAuthStateChange((_event, session) => {
            setSession(session);
            if (session && (_event === "SIGNED_IN" || _event === "TOKEN_REFRESHED")) {
                syncProfile(session);
            }
        });

        return () => subscription.unsubscribe();
    }, []);

    /**
     * Call the backend /auth/profile endpoint to ensure the user
     * exists in public.users (auto-creates on first call).
     */
    const syncProfile = async (sess: Session) => {
        try {
            await fetch(`${process.env.EXPO_PUBLIC_API_URL}/auth/profile`, {
                headers: { Authorization: `Bearer ${sess.access_token}` },
            });
        } catch (e) {
            console.error("Failed to sync profile:", e);
        }
    };

    const signOut = async () => {
        await supabase.auth.signOut();
        setSession(null);
    };

    return (
        <AuthContext.Provider
            value={{
                session,
                user: session?.user ?? null,
                isLoading,
                signOut,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);
