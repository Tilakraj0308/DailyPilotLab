/**
 * Typed API client for connector endpoints.
 *
 * All functions require a Supabase JWT access token.
 * Tokens are never stored or handled in the app —
 * only passed through to the backend via Authorization header.
 */

import { Platform } from "react-native";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ConnectorStatus = {
    provider: string;
    connected: boolean;
    provider_account_email: string | null;
    scopes: string[];
    expires_at: string | null;
    connected_at: string | null;
    last_sync_at: string | null;
    needs_reconnect: boolean;
};

export type CalendarEvent = {
    id: string;
    summary: string;
    start: string;
    end: string;
    location: string | null;
    status: string;
    is_all_day: boolean;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getApiUrl(): string {
    const envUrl = process.env.EXPO_PUBLIC_API_URL;
    if (!Platform.OS || Platform.OS === "web") {
        return envUrl || "http://localhost:8000";
    }
    if (envUrl) return envUrl;
    if (Platform.OS === "android") return "http://10.0.2.2:8000";
    return "http://localhost:8000";
}

async function apiFetch<T>(
    path: string,
    token: string,
    options: RequestInit = {}
): Promise<T> {
    const url = `${getApiUrl()}${path}`;
    const response = await fetch(url, {
        ...options,
        headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
    });

    if (!response.ok) {
        const body = await response.text();
        throw new Error(`API ${response.status}: ${body}`);
    }

    return response.json();
}

// ---------------------------------------------------------------------------
// Connector API Functions
// ---------------------------------------------------------------------------

/**
 * List all connectors for the authenticated user.
 */
export async function getConnectors(
    token: string
): Promise<ConnectorStatus[]> {
    const data = await apiFetch<{ connectors: ConnectorStatus[] }>(
        "/connectors",
        token
    );
    return data.connectors;
}

/**
 * Start the Google Calendar OAuth flow.
 * Returns the auth URL to open in the browser.
 */
export async function startGoogleCalendarConnect(
    token: string
): Promise<string> {
    const data = await apiFetch<{ auth_url: string }>(
        "/connectors/google/calendar/start",
        token
    );
    return data.auth_url;
}

/**
 * Get the connection status of Google Calendar.
 */
export async function getGoogleCalendarStatus(
    token: string
): Promise<ConnectorStatus> {
    return apiFetch<ConnectorStatus>(
        "/connectors/google/calendar/status",
        token
    );
}

/**
 * Disconnect Google Calendar.
 */
export async function disconnectGoogleCalendar(
    token: string
): Promise<void> {
    await apiFetch<{ status: string }>(
        "/connectors/google/calendar/disconnect",
        token,
        { method: "POST" }
    );
}

/**
 * Fetch upcoming calendar events.
*/
export async function getGoogleCalendarEvents(
    token: string,
    timeMin?: string,
    timeMax?: string
): Promise<CalendarEvent[]> {
    const params = new URLSearchParams();
    if (timeMin) params.set("time_min", timeMin);
    if (timeMax) params.set("time_max", timeMax);
    const qs = params.toString();
    const path = `/connectors/google/calendar/events${qs ? `?${qs}` : ""}`;

    const data = await apiFetch<{ events: CalendarEvent[]; synced_at: string }>(
        path,
        token
    );
    return data.events;
}