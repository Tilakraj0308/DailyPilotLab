/**
 * Connector API client — typed functions for interacting with connector endpoints.
 *
 * Uses the same bearer token pattern as AuthContext.syncProfile.
 */

export interface ConnectorProvider {
    provider_id: number;
    provider_key: string;
    display_name: string;
    description: string;
    icon_url: string;
    connector_id: number | null;
    status: string;
    connected_at: string | null;
    error_message: string | null;
}

export interface ConnectorListResponse {
    connectors: ConnectorProvider[];
}

export interface StartConnectResponse {
    auth_url: string;
}

export interface ExchangeResponse {
    success: boolean;
    provider_key: string;
}

export interface DisconnectResponse {
    success: boolean;
    message: string;
}

export interface HealthResponse {
    connector_id: number;
    provider_key: string;
    healthy: boolean;
    reason: string;
}

const headers = (token: string) => ({
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
});

/**
 * List all available connector providers with the user's connection status.
 */
export async function getConnectors(
    apiUrl: string,
    token: string
): Promise<ConnectorListResponse> {
    const res = await fetch(`${apiUrl}/connectors`, { headers: headers(token) });
    if (!res.ok) throw new Error(`GET /connectors failed: ${res.status}`);
    return res.json();
}

/**
 * Start the OAuth flow for a provider. Returns the Google authorization URL.
 * @param providerSlug - e.g., "google-calendar" or "google-tasks"
 * @param deepLink - the URI scheme WebBrowser is listening for (e.g. exp://...)
 */
export async function startConnect(
    apiUrl: string,
    token: string,
    providerSlug: string,
    deepLink: string
): Promise<StartConnectResponse> {
    const res = await fetch(`${apiUrl}/connectors/${providerSlug}/start`, {
        method: "POST",
        headers: headers(token),
        body: JSON.stringify({ deep_link: deepLink }),
    });
    if (!res.ok) throw new Error(`POST /connectors/${providerSlug}/start failed: ${res.status}`);
    return res.json();
}



/**
 * Disconnect a connector by its ID.
 */
export async function disconnectConnector(
    apiUrl: string,
    token: string,
    connectorId: number
): Promise<DisconnectResponse> {
    const res = await fetch(`${apiUrl}/connectors/${connectorId}/disconnect`, {
        method: "POST",
        headers: headers(token),
    });
    if (!res.ok) throw new Error(`POST /connectors/${connectorId}/disconnect failed: ${res.status}`);
    return res.json();
}

/**
 * Check if a connector's stored credentials are still valid.
 */
export async function getConnectorHealth(
    apiUrl: string,
    token: string,
    connectorId: number
): Promise<HealthResponse> {
    const res = await fetch(`${apiUrl}/connectors/${connectorId}/health`, {
        headers: headers(token),
    });
    if (!res.ok) throw new Error(`GET /connectors/${connectorId}/health failed: ${res.status}`);
    return res.json();
}
