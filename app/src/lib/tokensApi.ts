import { supabase } from "./supabase";
import { getApiUrl } from "./api";

export interface TokenOverviewStats {
    total_requests: number;
    total_tokens: number;
    prompt_tokens: number;
    completion_tokens: number;
    total_cost_usd: number;
    avg_duration_ms: number;
}

export interface ModelBreakdown {
    model: string;
    request_count: number;
    total_tokens: number;
    cost_usd: number;
}

export interface TypeBreakdown {
    request_type: string;
    request_count: number;
    total_tokens: number;
    cost_usd: number;
}

export interface PeriodStats {
    request_count: number;
    total_tokens: number;
    prompt_tokens: number;
    completion_tokens: number;
    cost_usd: number;
}

export interface DailyHistoryItem {
    date: string;
    request_count: number;
    total_tokens: number;
    prompt_tokens: number;
    completion_tokens: number;
    cost_usd: number;
}

export interface TokenStatsResponse {
    status: string;
    data: {
        overview: TokenOverviewStats;
        today?: PeriodStats;
        yesterday?: PeriodStats;
        past_7_days?: PeriodStats;
        past_30_days?: PeriodStats;
        daily_history?: DailyHistoryItem[];
        by_model: ModelBreakdown[];
        by_type: TypeBreakdown[];
    };
}

export interface TokenTraceSummary {
    id: string;
    session_id?: string;
    request_type: string;
    model: string;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    estimated_cost_usd: number;
    duration_ms: number;
    status: string;
    metadata?: any;
    created_at: string;
}

export interface TokenTracesResponse {
    status: string;
    traces: TokenTraceSummary[];
    limit: number;
    offset: number;
}

export interface TokenTimelineStep {
    id: string;
    step_number: number;
    event_type: string;
    name: string;
    model?: string;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    estimated_cost_usd: number;
    duration_ms: number;
    details?: any;
    created_at: string;
}

export interface TokenTraceDetail extends TokenTraceSummary {
    timeline: TokenTimelineStep[];
}

export interface TokenTraceDetailResponse {
    status: string;
    trace: TokenTraceDetail;
}

async function getAuthHeader(): Promise<Record<string, string>> {
    const { data } = await supabase.auth.getSession();
    const token = data?.session?.access_token;
    if (!token) throw new Error("Not authenticated");
    return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

export async function fetchTokenStats(): Promise<TokenStatsResponse["data"]> {
    const headers = await getAuthHeader();
    const res = await fetch(`${getApiUrl()}/tokens/stats`, { headers });
    if (!res.ok) {
        throw new Error(`Failed to fetch token stats: ${res.statusText}`);
    }
    const json: TokenStatsResponse = await res.json();
    return json.data;
}

export async function fetchTokenTraces(
    limit: number = 20,
    offset: number = 0,
    requestType?: string
): Promise<TokenTraceSummary[]> {
    const headers = await getAuthHeader();
    let url = `${getApiUrl()}/tokens/traces?limit=${limit}&offset=${offset}`;
    if (requestType && requestType.toLowerCase() !== "all") {
        url += `&request_type=${encodeURIComponent(requestType)}`;
    }
    const res = await fetch(url, { headers });
    if (!res.ok) {
        throw new Error(`Failed to fetch token traces: ${res.statusText}`);
    }
    const json: TokenTracesResponse = await res.json();
    return json.traces || [];
}

export async function fetchTokenTraceTimeline(traceId: string): Promise<TokenTraceDetail> {
    const headers = await getAuthHeader();
    const res = await fetch(`${getApiUrl()}/tokens/traces/${traceId}`, { headers });
    if (!res.ok) {
        throw new Error(`Failed to fetch trace timeline: ${res.statusText}`);
    }
    const json: TokenTraceDetailResponse = await res.json();
    return json.trace;
}
