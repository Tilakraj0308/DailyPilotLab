import React from "react";
import { View, Text, StyleSheet, FlatList } from "react-native";
import { Check, X, Bot, User } from "lucide-react-native";
import { ConnectorHistoryItem } from "./api";

interface ActivityFeedProps {
    history: ConnectorHistoryItem[];
}

export default function ActivityFeed({ history }: ActivityFeedProps) {
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
            <View className="flex-row items-center py-3 border-b border-outline-variant/15">
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
            </View>
        );
    };

    return (
        <View className="mt-2 bg-surface-container-lowest rounded-2xl px-4 py-2 border border-outline-variant/15 shadow-sm">
            <FlatList
                data={history}
                keyExtractor={(item) => item.id}
                renderItem={renderItem}
                scrollEnabled={false}
            />
        </View>
    );
}
