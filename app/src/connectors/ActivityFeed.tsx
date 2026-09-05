import React, { useMemo, useState } from "react";
import {
    View,
    Text,
    FlatList,
    Modal,
    Pressable,
    TouchableOpacity,
    ScrollView,
    Platform,
} from "react-native";
import { Check, X, Bot, User } from "lucide-react-native";
import { ConnectorHistoryItem } from "./api";

interface ActivityFeedProps {
    history: ConnectorHistoryItem[];
}

function formatJsonBlock(value: unknown): string {
    if (value === null || value === undefined) return "—";
    if (typeof value === "string") {
        try {
            const parsed = JSON.parse(value);
            return JSON.stringify(parsed, null, 2);
        } catch {
            return value;
        }
    }
    try {
        return JSON.stringify(value, null, 2);
    } catch {
        return String(value);
    }
}

export default function ActivityFeed({ history }: ActivityFeedProps) {
    const [detailItem, setDetailItem] = useState<ConnectorHistoryItem | null>(null);

    const paramsText = useMemo(
        () => (detailItem ? formatJsonBlock(detailItem.params) : ""),
        [detailItem]
    );
    const resultText = useMemo(
        () => (detailItem ? formatJsonBlock(detailItem.result_summary) : ""),
        [detailItem]
    );
    if (!history || history.length === 0) {
        return (
            <View className="py-4 items-center">
                <Text className="text-on-surface-variant font-['Inter_400Regular']">No recent activity</Text>
            </View>
        );
    }

    const renderItem = ({ item }: { item: ConnectorHistoryItem }) => {
        const isSuccess = item.status === "success";
        const isAgent = item.triggered_by === "ai_agent";

        // Format human readable time
        const date = new Date(item.created_at);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        let timeStr = "";
        if (diffMins < 1) timeStr = "Just now";
        else if (diffMins < 60) timeStr = `${diffMins} min ago`;
        else if (diffHours < 24) timeStr = `${diffHours} hr ago`;
        else timeStr = `${diffDays} days ago`;

        // Make human readable summary
        let summary = `Used tool: ${item.tool_name}`;
        if (item.crud_type === "read") {
            const count = item.result_summary?.count;
            if (count !== undefined) {
                summary = `Read ${count} items`;
            } else {
                summary = "Read data";
            }
        } else if (item.crud_type === "create") {
            summary = `Created '${item.result_summary?.title || "item"}'`;
        } else if (item.crud_type === "update") {
            summary = `Updated '${item.result_summary?.title || "item"}'`;
        } else if (item.crud_type === "delete") {
            summary = "Deleted an item";
        }

        if (!isSuccess) {
            summary = `Failed: ${item.error_message || "Unknown error"}`;
        }

        return (
            <TouchableOpacity
                activeOpacity={0.7}
                className="flex-row items-center py-3 border-b border-outline-variant/15"
                onPress={() => setDetailItem(item)}
                accessibilityRole="button"
                accessibilityLabel={`Activity: ${summary}. ${timeStr}. Open details.`}
            >
                <View className="mr-3">
                    {isSuccess ? (
                        <Check size={16} color="#10b981" />
                    ) : (
                        <X size={16} color="#ef4444" />
                    )}
                </View>
                <View className="flex-1">
                    <View className="flex-row items-center mb-1">
                        <Text
                            className="text-sm text-on-surface flex-1"
                            style={{ fontFamily: 'Inter_500Medium' }}
                            numberOfLines={1}
                        >
                            {summary}
                        </Text>
                    </View>
                    <View className="flex-row items-center">
                        {isAgent ? (
                            <View className="flex-row items-center bg-purple-100 px-1.5 py-0.5 rounded border border-purple-200">
                                <Bot size={10} color="#9333ea" />
                                <Text className="text-[10px] text-purple-700 ml-1" style={{ fontFamily: 'Inter_600SemiBold' }}>AI</Text>
                            </View>
                        ) : (
                            <View className="flex-row items-center bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
                                <User size={10} color="#475569" />
                                <Text className="text-[10px] text-slate-600 ml-1" style={{ fontFamily: 'Inter_600SemiBold' }}>You</Text>
                            </View>
                        )}
                        <Text
                            className="text-[11px] text-on-surface-variant ml-2"
                            style={{ fontFamily: 'Inter_400Regular' }}
                        >
                            {timeStr}
                        </Text>
                    </View>
                </View>
            </TouchableOpacity>
        );
    };

    const mono = Platform.select({ ios: "Menlo", android: "monospace", default: "monospace" });

    return (
        <>
            <View className="mt-2 bg-surface-container-lowest rounded-2xl px-4 py-2 border border-outline-variant/15 shadow-sm">
                <FlatList
                    data={history}
                    keyExtractor={(item) => item.id}
                    renderItem={renderItem}
                    scrollEnabled={false}
                />
            </View>

            <Modal visible={detailItem !== null} animationType="slide" transparent onRequestClose={() => setDetailItem(null)}>
                <Pressable className="flex-1 bg-black/50 justify-end" onPress={() => setDetailItem(null)}>
                    <Pressable
                        className="bg-surface-container-lowest rounded-t-3xl max-h-[85%] border-t border-outline-variant/20"
                        onPress={(e) => e.stopPropagation()}
                    >
                        {detailItem ? (
                            <>
                                <View className="px-4 pt-4 pb-2 border-b border-outline-variant/15">
                                    <Text
                                        className="text-lg text-on-surface"
                                        style={{ fontFamily: "Inter_600SemiBold" }}
                                        numberOfLines={2}
                                    >
                                        {detailItem.tool_name}
                                    </Text>
                                    <Text className="text-xs text-on-surface-variant mt-1" style={{ fontFamily: "Inter_400Regular" }}>
                                        {new Date(detailItem.created_at).toLocaleString()}
                                    </Text>
                                    <View className="flex-row flex-wrap gap-2 mt-3">
                                        <View
                                            className={`px-2 py-0.5 rounded-full ${detailItem.status === "success" ? "bg-emerald-50" : "bg-red-50"}`}
                                        >
                                            <Text
                                                className={`text-[11px] ${detailItem.status === "success" ? "text-emerald-800" : "text-red-800"}`}
                                                style={{ fontFamily: "Inter_600SemiBold" }}
                                            >
                                                {detailItem.status === "success" ? "Success" : "Error"}
                                            </Text>
                                        </View>
                                        <View className="px-2 py-0.5 rounded-full bg-surface-container-high">
                                            <Text className="text-[11px] text-on-surface-variant" style={{ fontFamily: "Inter_500Medium" }}>
                                                {detailItem.crud_type}
                                            </Text>
                                        </View>
                                        <View className="px-2 py-0.5 rounded-full bg-surface-container-high">
                                            <Text className="text-[11px] text-on-surface-variant" style={{ fontFamily: "Inter_500Medium" }}>
                                                {detailItem.triggered_by === "ai_agent"
                                                    ? "AI agent"
                                                    : detailItem.triggered_by === "automation"
                                                        ? "Automation"
                                                        : "You"}
                                            </Text>
                                        </View>
                                    </View>
                                </View>

                                <ScrollView className="px-4 py-3" keyboardShouldPersistTaps="handled">
                                    <Text className="text-[11px] text-on-surface-variant uppercase tracking-wide mb-1" style={{ fontFamily: "Inter_600SemiBold" }}>
                                        Connector
                                    </Text>
                                    <Text className="text-sm text-on-surface mb-4" style={{ fontFamily: "Inter_400Regular" }}>
                                        {detailItem.provider_key}
                                    </Text>

                                    {detailItem.status === "error" && detailItem.error_message ? (
                                        <>
                                            <Text
                                                className="text-[11px] text-on-surface-variant uppercase tracking-wide mb-1"
                                                style={{ fontFamily: "Inter_600SemiBold" }}
                                            >
                                                Error
                                            </Text>
                                            <Text className="text-sm text-red-700 mb-4 leading-snug" style={{ fontFamily: "Inter_400Regular" }}>
                                                {detailItem.error_message}
                                            </Text>
                                        </>
                                    ) : null}

                                    <Text
                                        className="text-[11px] text-on-surface-variant uppercase tracking-wide mb-1"
                                        style={{ fontFamily: "Inter_600SemiBold" }}
                                    >
                                        Parameters
                                    </Text>
                                    <Text
                                        className="text-xs text-on-surface mb-4 leading-5"
                                        style={{ fontFamily: mono }}
                                        selectable
                                    >
                                        {paramsText}
                                    </Text>

                                    <Text
                                        className="text-[11px] text-on-surface-variant uppercase tracking-wide mb-1"
                                        style={{ fontFamily: "Inter_600SemiBold" }}
                                    >
                                        Result summary
                                    </Text>
                                    <Text
                                        className="text-xs text-on-surface mb-6 leading-5"
                                        style={{ fontFamily: mono }}
                                        selectable
                                    >
                                        {resultText}
                                    </Text>
                                </ScrollView>

                                <TouchableOpacity onPress={() => setDetailItem(null)} className="py-3 items-center border-t border-outline-variant/15">
                                    <Text className="text-secondary" style={{ fontFamily: "Inter_600SemiBold" }}>
                                        Close
                                    </Text>
                                </TouchableOpacity>
                            </>
                        ) : null}
                    </Pressable>
                </Pressable>
            </Modal>
        </>
    );
}
