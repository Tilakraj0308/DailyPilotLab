import { getApiUrl } from "../lib/api";

export const GOOGLE_CALENDAR_PROVIDER = "google_calendar";
export const GOOGLE_TASKS_PROVIDER = "google_tasks";
export const NOTION_PROVIDER = "notion";
export const GMAIL_PROVIDER = "gmail";

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

// ── Tool Registry & History ────────────────────────────────────────────────

export type ToolPermissionMap = {
  create: boolean;
  read: boolean;
  update: boolean;
  delete: boolean;
};

export async function fetchToolPermissions(
  provider: string,
  accessToken: string
): Promise<ToolPermissionMap> {
  const res = await fetch(`${getApiUrl()}/connectors/${provider}/permissions`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) {
    throw new Error(`Failed to load permissions (${res.status})`);
  }
  return res.json();
}

export async function updateToolPermission(
  provider: string,
  crudType: string,
  enabled: boolean,
  accessToken: string
): Promise<void> {
  const res = await fetch(`${getApiUrl()}/connectors/${provider}/permissions`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ crud_type: crudType, enabled }),
  });
  if (!res.ok) {
    throw new Error(`Failed to update permission (${res.status})`);
  }
}

export type ConnectorHistoryItem = {
  id: string;
  provider_key: string;
  tool_name: string;
  crud_type: string;
  params: any;
  result_summary: any;
  /** Same object the backend JSON-stringifies into the LLM tool message content. Omitted on legacy rows. */
  ai_tool_response?: any | null;
  status: "success" | "error";
  error_message: string | null;
  triggered_by: "user" | "ai_agent" | "automation";
  created_at: string;
};

export async function fetchConnectorHistory(
  provider: string,
  accessToken: string
): Promise<ConnectorHistoryItem[]> {
  const res = await fetch(`${getApiUrl()}/connectors/${provider}/history`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) {
    throw new Error(`Failed to load history (${res.status})`);
  }
  const data = await res.json();
  return data.items ?? [];
}

export type ToolDefinition = {
  name: string;
  description: string;
  crud_type: string;
  parameters: any;
};

export async function fetchAvailableTools(
  provider: string,
  accessToken: string
): Promise<ToolDefinition[]> {
  const res = await fetch(`${getApiUrl()}/connectors/${provider}/tools`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) {
    throw new Error(`Failed to load tools (${res.status})`);
  }
  const data = await res.json();
  return data.tools ?? [];
}

// ── Gmail (priority inbox + thread + drafts) ───────────────────────────────

export type GmailThreadSummary = {
  id: string;
  snippet?: string | null;
  subject?: string | null;
  from_addr?: string | null;
  internal_date_ms?: string | null;
  label_ids?: string[];
};

export type GmailPriorityResponse = {
  query: string;
  items: GmailThreadSummary[];
};

export type GmailThreadMessage = {
  id: string;
  snippet?: string | null;
  internalDate?: string | null;
  labelIds?: string[];
  headers: Record<string, string>;
};

export type GmailThreadDetail = {
  id: string;
  snippet?: string | null;
  historyId?: string | null;
  messages: GmailThreadMessage[];
};

export type GmailDraftCreateBody = {
  thread_id?: string | null;
  to?: string[];
  cc?: string[];
  bcc?: string[];
  subject: string;
  body_text: string;
};

export type GmailDraftCreateResult = {
  draft_id: string;
  message_id?: string | null;
  thread_id?: string | null;
};

export async function fetchGmailPriority(
  accessToken: string,
  maxResults = 30
): Promise<GmailPriorityResponse> {
  const q = new URLSearchParams();
  if (maxResults !== 30) q.set("max_results", String(maxResults));
  const suffix = q.toString() ? `?${q.toString()}` : "";
  const res = await fetch(`${getApiUrl()}/connectors/gmail/priority${suffix}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Failed to load Gmail priority (${res.status})`);
  }
  return res.json();
}

export async function fetchGmailThread(
  accessToken: string,
  threadId: string
): Promise<GmailThreadDetail> {
  const res = await fetch(
    `${getApiUrl()}/connectors/gmail/threads/${encodeURIComponent(threadId)}`,
    {
      headers: { Authorization: `Bearer ${accessToken}` },
    }
  );
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Failed to load thread (${res.status})`);
  }
  return res.json();
}

export async function createGmailDraft(
  accessToken: string,
  body: GmailDraftCreateBody
): Promise<GmailDraftCreateResult> {
  const res = await fetch(`${getApiUrl()}/connectors/gmail/drafts`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      thread_id: body.thread_id ?? null,
      to: body.to ?? [],
      cc: body.cc ?? [],
      bcc: body.bcc ?? [],
      subject: body.subject,
      body_text: body.body_text,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Failed to create draft (${res.status})`);
  }
  return res.json();
}

export async function sendGmailDraft(
  accessToken: string,
  draftId: string
): Promise<{ ok: boolean; id: string }> {
  const res = await fetch(
    `${getApiUrl()}/connectors/gmail/drafts/${encodeURIComponent(draftId)}/send`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}` },
    }
  );
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Failed to send draft (${res.status})`);
  }
  return res.json();
}
