import { supabase } from './supabase';
import { getApiUrl } from './api';

export type TaskStatus = 'todo' | 'in_progress' | 'done' | 'cancelled';
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent';
export type TaskFilter = 'all' | 'due_today' | 'in_progress' | 'high_priority' | 'overdue' | 'completed';

export interface Task {
    id: string;
    user_id: string;
    title: string;
    description?: string;
    status: TaskStatus;
    priority: TaskPriority;
    due_date?: string;
    completed_at?: string;
    created_at: string;
    updated_at: string;
}

async function getAuthHeader(): Promise<Record<string, string>> {
    const { data } = await supabase.auth.getSession();
    const token = data?.session?.access_token;
    if (!token) throw new Error('Not authenticated');
    return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
}

export async function getTasks(filter: TaskFilter = 'all'): Promise<Task[]> {
    const headers = await getAuthHeader();
    const res = await fetch(`${getApiUrl()}/tasks?filter=${filter}`, { headers });
    if (!res.ok) throw new Error('Failed to fetch tasks');
    const json = await res.json();
    return json.tasks as Task[];
}

export async function createTask(data: {
    title: string;
    description?: string;
    priority?: TaskPriority;
    due_date?: string;
}): Promise<Task> {
    const headers = await getAuthHeader();
    const res = await fetch(`${getApiUrl()}/tasks`, {
        method: 'POST',
        headers,
        body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to create task');
    const json = await res.json();
    return json.task as Task;
}

export async function updateTask(
    taskId: string,
    data: Partial<Pick<Task, 'title' | 'description' | 'status' | 'priority' | 'due_date'>>
): Promise<Task> {
    const headers = await getAuthHeader();
    const res = await fetch(`${getApiUrl()}/tasks/${taskId}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update task');
    const json = await res.json();
    return json.task as Task;
}

export async function deleteTask(taskId: string): Promise<void> {
    const headers = await getAuthHeader();
    const res = await fetch(`${getApiUrl()}/tasks/${taskId}`, {
        method: 'DELETE',
        headers,
    });
    if (!res.ok) throw new Error('Failed to delete task');
}
