import { getApiUrl } from "./api";

export const GOOGLE_CALENDAR_PROVIDER = "google_calendar";
export const GOOGLE_TASKS_PROVIDER = "google_tasks";

export type ConnectorStatusItem = {
  provider_key: string;
  display_name: string;
  status: string;
  scopes: string[];
  connected_at: string | null;
  provider_email: string | null;
  error_message: string | null;
  /** Present for Google Tasks when a task list is selected */
  selected_resource_id?: string | null;
  selected_resource_name?: string | null;
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

// ── Google Tasks (list selection + CRUD against selected list) ─────────────

export type GoogleTaskListItem = {
  id: string;
  title: string;
};

export async function fetchGoogleTaskLists(accessToken: string): Promise<GoogleTaskListItem[]> {
  const res = await fetch(`${getApiUrl()}/connectors/google_tasks/lists`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Failed to load task lists (${res.status})`);
  }
  const data = await res.json();
  return data.items ?? [];
}

export async function selectGoogleTaskList(
  accessToken: string,
  taskListId: string,
  taskListTitle?: string | null
): Promise<void> {
  const res = await fetch(`${getApiUrl()}/connectors/google_tasks/select-list`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      task_list_id: taskListId,
      task_list_title: taskListTitle ?? null,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Failed to save task list (${res.status})`);
  }
}

/** Raw Google Tasks API task object (subset used in UI) */
export type GoogleTaskApiItem = {
  id?: string;
  title?: string;
  status?: string;
  notes?: string;
};

export async function fetchGoogleTasks(
  accessToken: string,
  showCompleted = false
): Promise<GoogleTaskApiItem[]> {
  const q = showCompleted ? "?show_completed=true" : "";
  const res = await fetch(`${getApiUrl()}/connectors/google_tasks/tasks${q}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Failed to load tasks (${res.status})`);
  }
  const data = await res.json();
  return data.items ?? [];
}

export async function createGoogleTask(
  accessToken: string,
  title: string,
  notes?: string | null
): Promise<GoogleTaskApiItem> {
  const res = await fetch(`${getApiUrl()}/connectors/google_tasks/tasks`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ title, notes: notes ?? null }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Failed to create task (${res.status})`);
  }
  return res.json();
}

export type UpdateGoogleTaskBody = {
  title?: string | null;
  notes?: string | null;
  status?: string | null;
  completed?: boolean | null;
};

export async function updateGoogleTask(
  accessToken: string,
  taskId: string,
  body: UpdateGoogleTaskBody
): Promise<GoogleTaskApiItem> {
  const res = await fetch(`${getApiUrl()}/connectors/google_tasks/tasks/${encodeURIComponent(taskId)}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Failed to update task (${res.status})`);
  }
  return res.json();
}

export async function deleteGoogleTask(accessToken: string, taskId: string): Promise<void> {
  const res = await fetch(`${getApiUrl()}/connectors/google_tasks/tasks/${encodeURIComponent(taskId)}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Failed to delete task (${res.status})`);
  }
}
