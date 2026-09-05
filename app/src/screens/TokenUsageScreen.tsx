import React, { useEffect, useState } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    ScrollView,
    ActivityIndicator,
    RefreshControl,
    Modal,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { MaterialIcons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import {
    fetchTokenStats,
    fetchTokenTraces,
    fetchTokenTraceTimeline,
    TokenTraceSummary,
    TokenTraceDetail,
    TokenStatsResponse,
    PeriodStats,
    DailyHistoryItem,
} from "../lib/tokensApi";

type TimeRangeKey = "today" | "7d" | "30d" | "all";

export default function TokenUsageScreen() {
    const navigation = useNavigation<any>();

    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [rawStats, setRawStats] = useState<TokenStatsResponse["data"] | null>(null);
    const [traces, setTraces] = useState<TokenTraceSummary[]>([]);
    const [selectedFilter, setSelectedFilter] = useState("all");
    const [selectedTimeRange, setSelectedTimeRange] = useState<TimeRangeKey>("today");

    // Detailed Modal state
    const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
    const [traceDetail, setTraceDetail] = useState<TokenTraceDetail | null>(null);
    const [modalLoading, setModalLoading] = useState(false);

    const loadData = async () => {
        try {
            setLoading(true);
            const [statsData, tracesData] = await Promise.all([
                fetchTokenStats().catch(() => null),
                fetchTokenTraces(30, 0, selectedFilter).catch(() => []),
            ]);
            setRawStats(statsData);
            setTraces(tracesData);
        } catch (e) {
            console.error("Error loading token usage data:", e);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        loadData();
    }, [selectedFilter]);

    const onRefresh = () => {
        setRefreshing(true);
        loadData();
    };

    const handleOpenTrace = async (traceId: string) => {
        setSelectedTraceId(traceId);
        setModalLoading(true);
        try {
            const detail = await fetchTokenTraceTimeline(traceId);
            setTraceDetail(detail);
        } catch (e) {
            console.error("Error fetching trace timeline:", e);
            setTraceDetail(null);
        } finally {
            setModalLoading(false);
        }
    };

    const formatTokens = (num: number) => {
        if (!num) return "0";
        return num.toLocaleString();
    };

    const formatCost = (cost: number) => {
        if (!cost) return "$0.000000";
        return `$${cost.toFixed(6)}`;
    };

    const formatDate = (isoStr: string) => {
        if (!isoStr) return "";
        const d = new Date(isoStr);
        return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) +
            " · " + d.toLocaleDateString([], { month: "short", day: "numeric" });
    };

    const formatDayLabel = (dateStr: string) => {
        if (!dateStr) return "";
        const d = new Date(dateStr);
        const today = new Date();
        const yesterday = new Date();
        yesterday.setDate(today.getDate() - 1);

        if (d.toDateString() === today.toDateString()) {
            return "Today (" + d.toLocaleDateString([], { month: "short", day: "numeric" }) + ")";
        }
        if (d.toDateString() === yesterday.toDateString()) {
            return "Yesterday (" + d.toLocaleDateString([], { month: "short", day: "numeric" }) + ")";
        }
        return d.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
    };

    // Extract stats for current selected time range
    const getActiveStats = (): {
        requests: number;
        tokens: number;
        prompt: number;
        completion: number;
        cost: number;
        latency: number;
    } => {
        if (!rawStats) {
            return { requests: 0, tokens: 0, prompt: 0, completion: 0, cost: 0, latency: 0 };
        }

        if (selectedTimeRange === "today") {
            const t = rawStats.today;
            return {
                requests: t?.request_count || 0,
                tokens: t?.total_tokens || 0,
                prompt: t?.prompt_tokens || 0,
                completion: t?.completion_tokens || 0,
                cost: t?.cost_usd || 0,
                latency: rawStats.overview.avg_duration_ms || 0,
            };
        } else if (selectedTimeRange === "7d") {
            const t = rawStats.past_7_days;
            return {
                requests: t?.request_count || 0,
                tokens: t?.total_tokens || 0,
                prompt: t?.prompt_tokens || 0,
                completion: t?.completion_tokens || 0,
                cost: t?.cost_usd || 0,
                latency: rawStats.overview.avg_duration_ms || 0,
            };
        } else if (selectedTimeRange === "30d") {
            const t = rawStats.past_30_days;
            return {
                requests: t?.request_count || 0,
                tokens: t?.total_tokens || 0,
                prompt: t?.prompt_tokens || 0,
                completion: t?.completion_tokens || 0,
                cost: t?.cost_usd || 0,
                latency: rawStats.overview.avg_duration_ms || 0,
            };
        } else {
            const o = rawStats.overview;
            return {
                requests: o.total_requests || 0,
                tokens: o.total_tokens || 0,
                prompt: o.prompt_tokens || 0,
                completion: o.completion_tokens || 0,
                cost: o.total_cost_usd || 0,
                latency: o.avg_duration_ms || 0,
            };
        }
    };

    const activeStats = getActiveStats();
    const dailyHistory = rawStats?.daily_history || [];
    const maxDayTokens = Math.max(1, ...dailyHistory.map((d) => d.total_tokens));

    return (
        <SafeAreaView className="flex-1 bg-background">
            {/* Header */}
            <View className="flex-row items-center px-5 py-4 border-b border-outline-variant/10 bg-background">
                <TouchableOpacity onPress={() => navigation.goBack()} className="mr-3 p-1">
                    <MaterialIcons name="arrow-back" size={24} color="#2b3437" />
                </TouchableOpacity>
                <View className="flex-1">
                    <Text
                        className="text-lg font-bold text-on-surface"
                        style={{ fontFamily: "Manrope_700Bold" }}
                    >
                        Token Usage & Costs
                    </Text>
                    <Text className="text-xs text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>
                        Per-request timeline & daily usage analytics
                    </Text>
                </View>
                <TouchableOpacity onPress={onRefresh} className="p-2">
                    <MaterialIcons name="refresh" size={22} color="#4e45e4" />
                </TouchableOpacity>
            </View>

            <ScrollView
                className="flex-1 px-4 pt-3"
                contentContainerStyle={{ paddingBottom: 40 }}
                refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
            >
                {/* Time Range Selector Bar */}
                <View className="bg-surface-container-low p-1.5 rounded-2xl mb-4 flex-row border border-outline-variant/15">
                    {[
                        { id: "today", label: "Today" },
                        { id: "7d", label: "7 Days" },
                        { id: "30d", label: "30 Days" },
                        { id: "all", label: "All Time" },
                    ].map((t) => {
                        const active = selectedTimeRange === t.id;
                        return (
                            <TouchableOpacity
                                key={t.id}
                                onPress={() => setSelectedTimeRange(t.id as TimeRangeKey)}
                                className={`flex-1 py-2 items-center rounded-xl ${active ? "bg-primary shadow-sm" : ""
                                    }`}
                            >
                                <Text
                                    className={`text-xs font-semibold ${active ? "text-white" : "text-on-surface-variant"
                                        }`}
                                    style={{ fontFamily: active ? "Inter_600SemiBold" : "Inter_500Medium" }}
                                >
                                    {t.label}
                                </Text>
                            </TouchableOpacity>
                        );
                    })}
                </View>

                {/* Overview Stats Cards */}
                <View className="flex-row flex-wrap justify-between gap-2 mb-5">
                    {/* Card 1: Total Tokens */}
                    <View className="w-[48%] bg-surface-container-low p-4 rounded-2xl border border-outline-variant/15">
                        <View className="flex-row items-center justify-between mb-1">
                            <Text className="text-xs text-on-surface-variant" style={{ fontFamily: "Inter_500Medium" }}>
                                Total Tokens
                            </Text>
                            <MaterialIcons name="bolt" size={18} color="#4e45e4" />
                        </View>
                        <Text className="text-xl font-bold text-on-surface mb-1" style={{ fontFamily: "Manrope_700Bold" }}>
                            {formatTokens(activeStats.tokens)}
                        </Text>
                        <Text className="text-[10px] text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>
                            Prompt: {formatTokens(activeStats.prompt)} · Output: {formatTokens(activeStats.completion)}
                        </Text>
                    </View>

                    {/* Card 2: Estimated Cost */}
                    <View className="w-[48%] bg-surface-container-low p-4 rounded-2xl border border-outline-variant/15">
                        <View className="flex-row items-center justify-between mb-1">
                            <Text className="text-xs text-on-surface-variant" style={{ fontFamily: "Inter_500Medium" }}>
                                Est. Total Cost
                            </Text>
                            <MaterialIcons name="attach-money" size={18} color="#10b981" />
                        </View>
                        <Text className="text-xl font-bold text-emerald-600 mb-1" style={{ fontFamily: "Manrope_700Bold" }}>
                            {formatCost(activeStats.cost)}
                        </Text>
                        <Text className="text-[10px] text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>
                            Avg / request: {formatCost(activeStats.cost / Math.max(1, activeStats.requests))}
                        </Text>
                    </View>

                    {/* Card 3: Requests */}
                    <View className="w-[48%] bg-surface-container-low p-4 rounded-2xl border border-outline-variant/15">
                        <View className="flex-row items-center justify-between mb-1">
                            <Text className="text-xs text-on-surface-variant" style={{ fontFamily: "Inter_500Medium" }}>
                                Requests
                            </Text>
                            <MaterialIcons name="forum" size={18} color="#6366f1" />
                        </View>
                        <Text className="text-xl font-bold text-on-surface mb-1" style={{ fontFamily: "Manrope_700Bold" }}>
                            {activeStats.requests}
                        </Text>
                        <Text className="text-[10px] text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>
                            Tracked API calls
                        </Text>
                    </View>

                    {/* Card 4: Avg Latency */}
                    <View className="w-[48%] bg-surface-container-low p-4 rounded-2xl border border-outline-variant/15">
                        <View className="flex-row items-center justify-between mb-1">
                            <Text className="text-xs text-on-surface-variant" style={{ fontFamily: "Inter_500Medium" }}>
                                Avg Latency
                            </Text>
                            <MaterialIcons name="timer" size={18} color="#f59e0b" />
                        </View>
                        <Text className="text-xl font-bold text-on-surface mb-1" style={{ fontFamily: "Manrope_700Bold" }}>
                            {activeStats.latency ? `${Math.round(activeStats.latency)}ms` : "0ms"}
                        </Text>
                        <Text className="text-[10px] text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>
                            Response duration
                        </Text>
                    </View>
                </View>

                {/* Daily History Breakdown Section */}
                {dailyHistory.length > 0 && (
                    <View className="mb-6">
                        <View className="flex-row items-center justify-between mb-3">
                            <Text className="text-sm font-bold text-on-surface" style={{ fontFamily: "Manrope_700Bold" }}>
                                Daily Usage Breakdown
                            </Text>
                            <Text className="text-xs text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>
                                Past 30 Days
                            </Text>
                        </View>

                        <View className="bg-surface-container-low p-4 rounded-2xl border border-outline-variant/15">
                            {dailyHistory.map((item, idx) => {
                                const percentage = Math.min(100, Math.round((item.total_tokens / maxDayTokens) * 100));

                                return (
                                    <View key={item.date || idx} className="mb-3 last:mb-0">
                                        <View className="flex-row items-center justify-between mb-1.5">
                                            <View className="flex-row items-center gap-2">
                                                <MaterialIcons name="event" size={15} color="#6366f1" />
                                                <Text className="text-xs font-semibold text-on-surface" style={{ fontFamily: "Inter_600SemiBold" }}>
                                                    {formatDayLabel(item.date)}
                                                </Text>
                                                <View className="bg-primary/10 px-2 py-0.5 rounded-full">
                                                    <Text className="text-[10px] font-bold text-primary" style={{ fontFamily: "Inter_600SemiBold" }}>
                                                        {item.request_count} req
                                                    </Text>
                                                </View>
                                            </View>

                                            <View className="flex-row items-center gap-3">
                                                <Text className="text-xs font-semibold text-on-surface" style={{ fontFamily: "Inter_600SemiBold" }}>
                                                    {formatTokens(item.total_tokens)} tokens
                                                </Text>
                                                <Text className="text-xs font-bold text-emerald-600" style={{ fontFamily: "Manrope_700Bold" }}>
                                                    {formatCost(item.cost_usd)}
                                                </Text>
                                            </View>
                                        </View>

                                        {/* Usage Progress Bar */}
                                        <View className="w-full h-1.5 bg-outline-variant/10 rounded-full overflow-hidden">
                                            <View
                                                className="h-full bg-primary rounded-full"
                                                style={{ width: `${percentage}%` }}
                                            />
                                        </View>
                                    </View>
                                );
                            })}
                        </View>
                    </View>
                )}

                {/* Category Filter Pills for Traces */}
                <View className="flex-row items-center justify-between mb-3">
                    <Text className="text-sm font-bold text-on-surface" style={{ fontFamily: "Manrope_700Bold" }}>
                        Request Timeline Traces
                    </Text>
                    <View className="flex-row gap-1.5">
                        {[
                            { id: "all", label: "All" },
                            { id: "chat", label: "Chat" },
                            { id: "memory", label: "Memory" },
                        ].map((f) => {
                            const active = selectedFilter === f.id;
                            return (
                                <TouchableOpacity
                                    key={f.id}
                                    onPress={() => setSelectedFilter(f.id)}
                                    className={`px-2.5 py-1 rounded-full border ${active
                                            ? "bg-primary border-primary"
                                            : "bg-surface-container-low border-outline-variant/20"
                                        }`}
                                >
                                    <Text
                                        className={`text-[11px] ${active ? "text-white font-semibold" : "text-on-surface-variant"
                                            }`}
                                        style={{ fontFamily: active ? "Inter_600SemiBold" : "Inter_400Regular" }}
                                    >
                                        {f.label}
                                    </Text>
                                </TouchableOpacity>
                            );
                        })}
                    </View>
                </View>

                {loading && !refreshing ? (
                    <View className="py-12 items-center">
                        <ActivityIndicator size="large" color="#4e45e4" />
                    </View>
                ) : traces.length === 0 ? (
                    <View className="py-12 px-4 bg-surface-container-low rounded-2xl items-center border border-outline-variant/15">
                        <MaterialIcons name="analytics" size={36} color="#94a3b8" />
                        <Text className="text-base font-semibold text-on-surface mt-2 mb-1" style={{ fontFamily: "Manrope_600SemiBold" }}>
                            No Token Traces Found
                        </Text>
                        <Text className="text-xs text-on-surface-variant text-center" style={{ fontFamily: "Inter_400Regular" }}>
                            Send a chat message or execute an AI request to view token usage traceability data.
                        </Text>
                    </View>
                ) : (
                    traces.map((item) => (
                        <TouchableOpacity
                            key={item.id}
                            onPress={() => handleOpenTrace(item.id)}
                            className="bg-surface-container-low p-4 rounded-2xl mb-3 border border-outline-variant/15 active:opacity-80"
                        >
                            {/* Row 1: Type badge, model, timestamp */}
                            <View className="flex-row items-center justify-between mb-2">
                                <View className="flex-row items-center gap-1.5">
                                    <View className="bg-primary/10 px-2 py-0.5 rounded-md">
                                        <Text className="text-[10px] font-bold text-primary capitalize" style={{ fontFamily: "Inter_600SemiBold" }}>
                                            {item.request_type}
                                        </Text>
                                    </View>
                                    <View className="bg-secondary/10 px-2 py-0.5 rounded-md">
                                        <Text className="text-[10px] font-medium text-secondary" style={{ fontFamily: "Inter_500Medium" }}>
                                            {item.model}
                                        </Text>
                                    </View>
                                </View>
                                <Text className="text-[11px] text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>
                                    {formatDate(item.created_at)}
                                </Text>
                            </View>

                            {/* User Prompt Snippet if available */}
                            {item.metadata?.user_prompt_snippet ? (
                                <Text
                                    numberOfLines={1}
                                    className="text-xs text-on-surface font-medium mb-2"
                                    style={{ fontFamily: "Inter_500Medium" }}
                                >
                                    "{item.metadata.user_prompt_snippet}"
                                </Text>
                            ) : null}

                            {/* Tokens & Cost Summary Bar */}
                            <View className="flex-row items-center justify-between pt-2 border-t border-outline-variant/10">
                                <View className="flex-row items-center gap-3">
                                    <View className="flex-row items-center gap-1">
                                        <MaterialIcons name="bolt" size={14} color="#6366f1" />
                                        <Text className="text-xs font-semibold text-on-surface" style={{ fontFamily: "Inter_600SemiBold" }}>
                                            {formatTokens(item.total_tokens)} tokens
                                        </Text>
                                    </View>
                                    <Text className="text-[11px] text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>
                                        In: {item.prompt_tokens} · Out: {item.completion_tokens}
                                    </Text>
                                </View>

                                <View className="flex-row items-center gap-2">
                                    <Text className="text-xs font-bold text-emerald-600" style={{ fontFamily: "Manrope_700Bold" }}>
                                        {formatCost(item.estimated_cost_usd)}
                                    </Text>
                                    <MaterialIcons name="chevron-right" size={18} color="#94a3b8" />
                                </View>
                            </View>
                        </TouchableOpacity>
                    ))
                )}
            </ScrollView>

            {/* Step-by-Step Timeline Detail Modal */}
            <Modal
                visible={selectedTraceId !== null}
                animationType="slide"
                transparent={true}
                onRequestClose={() => setSelectedTraceId(null)}
            >
                <View className="flex-1 bg-black/60 justify-end items-center">
                    <View className="bg-background rounded-t-3xl p-5 max-h-[85%] w-full max-w-[480px] border-t border-outline-variant/20 shadow-2xl">
                        {/* Modal Header */}
                        <View className="flex-row items-center justify-between pb-3 border-b border-outline-variant/10 mb-4">
                            <View className="flex-1">
                                <Text className="text-base font-bold text-on-surface" style={{ fontFamily: "Manrope_700Bold" }}>
                                    Request Execution Timeline
                                </Text>
                                <Text className="text-xs text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>
                                    Trace ID: {selectedTraceId}
                                </Text>
                            </View>
                            <TouchableOpacity onPress={() => setSelectedTraceId(null)} className="p-1">
                                <MaterialIcons name="close" size={24} color="#64748b" />
                            </TouchableOpacity>
                        </View>

                        {modalLoading ? (
                            <View className="py-12 items-center">
                                <ActivityIndicator size="large" color="#4e45e4" />
                            </View>
                        ) : traceDetail ? (
                            <ScrollView className="flex-1" contentContainerStyle={{ paddingBottom: 20 }}>
                                {/* Summary Metadata */}
                                <View className="bg-surface-container-low p-4 rounded-2xl mb-4 border border-outline-variant/15">
                                    <View className="flex-row justify-between items-center mb-2">
                                        <View className="flex-row items-center gap-2">
                                            <MaterialIcons name="dns" size={16} color="#4e45e4" />
                                            <Text className="text-xs text-on-surface font-semibold" style={{ fontFamily: "Inter_600SemiBold" }}>
                                                Model: {traceDetail.model}
                                            </Text>
                                        </View>
                                        <Text className="text-xs text-emerald-600 font-bold" style={{ fontFamily: "Manrope_700Bold" }}>
                                            {formatCost(traceDetail.estimated_cost_usd)}
                                        </Text>
                                    </View>

                                    <View className="flex-row justify-between items-center pt-2 border-t border-outline-variant/10">
                                        <Text className="text-xs text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>
                                            Billed Tokens: <Text className="text-on-surface font-bold">{formatTokens(traceDetail.total_tokens)}</Text>
                                        </Text>
                                        <Text className="text-xs text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>
                                            Duration: <Text className="text-on-surface font-bold">
                                                {traceDetail.duration_ms >= 1000 ? `${(traceDetail.duration_ms / 1000).toFixed(2)}s` : `${traceDetail.duration_ms}ms`}
                                            </Text>
                                        </Text>
                                    </View>
                                </View>

                                <Text className="text-xs font-bold text-on-surface mb-3 uppercase tracking-wider" style={{ fontFamily: "Inter_600SemiBold" }}>
                                    Timeline Events ({traceDetail.timeline?.length || 0} Steps)
                                </Text>

                                {/* Timeline Steps */}
                                {traceDetail.timeline?.map((step) => {
                                    const durationStr = step.duration_ms >= 1000
                                        ? `${(step.duration_ms / 1000).toFixed(2)}s`
                                        : `${step.duration_ms}ms`;

                                    return (
                                        <View
                                            key={step.id || step.step_number}
                                            className="mb-3 bg-surface-container-low p-3.5 rounded-2xl border border-outline-variant/15"
                                        >
                                            <View className="flex-row items-start justify-between mb-2">
                                                <View className="flex-row items-center gap-2.5 flex-1">
                                                    <View className="w-6 h-6 rounded-full bg-primary/10 items-center justify-center">
                                                        <Text className="text-xs font-bold text-primary" style={{ fontFamily: "Inter_600SemiBold" }}>
                                                            {step.step_number}
                                                        </Text>
                                                    </View>
                                                    <Text className="text-xs font-bold text-on-surface flex-1" style={{ fontFamily: "Inter_600SemiBold" }}>
                                                        {step.name}
                                                    </Text>
                                                </View>
                                                <Text className="text-[11px] text-on-surface-variant font-medium ml-2" style={{ fontFamily: "Inter_500Medium" }}>
                                                    {durationStr}
                                                </Text>
                                            </View>

                                            {step.event_type === "llm_call" ? (
                                                <View className="bg-background/60 p-2.5 rounded-xl flex-row items-center justify-between border border-outline-variant/10">
                                                    <View className="flex-row items-center gap-3">
                                                        <Text className="text-[11px] text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>
                                                            Prompt: <Text className="text-on-surface font-semibold">{step.prompt_tokens}</Text>
                                                        </Text>
                                                        <Text className="text-[11px] text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>
                                                            Completion: <Text className="text-on-surface font-semibold">{step.completion_tokens}</Text>
                                                        </Text>
                                                    </View>
                                                    <Text className="text-[11px] text-emerald-600 font-bold" style={{ fontFamily: "Inter_600SemiBold" }}>
                                                        {formatCost(step.estimated_cost_usd)}
                                                    </Text>
                                                </View>
                                            ) : (
                                                <View className="mt-1">
                                                    <Text className="text-[10px] uppercase font-bold text-secondary mb-1" style={{ fontFamily: "Inter_600SemiBold" }}>
                                                        Tool Arguments:
                                                    </Text>
                                                    <View className="bg-slate-900 p-2.5 rounded-xl border border-slate-800">
                                                        <Text className="text-[11px] text-emerald-400 font-mono" style={{ fontFamily: "monospace" }}>
                                                            {step.details?.tool_args || step.details?.tool_name || "{}"}
                                                        </Text>
                                                    </View>
                                                </View>
                                            )}
                                        </View>
                                    );
                                })}

                                <View className="mt-2 p-3 bg-primary/5 rounded-xl border border-primary/10">
                                    <Text className="text-[11px] text-on-surface-variant leading-4" style={{ fontFamily: "Inter_400Regular" }}>
                                        💡 <Text className="font-semibold">Note:</Text> Multi-turn LLM requests execute multiple API iterations. Total prompt tokens reflect cumulative API context sent across iterations.
                                    </Text>
                                </View>
                            </ScrollView>
                        ) : (
                            <Text className="text-xs text-on-surface-variant text-center py-6">
                                Unable to load trace details.
                            </Text>
                        )}
                    </View>
                </View>
            </Modal>
        </SafeAreaView>
    );
}
