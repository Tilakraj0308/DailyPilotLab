import React from "react";
import {
    View,
    Text,
    TouchableOpacity,
    ActivityIndicator,
} from "react-native";
import { MaterialIcons } from "@expo/vector-icons";

interface ConnectorTileProps {
    name: string;
    icon: keyof typeof MaterialIcons.glyphMap;
    connected: boolean;
    loading: boolean;
    accountEmail?: string | null;
    connectedAt?: string | null;
    lastSyncAt?: string | null;
    needsReconnect: boolean;
    disabled?: boolean;
    onConnect: () => void;
    onDisconnect: () => void;
}

function formatDate(iso: string | null | undefined): string {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function formatRelativeTime(iso: string | null | undefined): string {
    if (!iso) return "";
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
}

export default function ConnectorTile({
    name,
    icon,
    connected,
    loading,
    accountEmail,
    connectedAt,
    lastSyncAt,
    needsReconnect,
    disabled = false,
    onConnect,
    onDisconnect,
}: ConnectorTileProps) {
    // ── Disabled / Coming Soon ──
    if (disabled) {
        return (
            <View className="bg-surface-container-lowest rounded-2xl p-5 border border-outline-variant/10 shadow-sm mb-3 opacity-50">
                <View className="flex-row items-center gap-3">
                    <View className="w-11 h-11 rounded-xl bg-surface-container items-center justify-center">
                        <MaterialIcons name={icon} size={24} color="#586064" />
                    </View>
                    <View className="flex-1">
                        <Text
                            className="text-base text-on-surface"
                            style={{ fontFamily: "Inter_600SemiBold" }}
                        >
                            {name}
                        </Text>
                        <Text
                            className="text-xs text-on-surface-variant mt-0.5"
                            style={{ fontFamily: "Inter_400Regular" }}
                        >
                            Coming Soon
                        </Text>
                    </View>
                </View>
            </View>
        );
    }

    // ── Needs Reconnect ──
    if (needsReconnect) {
        return (
            <View className="bg-surface-container-lowest rounded-2xl p-5 border border-error-container/40 shadow-sm mb-3">
                <View className="flex-row items-center gap-3">
                    <View className="w-11 h-11 rounded-xl bg-error-container/20 items-center justify-center">
                        <MaterialIcons name={icon} size={24} color="#9e3f4e" />
                    </View>
                    <View className="flex-1">
                        <Text
                            className="text-base text-on-surface"
                            style={{ fontFamily: "Inter_600SemiBold" }}
                        >
                            {name}
                        </Text>
                        <View className="flex-row items-center gap-1 mt-0.5">
                            <MaterialIcons name="warning" size={12} color="#9e3f4e" />
                            <Text
                                className="text-xs text-error"
                                style={{ fontFamily: "Inter_500Medium" }}
                            >
                                Reconnect required
                            </Text>
                        </View>
                    </View>
                    <TouchableOpacity
                        className="bg-secondary px-4 py-2 rounded-full"
                        onPress={onConnect}
                        disabled={loading}
                    >
                        {loading ? (
                            <ActivityIndicator size="small" color="#ffffff" />
                        ) : (
                            <Text
                                className="text-sm text-on-secondary"
                                style={{ fontFamily: "Inter_600SemiBold" }}
                            >
                                Reconnect
                            </Text>
                        )}
                    </TouchableOpacity>
                </View>
            </View>
        );
    }

    // ── Connected ──
    if (connected) {
        return (
            <View className="bg-surface-container-lowest rounded-2xl p-5 border border-outline-variant/15 shadow-sm mb-3">
                <View className="flex-row items-center gap-3">
                    <View className="w-11 h-11 rounded-xl bg-secondary-container items-center justify-center">
                        <MaterialIcons name={icon} size={24} color="#4e45e4" />
                    </View>
                    <View className="flex-1">
                        <View className="flex-row items-center gap-2">
                            <Text
                                className="text-base text-on-surface"
                                style={{ fontFamily: "Inter_600SemiBold" }}
                            >
                                {name}
                            </Text>
                            <View className="w-2 h-2 rounded-full bg-green-500" />
                        </View>
                        {accountEmail && (
                            <Text
                                className="text-xs text-on-surface-variant mt-0.5"
                                style={{ fontFamily: "Inter_400Regular" }}
                            >
                                {accountEmail}
                            </Text>
                        )}
                    </View>
                </View>

                {/* Details row */}
                <View className="flex-row items-center justify-between mt-4 pt-3 border-t border-outline-variant/10">
                    <View className="flex-row items-center gap-4">
                        {connectedAt && (
                            <View className="flex-row items-center gap-1">
                                <MaterialIcons name="link" size={12} color="#586064" />
                                <Text
                                    className="text-[11px] text-on-surface-variant"
                                    style={{ fontFamily: "Inter_400Regular" }}
                                >
                                    {formatDate(connectedAt)}
                                </Text>
                            </View>
                        )}
                        {lastSyncAt && (
                            <View className="flex-row items-center gap-1">
                                <MaterialIcons name="sync" size={12} color="#586064" />
                                <Text
                                    className="text-[11px] text-on-surface-variant"
                                    style={{ fontFamily: "Inter_400Regular" }}
                                >
                                    {formatRelativeTime(lastSyncAt)}
                                </Text>
                            </View>
                        )}
                    </View>
                    <TouchableOpacity
                        className="px-3 py-1.5 rounded-full border border-outline-variant/20"
                        onPress={onDisconnect}
                        disabled={loading}
                    >
                        {loading ? (
                            <ActivityIndicator size="small" color="#586064" />
                        ) : (
                            <Text
                                className="text-xs text-on-surface-variant"
                                style={{ fontFamily: "Inter_500Medium" }}
                            >
                                Disconnect
                            </Text>
                        )}
                    </TouchableOpacity>
                </View>
            </View>
        );
    }

    // ── Disconnected (default) ──
    return (
        <View className="bg-surface-container-lowest rounded-2xl p-5 border border-outline-variant/15 shadow-sm mb-3">
            <View className="flex-row items-center gap-3">
                <View className="w-11 h-11 rounded-xl bg-surface-container items-center justify-center">
                    <MaterialIcons name={icon} size={24} color="#586064" />
                </View>
                <View className="flex-1">
                    <Text
                        className="text-base text-on-surface"
                        style={{ fontFamily: "Inter_600SemiBold" }}
                    >
                        {name}
                    </Text>
                    <Text
                        className="text-xs text-on-surface-variant mt-0.5"
                        style={{ fontFamily: "Inter_400Regular" }}
                    >
                        Not connected
                    </Text>
                </View>
                <TouchableOpacity
                    className="bg-secondary px-4 py-2 rounded-full"
                    onPress={onConnect}
                    disabled={loading}
                >
                    {loading ? (
                        <ActivityIndicator size="small" color="#ffffff" />
                    ) : (
                        <Text
                            className="text-sm text-on-secondary"
                            style={{ fontFamily: "Inter_600SemiBold" }}
                        >
                            Connect
                        </Text>
                    )}
                </TouchableOpacity>
            </View>
        </View>
    );
}
