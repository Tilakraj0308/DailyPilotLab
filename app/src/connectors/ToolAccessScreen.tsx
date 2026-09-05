import React, { useEffect, useState } from "react";
import { View, Text, ScrollView, TouchableOpacity, ActivityIndicator, Image } from "react-native";
import { useNavigation, useRoute } from "@react-navigation/native";
import { ArrowLeft } from "lucide-react-native";

import { useAuth } from "../context/AuthContext";
import {
    fetchToolPermissions,
    updateToolPermission,
    fetchConnectorHistory,
    disconnectConnector,
    fetchConnectors,
    fetchGoogleTaskLists,
    selectGoogleTaskList,
    ToolPermissionMap,
    ConnectorHistoryItem,
    ConnectorStatusItem,
    GoogleTaskListItem
} from "./api";
import PermissionToggleCard from "./PermissionToggleCard";
import ActivityFeed from "./ActivityFeed";
import TaskListPicker from "./TaskListPicker";
import { universalAlert } from "../lib/alerts";

const PROVIDER_INFO: Record<string, { title: string; iconUri: string }> = {
    google_tasks: {
        title: "Google Tasks",
        iconUri: "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Google_Tasks_2021.svg/512px-Google_Tasks_2021.svg.png",
    },
    google_calendar: {
        title: "Google Calendar",
        iconUri: "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Google_Calendar_icon_%282020%29.svg/512px-Google_Calendar_icon_%282020%29.svg.png",
    },
    gmail: {
        title: "Gmail",
        iconUri: "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Gmail_icon_%282020%29.svg/512px-Gmail_icon_%282020%29.svg.png",
    },
};

