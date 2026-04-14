import { getApiUrl } from "./api";

export const GOOGLE_CALENDAR_PROVIDER = "google_calendar";

export type ConnectorStatusItem = {
  provider_key: string;
  display_name: string;
  status: string;
  scopes: string[];
  connected_at: string | null;
  provider_email: string | null;
  error_message: string | null;
};

export type ConnectorListResponse = {
  connectors: ConnectorStatusItem[];
};

export type ConnectorStartResponse = {
  authorization_url: string;
  state: string;
};

export async function fetchConnectors(accessToken: string): Promise<ConnectorListResponse> {
  const res = await fetch(`${getApiUrl()}/connectors`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Failed to list connectors (${res.status})`);
  }
  return res.json();
}

export async function startConnectorOAuth(
  provider: string,
  accessToken: string,
  returnTo: string | undefined
): Promise<ConnectorStartResponse> {
  const res = await fetch(`${getApiUrl()}/connectors/${provider}/start`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ return_to: returnTo ?? null }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Failed to start connector (${res.status})`);
  }
  return res.json();
}

export async function disconnectConnector(
  provider: string,
  accessToken: string
): Promise<{ ok: boolean; provider_key: string }> {
  const res = await fetch(`${getApiUrl()}/connectors/${provider}/disconnect`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Failed to disconnect (${res.status})`);
  }
  return res.json();
}
