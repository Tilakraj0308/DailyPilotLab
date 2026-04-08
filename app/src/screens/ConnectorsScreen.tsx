import React, { useState, useEffect, useCallback } from "react";
import {
    View,
    Text,
    ScrollView,
    TouchableOpacity,
    Alert,
    Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { MaterialIcons } from "@expo/vector-icons";
import { useNavigation, useRoute, RouteProp } from "@react-navigation/native";
import * as WebBrowser from "expo-web-browser";
import { makeRedirectUri } from "expo-auth-session";

import { useAuth } from "../context/AuthContext";
import ConnectorTile from "../components/ConnectorTile";
import ConsentModal from "../components/ConsentModal";
import {
    ConnectorStatus,
    getConnectors,
    startGoogleCalendarConnect,
    disconnectGoogleCalendar,
} from "../lib/connectors";

type ConnectorsRouteParams = {
    Connectors: {
        callbackStatus?: string;
        callbackReason?: string;
    };
};

const CONNECTOR_CALLBACK_REDIRECT = makeRedirectUri({
    path: "connectors/callback",
});

export default function ConnectorsScreen() {
    const navigation = useNavigation<any>();
    const route = useRoute<RouteProp<ConnectorsRouteParams, "Connectors">>();
    const { session } = useAuth();

    // State
    const [connectors, setConnectors] = useState<ConnectorStatus[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [consentVisible, setConsentVisible] = useState(false);
    const [connectingProvider, setConnectingProvider] = useState<string | null>(null);
    const [disconnectingProvider, setDisconnectingProvider] = useState<string | null>(null);

    const token = session?.access_token;

    // ── Fetch connector statuses ──
    const fetchConnectors = useCallback(async () => {
        if (!token) return;
        try {
            const data = await getConnectors(token);
            setConnectors(data);
        } catch (e) {
            console.error("Failed to fetch connectors:", e);
        } finally {
            setIsLoading(false);
        }
    }, [token]);

    useEffect(() => {
        fetchConnectors();
    }, [fetchConnectors]);

    // ── Handle deep-link callback params ──
    useEffect(() => {
        const status = route.params?.callbackStatus;
        const reason = route.params?.callbackReason;

        if (!status) return;

        if (status === "success") {
            showToast("Connected!", "Google Calendar connected successfully.");
            fetchConnectors();
        } else if (status === "error") {
            const messages: Record<string, string> = {
                cancelled: "Connection was cancelled.",
                invalid_state: "Session expired — please try again.",
                exchange_failed: "Failed to connect — please try again.",
                identity_failed: "Could not verify Google account.",
                save_failed: "Failed to save connection — please try again.",
                missing_params: "Connection failed — missing data.",
            };
            showToast("Connection Failed", messages[reason || ""] || "An error occurred.");
        }

        // Clear params after handling
        navigation.setParams({ callbackStatus: undefined, callbackReason: undefined });
    }, [route.params?.callbackStatus]);

    // ── Helpers ──
    function showToast(title: string, message: string) {
        if (Platform.OS === "web") {
            window.alert(`${title}\n${message}`);
        } else {
            Alert.alert(title, message);
        }
    }

    function getCalendarStatus(): ConnectorStatus | undefined {
        return connectors.find((c) => c.provider === "google_calendar");
    }

    // ── Connect flow ──
    const handleConnectCalendar = () => {
        setConsentVisible(true);
    };

    const handleConsentConfirm = async () => {
        if (!token) return;

        setConsentVisible(false);
        setConnectingProvider("google_calendar");

        try {
            const authUrl = await startGoogleCalendarConnect(token);

            if (Platform.OS === "web") {
                window.location.href = authUrl;
                return;
            }

            const result = await WebBrowser.openAuthSessionAsync(
                authUrl,
                CONNECTOR_CALLBACK_REDIRECT
            );

            if (result.type === "success") {
                // The backend already handled the callback and stored tokens.
                // The redirect triggered the deep-link handler which navigated here with params.
                // We just need to refresh.
                await fetchConnectors();
            } else {
                console.log("Browser session result:", result.type);
            }
        } catch (e: any) {
            console.error("Connect error:", e);
            showToast("Connection Error", e.message || "Failed to start connection.");
        } finally {
            setConnectingProvider(null);
        }
    };

    // ── Disconnect flow ──
    const handleDisconnectCalendar = () => {
        const title = "Disconnect Google Calendar";
        const message =
            "This will remove calendar access. You can reconnect at any time.";

        if (Platform.OS === "web") {
            if (window.confirm(`${title}\n${message}`)) {
                performDisconnect();
            }
            return;
        }

        Alert.alert(title, message, [
            { text: "Cancel", style: "cancel" },
            {
                text: "Disconnect",
                style: "destructive",
                onPress: performDisconnect,
            },
        ]);
    };

    const performDisconnect = async () => {
        if (!token) return;
        setDisconnectingProvider("google_calendar");
        try {
            await disconnectGoogleCalendar(token);
            await fetchConnectors();
            showToast("Disconnected", "Google Calendar has been disconnected.");
        } catch (e: any) {
            console.error("Disconnect error:", e);
            showToast("Error", e.message || "Failed to disconnect.");
        } finally {
            setDisconnectingProvider(null);
        }
    };

    // ── Derived state ──
    const calendarStatus = getCalendarStatus();
    const isCalendarConnected = calendarStatus?.connected ?? false;
    const calendarNeedsReconnect = calendarStatus?.needs_reconnect ?? false;

    return (
        <SafeAreaView className="flex-1 bg-background">
            {/* Header */}
            <View className="flex-row items-center px-5 py-4 border-b border-outline-variant/10 bg-background">
                <TouchableOpacity
                    onPress={() => navigation.goBack()}
                    className="mr-3"
                >
                    <MaterialIcons name="arrow-back" size={24} color="#2b3437" />
                </TouchableOpacity>
                <Text
                    className="text-lg text-on-surface"
                    style={{ fontFamily: "Manrope_700Bold" }}
                >
                    Connected Apps
                </Text>
            </View>

            <ScrollView
                showsVerticalScrollIndicator={false}
                contentContainerStyle={{ paddingBottom: 40 }}
            >
                <View className="px-5 pt-6">
                    {/* Section header */}
                    <Text
                        className="text-[10px] uppercase text-on-surface-variant tracking-widest mb-4"
                        style={{ fontFamily: "Inter_600SemiBold" }}
                    >
                        INTEGRATIONS
                    </Text>

                    {/* Google Calendar tile */}
                    <ConnectorTile
                        name="Google Calendar"
                        icon="event"
                        connected={isCalendarConnected}
                        loading={
                            connectingProvider === "google_calendar" ||
                            disconnectingProvider === "google_calendar"
                        }
                        accountEmail={calendarStatus?.provider_account_email}
                        connectedAt={calendarStatus?.connected_at}
                        lastSyncAt={calendarStatus?.last_sync_at}
                        needsReconnect={calendarNeedsReconnect}
                        onConnect={handleConnectCalendar}
                        onDisconnect={handleDisconnectCalendar}
                    />

                    {/* Future connectors — disabled */}
                    <ConnectorTile
                        name="Google Tasks"
                        icon="check-circle"
                        connected={false}
                        loading={false}
                        needsReconnect={false}
                        disabled
                        onConnect={() => {}}
                        onDisconnect={() => {}}
                    />

                    <ConnectorTile
                        name="Notion"
                        icon="description"
                        connected={false}
                        loading={false}
                        needsReconnect={false}
                        disabled
                        onConnect={() => {}}
                        onDisconnect={() => {}}
                    />

                    <ConnectorTile
                        name="Slack"
                        icon="chat"
                        connected={false}
                        loading={false}
                        needsReconnect={false}
                        disabled
                        onConnect={() => {}}
                        onDisconnect={() => {}}
                    />

                    {/* Info footer */}
                    <View className="mt-6 px-2">
                        <View className="flex-row items-start gap-2">
                            <MaterialIcons name="info-outline" size={14} color="#586064" style={{ marginTop: 1 }} />
                            <Text
                                className="text-xs text-on-surface-variant leading-relaxed flex-1"
                                style={{ fontFamily: "Inter_400Regular" }}
                            >
                                Connected apps can be disconnected at any time. Your data stays
                                private and is only used to power your DailyPilot experience.
                            </Text>
                        </View>
                    </View>
                </View>
            </ScrollView>

            {/* Consent Modal */}
            <ConsentModal
                visible={consentVisible}
                onConfirm={handleConsentConfirm}
                onCancel={() => setConsentVisible(false)}
                loading={connectingProvider === "google_calendar"}
            />
        </SafeAreaView>
    );
}
