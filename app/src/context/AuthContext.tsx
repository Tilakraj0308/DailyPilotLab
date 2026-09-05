import React, { createContext, useContext, useEffect, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Session, User } from "@supabase/supabase-js";
import { supabase } from "../lib/supabase";
import { getApiUrl } from "../lib/api";

interface AuthContextType {
    session: Session | null;
    user: User | null;
    isLoading: boolean;
    onboardingCompleted: boolean;
    isAdmin: boolean;
    personalState: Record<string, any>;
    setOnboardingCompleted: (val: boolean) => void;
    signOut: () => Promise<void>;
    updatePersonalState: (newState: Record<string, any>) => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
    session: null,
    user: null,
    isLoading: true,
    onboardingCompleted: false,
    isAdmin: false,
    personalState: {},
    setOnboardingCompleted: () => {},
    signOut: async () => { },
    updatePersonalState: async () => { },
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [session, setSession] = useState<Session | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [onboardingCompleted, setOnboardingCompleted] = useState(false);
    const [isAdmin, setIsAdmin] = useState(false);
    const [personalState, setPersonalState] = useState<Record<string, any>>({});

    useEffect(() => {
        // Get the initial session
        supabase.auth.getSession().then(async ({ data: { session } }) => {
            setSession(session);
            if (session) {
                await syncProfile(session);
            }
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
            if (!session) {
                // Reset onboarding state on sign out
                setOnboardingCompleted(false);
                setIsAdmin(false);
                setPersonalState({});
            }
        });

        return () => subscription.unsubscribe();
    }, []);

    /**
     * Call the backend /auth/profile endpoint to ensure the user
     * exists in public.users (auto-creates on first call).
     * Also reads onboarding_completed and personal_state from the response.
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
                return;
            }

            const data = await response.json();
            if (data?.user) {
                setOnboardingCompleted(data.user.onboarding_completed ?? false);
                setIsAdmin(data.user.is_admin ?? false);
                setPersonalState(data.user.personal_state ?? {});
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
        await AsyncStorage.removeItem("@onboarding_draft");
        await supabase.auth.signOut();
        setSession(null);
    };

    const updatePersonalState = async (newState: Record<string, any>) => {
        const mergedState = { ...personalState, ...newState };
        setPersonalState(mergedState);

        try {
            const apiUrl = getApiUrl();
            const response = await fetch(`${apiUrl}/auth/profile/personal_state`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${session?.access_token}`,
                },
                body: JSON.stringify({ personal_state: mergedState }),
            });
            if (!response.ok) {
                console.error("Failed to update personal state on server");
            }
        } catch (e) {
            console.error("Error updating personal state:", e);
        }
    };

    return (
        <AuthContext.Provider
            value={{
                session,
                user: session?.user ?? null,
                isLoading,
                onboardingCompleted,
                isAdmin,
                personalState,
                setOnboardingCompleted,
                signOut,
                updatePersonalState,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);
