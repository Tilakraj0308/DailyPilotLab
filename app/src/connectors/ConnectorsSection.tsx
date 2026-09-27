import React, { useCallback, useState, useEffect } from "react";
import { View, Text, ActivityIndicator, Platform } from "react-native";
import { useFocusEffect, useNavigation } from "@react-navigation/native";
import * as Linking from "expo-linking";

import { useAuth } from "../context/AuthContext";
import {
    fetchConnectors,
    startConnectorOAuth,
    GOOGLE_CALENDAR_PROVIDER,
    GOOGLE_TASKS_PROVIDER,
    GMAIL_PROVIDER,
    ConnectorStatusItem,
} from "./api";
import { getConnectorReturnUrl, openConnectorAuthorizationUrl } from "./oauthFlow";
import { universalAlert } from "../lib/alerts";
import ConnectorCard from "./ConnectorCard";

function statusPill(status: string | undefined): { label: string; bg: string; text: string } {
    switch (status) {
        case "connected":
            return { label: "Connected", bg: "bg-secondary-container", text: "text-secondary-dim" };
        case "connecting":
            return { label: "Connecting…", bg: "bg-primary-container", text: "text-primary-dim" };
        case "reauth_required":
            return { label: "Needs sign-in", bg: "bg-red-100", text: "text-red-800" };
        case "error":
            return { label: "Error", bg: "bg-red-100", text: "text-red-800" };
        default:
            return { label: "Not connected", bg: "bg-surface-container", text: "text-on-surface-variant" };
    }
}

function connectedSuccessLabel(provider: string | null): string {
    if (provider === GOOGLE_TASKS_PROVIDER) return "Google Tasks is connected.";
    if (provider === GMAIL_PROVIDER) return "Gmail is connected.";
    return "Google Calendar is connected.";
}

function humanizeConnectorErrorReason(reason: string | null | undefined): string {
    if (!reason) return "Please try again.";
    return reason;
}

import { getCache, setCache } from "../lib/cache";