export default function ToolAccessScreen() {
    const route = useRoute<any>();
    const navigation = useNavigation<any>();
    const { session } = useAuth();

    const providerKey = route.params?.provider_key;
    const info = PROVIDER_INFO[providerKey] || { title: "Connector", iconUri: "" };

    const [permissions, setPermissions] = useState<ToolPermissionMap | null>(null);
    const [history, setHistory] = useState<ConnectorHistoryItem[]>([]);
    const [status, setStatus] = useState<ConnectorStatusItem | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    // Tasks Picker state
    const [pickerOpen, setPickerOpen] = useState(false);
    const [taskLists, setTaskLists] = useState<GoogleTaskListItem[]>([]);
    const [listsLoading, setListsLoading] = useState(false);
    const [pickingBusy, setPickingBusy] = useState(false);

    useEffect(() => {
        loadData();
    }, [providerKey, session]);

    const loadData = async () => {
        if (!session?.access_token || !providerKey) return;
        try {
            setLoading(true);
            const [perms, hist, allConnectors] = await Promise.all([
                fetchToolPermissions(providerKey, session.access_token),
                fetchConnectorHistory(providerKey, session.access_token),
                fetchConnectors(session.access_token)
            ]);
            setPermissions(perms);
            setHistory(hist);
            const match = allConnectors.connectors.find(c => c.provider_key === providerKey);
            if (match) setStatus(match);
        } catch (e: any) {
            console.error("Failed to load tool access data:", e);
        } finally {
            setLoading(false);
        }
    };

    const openTaskListPicker = async () => {
        if (!session?.access_token) return;
        setPickerOpen(true);
        setListsLoading(true);
        try {
            const lists = await fetchGoogleTaskLists(session.access_token);
            setTaskLists(lists);
        } catch (e: any) {
            universalAlert("Error", "Could not load lists: " + e.message);
            setPickerOpen(false);
        } finally {
            setListsLoading(false);
        }
    };

    const handlePickList = async (list: GoogleTaskListItem) => {
        if (!session?.access_token) return;
        setPickingBusy(true);
        try {
            await selectGoogleTaskList(session.access_token, list.id, list.title);
            setStatus(s => s ? { ...s, selected_resource_id: list.id, selected_resource_name: list.title } : s);
            setPickerOpen(false);
        } catch (e: any) {
            universalAlert("Error", "Could not save list: " + e.message);
        } finally {
            setPickingBusy(false);
        }
    };

    const handleToggle = async (crudType: keyof ToolPermissionMap, enabled: boolean) => {
        if (!session?.access_token || !permissions || saving) return;
        try {
            setSaving(true);
            await updateToolPermission(providerKey, crudType, enabled, session.access_token);
            setPermissions(prev => prev ? { ...prev, [crudType]: enabled } : prev);
        } catch (e: any) {
            // Revert optimism if failed
            console.error("Failed to update permission", e);
        } finally {
            setSaving(false);
        }
    };

    const handleDisconnect = async () => {
        if (!session?.access_token) return;
        try {
            await disconnectConnector(providerKey, session.access_token);
            navigation.goBack();
        } catch (e) {
            console.error("Failed to disconnect", e);
        }
    };

    if (!providerKey) {
        return (
            <View className="flex-1 items-center justify-center bg-surface">
                <Text className="text-on-surface">Invalid provider</Text>
            </View>
        );
    }

    return (
        <View className="flex-1 bg-surface">
            {/* Header */}
            <View className="pt-16 pb-4 px-5 flex-row items-center border-b border-outline-variant/15 bg-surface-container-lowest">
                <TouchableOpacity className="mr-4 p-1" onPress={() => navigation.goBack()}>
                    <ArrowLeft color="#1e293b" size={24} />
                </TouchableOpacity>
                <Image className="w-7 h-7 mr-3" source={{ uri: info.iconUri }} />
                <Text className="text-on-surface text-xl flex-1" style={{ fontFamily: "Inter_600SemiBold" }}>{info.title}</Text>
                <View className="bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
                    <Text className="text-emerald-600 text-xs" style={{ fontFamily: "Inter_600SemiBold" }}>Connected</Text>
                </View>
            </View>

            <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 60 }} showsVerticalScrollIndicator={false}>
                {loading ? (
                    <View className="flex-1 items-center justify-center mt-10">
                        <ActivityIndicator size="large" color="#4f46e5" />
                    </View>
                ) : (
                    <>
                        {/* AI TOOL ACCESS */}
                        <View className="mb-8">
                            <Text className="text-primary text-xs tracking-widest mb-2 uppercase" style={{ fontFamily: "Inter_600SemiBold" }}>
                                AI TOOL ACCESS
                            </Text>
                            <Text className="text-on-surface-variant text-sm mb-4" style={{ fontFamily: "Inter_400Regular" }}>
                                Control what your AI assistant can do with {info.title}.
                            </Text>

                            <View className="mt-2">
                                <PermissionToggleCard
                                    crudType="read"
                                    enabled={permissions?.read ?? true}
                                    onToggle={(v) => handleToggle("read", v)}
                                    disabled={saving}
                                />

                                {(providerKey === "google_tasks" ||
                                    providerKey === "google_calendar" ||
                                    providerKey === "gmail") && (
                                        <>
                                            <PermissionToggleCard
                                                crudType="create"
                                                enabled={permissions?.create ?? true}
                                                onToggle={(v) => handleToggle("create", v)}
                                                disabled={saving}
                                            />
                                            <PermissionToggleCard
                                                crudType="update"
                                                enabled={permissions?.update ?? true}
                                                onToggle={(v) => handleToggle("update", v)}
                                                disabled={saving}
                                            />
                                            <PermissionToggleCard
                                                crudType="delete"
                                                enabled={permissions?.delete ?? false}
                                                onToggle={(v) => handleToggle("delete", v)}
                                                disabled={saving}
                                            />
                                        </>
                                    )}
                            </View>
                        </View>

                        {providerKey === "gmail" && (
                            <View className="mb-8">
                                <Text className="text-primary text-xs tracking-widest mb-2 uppercase" style={{ fontFamily: "Inter_600SemiBold" }}>
                                    Gmail tools
                                </Text>
                                <Text className="text-on-surface-variant text-sm mb-4" style={{ fontFamily: "Inter_400Regular" }}>
                                    Open the priority inbox view to read threads and create or send drafts.
                                </Text>
                                <TouchableOpacity
                                    className="bg-secondary px-4 py-3 rounded-xl items-center border border-secondary shadow-sm"
                                    onPress={() => navigation.navigate("GmailConnector")}
                                >
                                    <Text className="text-white text-sm" style={{ fontFamily: "Inter_600SemiBold" }}>
                                        Open Gmail connector
                                    </Text>
                                </TouchableOpacity>
                            </View>
                        )}

                        {providerKey === "google_tasks" && (
                            <View className="mb-8">
                                <Text className="text-primary text-xs tracking-widest mb-2 uppercase" style={{ fontFamily: "Inter_600SemiBold" }}>
                                    TARGET TASK LIST
                                </Text>
                                <Text className="text-on-surface-variant text-sm mb-4" style={{ fontFamily: "Inter_400Regular" }}>
                                    Currently selected: {status?.selected_resource_name || "None"}
                                </Text>
                                <TouchableOpacity
                                    className="bg-secondary px-4 py-3 rounded-xl items-center border border-secondary shadow-sm"
                                    onPress={openTaskListPicker}
                                    disabled={saving || pickingBusy}
                                >
                                    <Text className="text-white text-sm" style={{ fontFamily: "Inter_600SemiBold" }}>
                                        {status?.selected_resource_id ? "Change List" : "Choose List"}
                                    </Text>
                                </TouchableOpacity>
                            </View>
                        )}

                        {/* RECENT ACTIVITY */}
                        <View className="mb-8">
                            <Text className="text-primary text-xs tracking-widest mb-2 uppercase" style={{ fontFamily: "Inter_600SemiBold" }}>
                                RECENT ACTIVITY
                            </Text>
                            <ActivityFeed history={history} />
                        </View>

                        {/* Disconnect */}
                        <TouchableOpacity className="mt-5 p-4 items-center rounded-xl bg-red-50 border border-red-100" onPress={handleDisconnect}>
                            <Text className="text-red-500 text-base" style={{ fontFamily: "Inter_500Medium" }}>Disconnect</Text>
                        </TouchableOpacity>
                    </>
                )}
            </ScrollView>

            <TaskListPicker
                visible={pickerOpen}
                loading={listsLoading}
                taskLists={taskLists}
                isBusy={pickingBusy}
                onPick={handlePickList}
                onClose={() => setPickerOpen(false)}
            />
        </View>
    );
}
