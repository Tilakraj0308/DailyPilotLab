import React, { createContext, useContext, useEffect, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Session, User } from "@supabase/supabase-js";
import { supabase } from "../lib/supabase";
import { getApiUrl } from "../lib/api";

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
     * This is optional - app works fine without it if backend is unavailable.
     */
    const syncProfile = async (sess: Session) => {
        try {
            const apiUrl = getApiUrl();
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout

            const response = await fetch(`${apiUrl}/auth/profile`, {
                headers: { Authorization: `Bearer ${sess.access_token}` },
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                console.warn(`Profile sync returned ${response.status}, continuing anyway`);
            }
        } catch (e) {
            // Silently fail - profile sync is optional for local development
            if (e instanceof Error && e.name === 'AbortError') {
                console.debug("Profile sync timeout - backend may be unavailable");
            } else {
                console.debug("Profile sync skipped - backend may be unavailable");
            }
        }
    };

    const signOut = async () => {
        // Prevents the next account on this device from reusing a global chat session id.
        await AsyncStorage.removeItem("@chat_session_id");
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