export default function ConnectorsSection() {
    const { session, user } = useAuth();
    const navigation = useNavigation<any>();

    const [items, setItems] = useState<ConnectorStatusItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [busyId, setBusyId] = useState<string | null>(null);

    const token = session?.access_token;
    const userId = user?.id || session?.user?.id;
    const cacheKey = userId ? `@connectors_${userId}` : null;

    const load = useCallback(async () => {
        if (!token) {
            setItems([]);
            setLoading(false);
            return;
        }

        // Try reading from cache first for 0ms render
        if (cacheKey) {
            const cached = await getCache<ConnectorStatusItem[]>(cacheKey);
            if (cached && cached.length > 0) {
                setItems(cached);
                setLoading(false);
            }
        }

        try {
            const res = await fetchConnectors(token);
            setItems(res.connectors);
            if (cacheKey) {
                await setCache(cacheKey, res.connectors);
            }
        } catch (e) {
            console.warn("connectors load", e);
        } finally {
            setLoading(false);
        }
    }, [token, cacheKey]);

    useFocusEffect(
        useCallback(() => {
            load().catch((e) => console.warn("connectors load", e));
        }, [load])
    );

    useEffect(() => {
        if (Platform.OS !== "web" || typeof window === "undefined") return;
        const params = new URLSearchParams(window.location.search);
        const status = params.get("connector_status");
        const reason = params.get("reason");
        const provider = params.get("provider");
        if (status === "success") {
            universalAlert("Connected", connectedSuccessLabel(provider));
            window.history.replaceState({}, "", window.location.pathname);
        } else if (status === "error") {
            universalAlert("Connection failed", humanizeConnectorErrorReason(reason));
            window.history.replaceState({}, "", window.location.pathname);
        }
    }, []);

    useEffect(() => {
        if (Platform.OS === "web") return;
        const sub = Linking.addEventListener("url", ({ url }) => {
            const parsed = Linking.parse(url);
            const p = (parsed.queryParams?.provider as string) || null;
            if (url.includes("connector_status=success")) {
                load();
                universalAlert("Connected", connectedSuccessLabel(p));
                if (p) {
                    if (p === GMAIL_PROVIDER) {
                        navigation.navigate("GmailConnector");
                    } else {
                        navigation.navigate("ToolAccess", { provider_key: p });
                    }
                }
            } else if (url.includes("connector_status=error")) {
                load();
                const reason =
                    typeof parsed.queryParams?.reason === "string"
                        ? parsed.queryParams.reason
                        : undefined;
                universalAlert("Connection failed", humanizeConnectorErrorReason(reason));
            }
        });
        return () => sub.remove();
    }, [load]);

    const handleConnectProvider = async (providerKey: string) => {
        if (!token) return;

        const runOAuth = async () => {
            setBusyId(providerKey);
            try {
                const returnTo = getConnectorReturnUrl();
                const { authorization_url } = await startConnectorOAuth(providerKey, token, returnTo);
                await openConnectorAuthorizationUrl(authorization_url);

                // On native, we wait for the browser to close. On web, we are redirecting.
                if (Platform.OS !== "web") {
                    setBusyId(null);
                }
            } catch (e: any) {
                universalAlert("Error", e?.message || "Could not start connection.");
                setBusyId(null);
                await load();
            }
        };

        await runOAuth();
    };

    const handleCardPress = (providerKey: string, isConnected: boolean, isReauth: boolean) => {
        if (!token) return;
        if (isConnected && !isReauth) {
            if (providerKey === GMAIL_PROVIDER) {
                navigation.navigate("GmailConnector");
            } else {
                navigation.navigate("ToolAccess", { provider_key: providerKey });
            }
        } else {
            // Not connected or reauth required, start OAuth flow
            handleConnectProvider(providerKey);
        }
    };

    const googleCal = items.find((c) => c.provider_key === GOOGLE_CALENDAR_PROVIDER);
    const googleTasks = items.find((c) => c.provider_key === GOOGLE_TASKS_PROVIDER);
    const gmail = items.find((c) => c.provider_key === GMAIL_PROVIDER);

    const calConnected = googleCal?.status === "connected";
    const calReauth = googleCal?.status === "reauth_required";
    const calErr = googleCal?.status === "error";
    const calConnecting = googleCal?.status === "connecting";
    const calPill = statusPill(googleCal?.status);

    const tasksConnected = googleTasks?.status === "connected";
    const tasksReauth = googleTasks?.status === "reauth_required";
    const tasksErr = googleTasks?.status === "error";
    const tasksConnecting = googleTasks?.status === "connecting";

    // If connected but no task list is selected, mark it as needing setup
    const tasksHasList = Boolean(googleTasks?.selected_resource_id);
    const tasksNeedsSetup = tasksConnected && !tasksHasList;
    const tasksPill = tasksNeedsSetup
        ? { label: "Setup needed", bg: "bg-amber-100", text: "text-amber-900" }
        : statusPill(googleTasks?.status);

    const gmailConnected = gmail?.status === "connected";
    const gmailReauth = gmail?.status === "reauth_required";
    const gmailErr = gmail?.status === "error";
    const gmailConnecting = gmail?.status === "connecting";
    const gmailPill = statusPill(gmail?.status);

    return (
        <View>
            <Text
                className="text-[10px] uppercase text-on-surface-variant font-semibold tracking-widest mb-3"
                style={{ fontFamily: "Inter_600SemiBold" }}
            >
                Integrations
            </Text>

            {loading ? (
                <View className="py-10 items-center bg-surface-container-lowest rounded-2xl border border-outline-variant/15">
                    <ActivityIndicator color="#4e45e4" />
                </View>
            ) : (
                <View className="gap-4">
                    <ConnectorCard
                        title="Google Calendar"
                        description={googleCal?.provider_email || "Grant calendar access for the AI agent"}
                        iconName="event"
                        pill={calPill}
                        errorMessage={googleCal?.error_message}
                        isConnected={calConnected}
                        isReauth={calReauth}
                        isConnecting={calConnecting}
                        isError={calErr}
                        isBusy={busyId === GOOGLE_CALENDAR_PROVIDER}
                        onPressCard={() => handleCardPress(GOOGLE_CALENDAR_PROVIDER, calConnected, calReauth)}
                    />

                    <ConnectorCard
                        title="Google Tasks"
                        description={
                            googleTasks?.provider_email || "Let the AI read and create tasks for you"
                        }
                        iconName="check-circle"
                        pill={tasksPill}
                        errorMessage={googleTasks?.error_message}
                        isConnected={tasksConnected}
                        isReauth={tasksReauth}
                        isConnecting={tasksConnecting}
                        isError={tasksErr}
                        isBusy={busyId === GOOGLE_TASKS_PROVIDER}
                        onPressCard={() => handleCardPress(GOOGLE_TASKS_PROVIDER, tasksConnected, tasksReauth)}
                    />

                    <ConnectorCard
                        title="Gmail"
                        description={
                            gmail?.provider_email || "Priority inbox and drafts for your connected account"
                        }
                        iconName="mail"
                        pill={gmailPill}
                        errorMessage={gmail?.error_message}
                        isConnected={gmailConnected}
                        isReauth={gmailReauth}
                        isConnecting={gmailConnecting}
                        isError={gmailErr}
                        isBusy={busyId === GMAIL_PROVIDER}
                        onPressCard={() => handleCardPress(GMAIL_PROVIDER, gmailConnected, gmailReauth)}
                    />
                </View>
            )}
        </View>
    );
}
