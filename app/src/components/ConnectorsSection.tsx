import React, { useCallback, useState, useEffect } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  ActivityIndicator,
  Platform,
  Modal,
  FlatList,
  TextInput,
  Pressable,
} from "react-native";
import * as Linking from "expo-linking";
import { useFocusEffect } from "@react-navigation/native";
import { MaterialIcons } from "@expo/vector-icons";
import { useAuth } from "../context/AuthContext";
import {
  fetchConnectors,
  startConnectorOAuth,
  disconnectConnector,
  GOOGLE_CALENDAR_PROVIDER,
  GOOGLE_TASKS_PROVIDER,
  fetchGoogleTaskLists,
  selectGoogleTaskList,
  fetchGoogleTasks,
  createGoogleTask,
  updateGoogleTask,
  deleteGoogleTask,
  type ConnectorStatusItem,
  type GoogleTaskListItem,
  type GoogleTaskApiItem,
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

function tasksStatusPill(
  status: string | undefined,
  needsSetup: boolean
): { label: string; bg: string; text: string } {
  if (needsSetup && status === "connected") {
    return { label: "Setup needed", bg: "bg-amber-100", text: "text-amber-900" };
  }
  return statusPill(status);
}

function connectedSuccessLabel(provider: string | null): string {
  if (provider === GOOGLE_TASKS_PROVIDER) return "Google Tasks is connected.";
  return "Google Calendar is connected.";
}

/**
 * Integrations block for Profile — loads connector status and OAuth actions.
 */
export default function ConnectorsSection() {
  const { session } = useAuth();
  const [items, setItems] = useState<ConnectorStatusItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const [tasksPickerOpen, setTasksPickerOpen] = useState(false);
  const [taskLists, setTaskLists] = useState<GoogleTaskListItem[]>([]);
  const [listsLoading, setListsLoading] = useState(false);
  const [tasksPreview, setTasksPreview] = useState<GoogleTaskApiItem[]>([]);
  const [quickTitle, setQuickTitle] = useState("");

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
    const provider = params.get("provider");
    if (status === "success") {
      universalAlert("Connected", connectedSuccessLabel(provider));
      window.history.replaceState({}, "", window.location.pathname);
    } else if (status === "error") {
      universalAlert("Connection failed", reason || "Please try again.");
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
      } else if (url.includes("connector_status=error")) {
        load();
        universalAlert("Connection failed", "Check your settings and try again.");
      }
    });
    return () => sub.remove();
  }, [load]);

  const googleCal = items.find((c) => c.provider_key === GOOGLE_CALENDAR_PROVIDER);
  const googleTasks = items.find((c) => c.provider_key === GOOGLE_TASKS_PROVIDER);

  const calConnected = googleCal?.status === "connected";
  const calReauth = googleCal?.status === "reauth_required";
  const calErr = googleCal?.status === "error";
  const calConnecting = googleCal?.status === "connecting";
  const calPill = statusPill(googleCal?.status);

  const tasksConnected = googleTasks?.status === "connected";
  const tasksReauth = googleTasks?.status === "reauth_required";
  const tasksErr = googleTasks?.status === "error";
  const tasksConnecting = googleTasks?.status === "connecting";
  const tasksHasList = Boolean(googleTasks?.selected_resource_id);
  const tasksNeedsSetup = tasksConnected && !tasksHasList;
  const tasksPill = tasksStatusPill(googleTasks?.status, tasksNeedsSetup);

  const refreshTasksPreview = useCallback(async () => {
    if (!token || !tasksHasList) return;
    try {
      const list = await fetchGoogleTasks(token, true);
      setTasksPreview(list.slice(0, 8));
    } catch (e: any) {
      console.warn("tasks preview", e);
    }
  }, [token, tasksHasList]);

  useEffect(() => {
    if (tasksHasList && token) {
      refreshTasksPreview().catch(() => {});
    } else {
      setTasksPreview([]);
    }
  }, [tasksHasList, token, refreshTasksPreview, googleTasks?.selected_resource_id]);

  const handleConnectCalendar = async () => {
    if (!token) return;
    setBusyId(GOOGLE_CALENDAR_PROVIDER);
    try {
      const returnTo = getConnectorReturnUrl();
      const { authorization_url } = await startConnectorOAuth(GOOGLE_CALENDAR_PROVIDER, token, returnTo);
      await openConnectorAuthorizationUrl(authorization_url);
    } catch (e: any) {
      universalAlert("Error", e?.message || "Could not start Google Calendar connection.");
    } finally {
      setBusyId(null);
    }
  };

  const handleConnectTasks = async () => {
    if (!token) return;
    setBusyId(GOOGLE_TASKS_PROVIDER);
    try {
      const returnTo = getConnectorReturnUrl();
      const { authorization_url } = await startConnectorOAuth(GOOGLE_TASKS_PROVIDER, token, returnTo);
      await openConnectorAuthorizationUrl(authorization_url);
    } catch (e: any) {
      universalAlert("Error", e?.message || "Could not start Google Tasks connection.");
    } finally {
      setBusyId(null);
    }
  };

  const handleDisconnect = (providerKey: string) => {
    if (!token) return;
    const label = providerKey === GOOGLE_TASKS_PROVIDER ? "Google Tasks" : "Google Calendar";
    universalAlert("Disconnect", `Remove access to this ${label} connection?`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Disconnect",
        style: "destructive",
        onPress: async () => {
          setBusyId(providerKey);
          try {
            await disconnectConnector(providerKey, token);
            await load();
            if (providerKey === GOOGLE_TASKS_PROVIDER) {
              setTasksPreview([]);
            }
          } catch (e: any) {
            universalAlert("Error", e?.message || "Disconnect failed.");
          } finally {
            setBusyId(null);
          }
        },
      },
    ]);
  };

  const openTaskListPicker = async () => {
    if (!token) return;
    setTasksPickerOpen(true);
    setListsLoading(true);
    setTaskLists([]);
    try {
      const lists = await fetchGoogleTaskLists(token);
      setTaskLists(lists);
    } catch (e: any) {
      universalAlert("Could not load lists", e?.message || "Try again.");
      setTasksPickerOpen(false);
    } finally {
      setListsLoading(false);
    }
  };

  const onPickTaskList = async (item: GoogleTaskListItem) => {
    if (!token) return;
    setBusyId(GOOGLE_TASKS_PROVIDER);
    try {
      await selectGoogleTaskList(token, item.id, item.title);
      setTasksPickerOpen(false);
      await load();
    } catch (e: any) {
      universalAlert("Error", e?.message || "Could not save task list.");
    } finally {
      setBusyId(null);
    }
  };

  const onQuickAddTask = async () => {
    const t = quickTitle.trim();
    if (!token || !t) return;
    setBusyId("tasks_quick_add");
    try {
      await createGoogleTask(token, t);
      setQuickTitle("");
      await refreshTasksPreview();
    } catch (e: any) {
      universalAlert("Error", e?.message || "Could not create task.");
    } finally {
      setBusyId(null);
    }
  };

  const toggleTaskDone = async (task: GoogleTaskApiItem) => {
    if (!token || !task.id) return;
    const done = task.status === "completed";
    setBusyId(`task_${task.id}`);
    try {
      await updateGoogleTask(token, task.id, { completed: !done });
      await refreshTasksPreview();
    } catch (e: any) {
      universalAlert("Error", e?.message || "Could not update task.");
    } finally {
      setBusyId(null);
    }
  };

  const removeTask = (task: GoogleTaskApiItem) => {
    if (!token || !task.id) return;
    universalAlert("Delete task", "Remove this task from Google Tasks?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          setBusyId(`del_${task.id}`);
          try {
            await deleteGoogleTask(token, task.id!);
            await refreshTasksPreview();
          } catch (e: any) {
            universalAlert("Error", e?.message || "Could not delete.");
          } finally {
            setBusyId(null);
          }
        },
      },
    ]);
  };

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
          {/* Google Calendar */}
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
                    {googleCal?.provider_email || "Separate consent from your DailyPilot sign-in"}
                  </Text>
                </View>
              </View>
              <View className={`self-center px-2.5 py-1 rounded-full ${calPill.bg}`}>
                <Text
                  className={`text-[10px] font-semibold ${calPill.text}`}
                  style={{ fontFamily: "Inter_600SemiBold" }}
                >
                  {calPill.label}
                </Text>
              </View>
            </View>

            {(calReauth || calErr || calConnecting) && googleCal?.error_message ? (
              <Text
                className="text-xs text-red-600 mb-4 leading-snug"
                style={{ fontFamily: "Inter_400Regular" }}
              >
                {googleCal.error_message}
              </Text>
            ) : null}

            {calConnected && !calReauth ? (
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
                <Text className="text-red-500 text-base" style={{ fontFamily: "Inter_600SemiBold" }}>
                  Disconnect
                </Text>
              </TouchableOpacity>
            ) : (
              <TouchableOpacity
                onPress={handleConnectCalendar}
                disabled={busyId !== null}
                className="w-full py-3.5 px-4 rounded-xl bg-secondary flex-row items-center justify-center gap-2 shadow-sm"
              >
                {busyId === GOOGLE_CALENDAR_PROVIDER ? (
                  <ActivityIndicator color="#ffffff" size="small" />
                ) : (
                  <MaterialIcons name="link" size={22} color="#ffffff" />
                )}
                <Text className="text-white text-base" style={{ fontFamily: "Inter_600SemiBold" }}>
                  {calReauth || calErr || calConnecting ? "Reconnect calendar" : "Connect Google Calendar"}
                </Text>
              </TouchableOpacity>
            )}
          </View>

          {/* Google Tasks */}
          <View className="bg-surface-container-lowest rounded-2xl p-5 border border-outline-variant/15 shadow-sm">
            <View className="flex-row items-start justify-between gap-3 mb-3">
              <View className="flex-row items-center gap-3 flex-1">
                <View className="w-11 h-11 rounded-2xl bg-secondary-container items-center justify-center">
                  <MaterialIcons name="check-circle" size={24} color="#4e45e4" />
                </View>
                <View className="flex-1 min-w-0">
                  <Text
                    className="text-base text-on-surface"
                    style={{ fontFamily: "Inter_600SemiBold" }}
                    numberOfLines={1}
                  >
                    Google Tasks
                  </Text>
                  <Text
                    className="text-xs text-on-surface-variant mt-0.5"
                    style={{ fontFamily: "Inter_400Regular" }}
                    numberOfLines={2}
                  >
                    {tasksHasList
                      ? `List: ${googleTasks?.selected_resource_name || "Selected list"}`
                      : googleTasks?.provider_email || "One task list per connection (v1)"}
                  </Text>
                </View>
              </View>
              <View className={`self-center px-2.5 py-1 rounded-full ${tasksPill.bg}`}>
                <Text
                  className={`text-[10px] font-semibold ${tasksPill.text}`}
                  style={{ fontFamily: "Inter_600SemiBold" }}
                >
                  {tasksPill.label}
                </Text>
              </View>
            </View>

            {(tasksReauth || tasksErr || tasksConnecting) && googleTasks?.error_message ? (
              <Text
                className="text-xs text-red-600 mb-4 leading-snug"
                style={{ fontFamily: "Inter_400Regular" }}
              >
                {googleTasks.error_message}
              </Text>
            ) : null}

            {tasksConnected && !tasksReauth && tasksNeedsSetup ? (
              <TouchableOpacity
                onPress={openTaskListPicker}
                disabled={busyId !== null}
                className="w-full py-3.5 px-4 rounded-xl bg-amber-500 flex-row items-center justify-center gap-2 shadow-sm mb-2"
              >
                <MaterialIcons name="playlist-add-check" size={22} color="#ffffff" />
                <Text className="text-white text-base" style={{ fontFamily: "Inter_600SemiBold" }}>
                  Choose task list
                </Text>
              </TouchableOpacity>
            ) : null}

            {tasksConnected && tasksHasList && !tasksReauth ? (
              <View className="mb-4 gap-2">
                <TouchableOpacity
                  onPress={openTaskListPicker}
                  disabled={busyId !== null}
                  className="py-2 flex-row items-center gap-2"
                >
                  <MaterialIcons name="edit" size={18} color="#4e45e4" />
                  <Text className="text-sm text-secondary" style={{ fontFamily: "Inter_500Medium" }}>
                    Change task list
                  </Text>
                </TouchableOpacity>
                <View className="flex-row gap-2 items-center">
                  <TextInput
                    className="flex-1 border border-outline-variant/30 rounded-xl px-3 py-2 text-on-surface text-sm"
                    placeholder="Quick add to this list…"
                    placeholderTextColor="#888"
                    value={quickTitle}
                    onChangeText={setQuickTitle}
                    editable={busyId === null}
                  />
                  <TouchableOpacity
                    onPress={onQuickAddTask}
                    disabled={busyId !== null || !quickTitle.trim()}
                    className="px-4 py-2 rounded-xl bg-secondary"
                  >
                    {busyId === "tasks_quick_add" ? (
                      <ActivityIndicator color="#fff" size="small" />
                    ) : (
                      <Text className="text-white text-sm" style={{ fontFamily: "Inter_600SemiBold" }}>
                        Add
                      </Text>
                    )}
                  </TouchableOpacity>
                </View>
                {tasksPreview.length > 0 ? (
                  <View className="mt-2">
                    <Text
                      className="text-[10px] uppercase text-on-surface-variant mb-2"
                      style={{ fontFamily: "Inter_600SemiBold" }}
                    >
                      In this list
                    </Text>
                    {tasksPreview.map((task) => (
                      <View
                        key={task.id || task.title}
                        className="flex-row items-center justify-between py-2 border-b border-outline-variant/10"
                      >
                        <Pressable onPress={() => toggleTaskDone(task)} className="flex-row items-center flex-1 gap-2">
                          <MaterialIcons
                            name={task.status === "completed" ? "check-box" : "check-box-outline-blank"}
                            size={22}
                            color="#4e45e4"
                          />
                          <Text
                            className={`flex-1 text-sm ${task.status === "completed" ? "text-on-surface-variant line-through" : "text-on-surface"}`}
                            style={{ fontFamily: "Inter_400Regular" }}
                            numberOfLines={2}
                          >
                            {task.title || "(untitled)"}
                          </Text>
                        </Pressable>
                        <TouchableOpacity onPress={() => removeTask(task)} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
                          <MaterialIcons name="delete-outline" size={20} color="#ef4444" />
                        </TouchableOpacity>
                      </View>
                    ))}
                  </View>
                ) : null}
              </View>
            ) : null}

            {tasksConnected && !tasksReauth ? (
              <TouchableOpacity
                onPress={() => handleDisconnect(GOOGLE_TASKS_PROVIDER)}
                disabled={busyId !== null}
                className="w-full py-3.5 px-4 rounded-xl border border-outline-variant/25 bg-surface-container flex-row items-center justify-center gap-2"
              >
                {busyId === GOOGLE_TASKS_PROVIDER ? (
                  <ActivityIndicator color="#4e45e4" size="small" />
                ) : (
                  <MaterialIcons name="link-off" size={20} color="#ef4444" />
                )}
                <Text className="text-red-500 text-base" style={{ fontFamily: "Inter_600SemiBold" }}>
                  Disconnect
                </Text>
              </TouchableOpacity>
            ) : (
              <TouchableOpacity
                onPress={handleConnectTasks}
                disabled={busyId !== null}
                className="w-full py-3.5 px-4 rounded-xl bg-secondary flex-row items-center justify-center gap-2 shadow-sm"
              >
                {busyId === GOOGLE_TASKS_PROVIDER ? (
                  <ActivityIndicator color="#ffffff" size="small" />
                ) : (
                  <MaterialIcons name="link" size={22} color="#ffffff" />
                )}
                <Text className="text-white text-base" style={{ fontFamily: "Inter_600SemiBold" }}>
                  {tasksReauth || tasksErr || tasksConnecting ? "Reconnect Google Tasks" : "Connect Google Tasks"}
                </Text>
              </TouchableOpacity>
            )}
          </View>
        </View>
      )}

      <Modal visible={tasksPickerOpen} animationType="slide" transparent>
        <Pressable
          className="flex-1 bg-black/50 justify-end"
          onPress={() => !listsLoading && setTasksPickerOpen(false)}
        >
          <Pressable
            className="bg-surface-container-lowest rounded-t-3xl max-h-[70%] p-4 border-t border-outline-variant/20"
            onPress={(e) => e.stopPropagation()}
          >
            <Text className="text-lg text-on-surface mb-3" style={{ fontFamily: "Inter_600SemiBold" }}>
              Select a task list
            </Text>
            {listsLoading ? (
              <View className="py-12 items-center">
                <ActivityIndicator color="#4e45e4" />
              </View>
            ) : (
              <FlatList
                data={taskLists}
                keyExtractor={(item) => item.id}
                renderItem={({ item }) => (
                  <TouchableOpacity
                    onPress={() => onPickTaskList(item)}
                    disabled={busyId === GOOGLE_TASKS_PROVIDER}
                    className="py-3 border-b border-outline-variant/10"
                  >
                    <Text className="text-base text-on-surface" style={{ fontFamily: "Inter_500Medium" }}>
                      {item.title || "(Untitled list)"}
                    </Text>
                  </TouchableOpacity>
                )}
                ListEmptyComponent={
                  <Text className="text-on-surface-variant py-6 text-center">No task lists found.</Text>
                }
              />
            )}
            <TouchableOpacity
              onPress={() => setTasksPickerOpen(false)}
              className="mt-2 py-3 items-center"
            >
              <Text className="text-secondary" style={{ fontFamily: "Inter_600SemiBold" }}>
                Cancel
              </Text>
            </TouchableOpacity>
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}
