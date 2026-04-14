import React, { useCallback, useState, useEffect } from "react";
import { View, Text, TouchableOpacity, ActivityIndicator, Platform } from "react-native";
import * as Linking from "expo-linking";
import { useFocusEffect } from "@react-navigation/native";
import { MaterialIcons } from "@expo/vector-icons";
import { useAuth } from "../context/AuthContext";
import {
  fetchConnectors,
  startConnectorOAuth,
  disconnectConnector,
  GOOGLE_CALENDAR_PROVIDER,
  type ConnectorStatusItem,
} from "../lib/connectors";
import { getConnectorReturnUrl, openConnectorAuthorizationUrl } from "../lib/oauthConnectorFlow";
import { universalAlert } from "../lib/alerts";

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

/**
 * Integrations block for Profile — loads connector status and OAuth actions.
 */
export default function ConnectorsSection() {
  const { session } = useAuth();
  const [items, setItems] = useState<ConnectorStatusItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const token = session?.access_token;

  const load = useCallback(async () => {
    if (!token) {
      setItems([]);
      setLoading(false);
      return;
    }
    try {
      const res = await fetchConnectors(token);
      setItems(res.connectors);
    } catch (e) {
      console.warn("connectors load", e);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      load().catch((e) => console.warn("connectors load", e));
    }, [load])
  );

  useEffect(() => {
    if (Platform.OS !== "web" || typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const status = params.get("connector_status");
    const reason = params.get("reason");
    if (status === "success") {
      universalAlert("Connected", "Google Calendar is connected.");
      window.history.replaceState({}, "", window.location.pathname);
    } else if (status === "error") {
      universalAlert("Connection failed", reason || "Please try again.");
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  useEffect(() => {
    if (Platform.OS === "web") return;
    const sub = Linking.addEventListener("url", ({ url }) => {
      if (url.includes("connector_status=success")) {
        load();
        universalAlert("Connected", "Google Calendar is connected.");
      } else if (url.includes("connector_status=error")) {
        load();
        universalAlert("Connection failed", "Check your settings and try again.");
      }
    });
    return () => sub.remove();
  }, [load]);

  const handleConnectGoogleCalendar = async () => {
    if (!token) return;
    setBusyId(GOOGLE_CALENDAR_PROVIDER);
    try {
      const returnTo = getConnectorReturnUrl();
      const { authorization_url } = await startConnectorOAuth(
        GOOGLE_CALENDAR_PROVIDER,
        token,
        returnTo
      );
      await openConnectorAuthorizationUrl(authorization_url);
    } catch (e: any) {
      universalAlert("Error", e?.message || "Could not start Google Calendar connection.");
    } finally {
      setBusyId(null);
    }
  };

  const handleDisconnect = (providerKey: string) => {
    if (!token) return;
    universalAlert(
      "Disconnect",
      "Remove access to this Google Calendar connection?",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Disconnect",
          style: "destructive",
          onPress: async () => {
            setBusyId(providerKey);
            try {
              await disconnectConnector(providerKey, token);
              await load();
            } catch (e: any) {
              universalAlert("Error", e?.message || "Disconnect failed.");
            } finally {
              setBusyId(null);
            }
          },
        },
      ]
    );
  };

  const google = items.find((c) => c.provider_key === GOOGLE_CALENDAR_PROVIDER);
  const connected = google?.status === "connected";
  const reauth = google?.status === "reauth_required";
  const err = google?.status === "error";
  const connecting = google?.status === "connecting";
  const pill = statusPill(google?.status);

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
        <View className="bg-surface-container-lowest rounded-2xl p-5 border border-outline-variant/15 shadow-sm">
          <View className="flex-row items-start justify-between gap-3 mb-3">
            <View className="flex-row items-center gap-3 flex-1">
              <View className="w-11 h-11 rounded-2xl bg-secondary-container items-center justify-center">
                <MaterialIcons name="event" size={24} color="#4e45e4" />
              </View>
              <View className="flex-1 min-w-0">
                <Text
                  className="text-base text-on-surface"
                  style={{ fontFamily: "Inter_600SemiBold" }}
                  numberOfLines={1}
                >
                  Google Calendar
                </Text>
                <Text
                  className="text-xs text-on-surface-variant mt-0.5"
                  style={{ fontFamily: "Inter_400Regular" }}
                  numberOfLines={1}
                >
                  {google?.provider_email || "Separate consent from your DailyPilot sign-in"}
                </Text>
              </View>
            </View>
            <View className={`self-center px-2.5 py-1 rounded-full ${pill.bg}`}>
              <Text
                className={`text-[10px] font-semibold ${pill.text}`}
                style={{ fontFamily: "Inter_600SemiBold" }}
              >
                {pill.label}
              </Text>
            </View>
          </View>

          {(reauth || err || connecting) && google?.error_message ? (
            <Text
              className="text-xs text-red-600 mb-4 leading-snug"
              style={{ fontFamily: "Inter_400Regular" }}
            >
              {google.error_message}
            </Text>
          ) : null}

          {connected && !reauth ? (
            <TouchableOpacity
              onPress={() => handleDisconnect(GOOGLE_CALENDAR_PROVIDER)}
              disabled={busyId !== null}
              className="w-full py-3.5 px-4 rounded-xl border border-outline-variant/25 bg-surface-container flex-row items-center justify-center gap-2"
            >
              {busyId === GOOGLE_CALENDAR_PROVIDER ? (
                <ActivityIndicator color="#4e45e4" size="small" />
              ) : (
                <MaterialIcons name="link-off" size={20} color="#ef4444" />
              )}
              <Text
                className="text-red-500 text-base"
                style={{ fontFamily: "Inter_600SemiBold" }}
              >
                Disconnect
              </Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity
              onPress={handleConnectGoogleCalendar}
              disabled={busyId !== null}
              className="w-full py-3.5 px-4 rounded-xl bg-secondary flex-row items-center justify-center gap-2 shadow-sm"
            >
              {busyId === GOOGLE_CALENDAR_PROVIDER ? (
                <ActivityIndicator color="#ffffff" size="small" />
              ) : (
                <MaterialIcons name="link" size={22} color="#ffffff" />
              )}
              <Text
                className="text-white text-base"
                style={{ fontFamily: "Inter_600SemiBold" }}
              >
                {reauth || err || connecting ? "Reconnect calendar" : "Connect Google Calendar"}
              </Text>
            </TouchableOpacity>
          )}
        </View>
      )}
    </View>
  );
}
