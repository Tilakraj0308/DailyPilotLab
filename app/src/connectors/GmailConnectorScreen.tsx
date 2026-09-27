import React, { useCallback, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  TextInput,
  Switch,
} from "react-native";
import { useNavigation, useFocusEffect } from "@react-navigation/native";
import { ArrowLeft } from "lucide-react-native";

import { useAuth } from "../context/AuthContext";
import { universalAlert } from "../lib/alerts";
import { getCache, setCache } from "../lib/cache";
import {
  createGmailDraft,
  fetchGmailPriority,
  fetchGmailThread,
  sendGmailDraft,
  suggestGmailReplyDraft,
  GmailThreadDetail,
  GmailThreadSummary,
} from "./api";

function replySubject(original: string | undefined | null): string {
  const s = (original || "").trim();
  if (!s) return "Re: ";
  if (/^re:\s*/i.test(s)) return s;
  return `Re: ${s}`;
}

function extractEmail(fromHeader: string | undefined): string {
  if (!fromHeader) return "";
  const trimmed = fromHeader.trim();
  const angle = trimmed.match(/<([^>]+)>/);
  if (angle) return angle[1].trim();
  if (trimmed.includes("@")) return trimmed;
  return "";
}

function parseAddressList(raw: string): string[] {
  return raw
    .split(/[;,]/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function normalizeEmailAddr(fromHeader: string | undefined): string {
  return extractEmail(fromHeader || "").trim().toLowerCase();
}

/** Prefer latest message From that is not the signed-in user; else last message From. */
function replyToFromThread(detail: GmailThreadDetail, userEmail: string | undefined): string {
  const self = (userEmail || "").trim().toLowerCase();
  const msgs = detail.messages;
  for (let i = msgs.length - 1; i >= 0; i--) {
    const rawFrom = msgs[i]?.headers?.from;
    if (!rawFrom) continue;
    const addr = normalizeEmailAddr(rawFrom);
    if (!addr) continue;
    if (self && addr === self) continue;
    return extractEmail(rawFrom) || rawFrom.trim();
  }
  const last = msgs[msgs.length - 1];
  const lf = last?.headers?.from;
  if (!lf) return "";
  return extractEmail(lf) || lf.trim();
}

function formatPriorityTime(internalDateMs: string | null | undefined): string {
  if (internalDateMs == null || internalDateMs === "") return "";
  const n = Number(internalDateMs);
  if (!Number.isFinite(n)) return "";
  const d = new Date(n);
  const diff = Date.now() - n;
  if (diff < 60_000) return "Now";
  if (diff < 86_400_000)
    return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function GmailConnectorScreen() {
  const navigation = useNavigation();
  const { session, user } = useAuth();
  const token = session?.access_token;
  const userEmail = user?.email ?? undefined;

  const [loadingList, setLoadingList] = useState(true);
  const [priorityItems, setPriorityItems] = useState<GmailThreadSummary[]>([]);
  const [queryLabel, setQueryLabel] = useState("");

  const [selectedSummary, setSelectedSummary] = useState<GmailThreadSummary | null>(null);
  const [threadDetail, setThreadDetail] = useState<GmailThreadDetail | null>(null);
  const [loadingThread, setLoadingThread] = useState(false);

  const [toField, setToField] = useState("");
  const [subjectField, setSubjectField] = useState("");
  const [bodyField, setBodyField] = useState("");

  const [creating, setCreating] = useState(false);
  const [suggestingAi, setSuggestingAi] = useState(false);
  const [sending, setSending] = useState(false);
  const [draftId, setDraftId] = useState<string | null>(null);
  const [reviewed, setReviewed] = useState(false);

  const userId = user?.id || session?.user?.id;
  const cacheKey = userId ? `@gmail_priority_${userId}` : null;

  const loadPriority = useCallback(async () => {
    if (!token) {
      setPriorityItems([]);
      setLoadingList(false);
      return;
    }

    if (cacheKey) {
      const cached = await getCache<{ query: string; items: GmailThreadSummary[] }>(cacheKey);
      if (cached && cached.items) {
        setQueryLabel(cached.query || "");
        setPriorityItems(cached.items);
        setLoadingList(false);
      }
    }

    try {
      const res = await fetchGmailPriority(token);
      setQueryLabel(res.query);
      setPriorityItems(res.items ?? []);
      if (cacheKey) {
        await setCache(cacheKey, { query: res.query, items: res.items ?? [] });
      }
    } catch (e: any) {
      universalAlert("Gmail", e?.message || "Could not load priority threads.");
    } finally {
      setLoadingList(false);
    }
  }, [token, cacheKey]);

  useFocusEffect(
    useCallback(() => {
      loadPriority().catch(() => undefined);
    }, [loadPriority])
  );

  const resetDraftFlow = () => {
    setDraftId(null);
    setReviewed(false);
  };

  const openThread = async (summary: GmailThreadSummary) => {
    if (!token) return;
    setSelectedSummary(summary);
    setThreadDetail(null);
    resetDraftFlow();
    setBodyField("");
    setLoadingThread(true);
    try {
      const detail = await fetchGmailThread(token, summary.id);
      setThreadDetail(detail);
      const subj =
        summary.subject ||
        detail.messages[0]?.headers?.subject ||
        detail.snippet ||
        "";
      setSubjectField(replySubject(subj));
      setToField(replyToFromThread(detail, userEmail));
    } catch (e: any) {
      universalAlert("Gmail", e?.message || "Could not load thread.");
      setSelectedSummary(null);
    } finally {
      setLoadingThread(false);
    }
  };

  const clearThreadSelection = () => {
    setSelectedSummary(null);
    setThreadDetail(null);
    setSubjectField("");
    setToField("");
    setBodyField("");
    resetDraftFlow();
  };

  const handleCreateDraft = async () => {
    if (!token) return;
    if (!bodyField.trim()) {
      universalAlert("Draft", "Enter a message body.");
      return;
    }
    setCreating(true);
    resetDraftFlow();
    try {
      const toList = parseAddressList(toField);
      const res = await createGmailDraft(token, {
        thread_id: selectedSummary?.id ?? null,
        to: toList,
        subject: subjectField.trim() || "(no subject)",
        body_text: bodyField,
      });
      setDraftId(res.draft_id);
      universalAlert("Draft created", `Draft id: ${res.draft_id}`);
    } catch (e: any) {
      universalAlert("Gmail", e?.message || "Could not create draft.");
    } finally {
      setCreating(false);
    }
  };

  const handleSuggestAiDraft = async () => {
    if (!token || !selectedSummary?.id) {
      universalAlert("Gmail", "Open a thread first.");
      return;
    }
    setSuggestingAi(true);
    try {
      const out = await suggestGmailReplyDraft(token, selectedSummary.id);
      setBodyField((out.body_text || "").trim());
      const subj = (out.subject || "").trim();
      if (subj && !subjectField.trim()) {
        setSubjectField(subj);
      }
      if (draftId) resetDraftFlow();
    } catch (e: any) {
      universalAlert("Gmail", e?.message || "Could not get AI draft.");
    } finally {
      setSuggestingAi(false);
    }
  };

  const handleSendDraft = async () => {
    if (!token || !draftId) return;
    if (!reviewed) {
      universalAlert("Send", "Confirm you reviewed the draft first.");
      return;
    }
    setSending(true);
    try {
      const out = await sendGmailDraft(token, draftId);
      universalAlert("Sent", `Message id: ${out.id}`);
      resetDraftFlow();
      setBodyField("");
    } catch (e: any) {
      universalAlert("Gmail", e?.message || "Could not send draft.");
    } finally {
      setSending(false);
    }
  };

  return (
    <View className="flex-1 bg-surface">
      <View className="pt-16 pb-4 px-5 flex-row items-center border-b border-outline-variant/15 bg-surface-container-lowest">
        <TouchableOpacity className="mr-4 p-1" onPress={() => navigation.goBack()}>
          <ArrowLeft color="#1e293b" size={24} />
        </TouchableOpacity>
        <Text className="text-on-surface text-xl flex-1" style={{ fontFamily: "Inter_600SemiBold" }}>
          Gmail
        </Text>
      </View>

      <ScrollView
        contentContainerStyle={{ padding: 20, paddingBottom: 48 }}
        showsVerticalScrollIndicator={false}
      >
        <Text
          className="text-primary text-xs tracking-widest mb-2 uppercase"
          style={{ fontFamily: "Inter_600SemiBold" }}
        >
          Priority ({queryLabel || "inbox"})
        </Text>

        {loadingList ? (
          <View className="py-8 items-center">
            <ActivityIndicator size="large" color="#4f46e5" />
          </View>
        ) : priorityItems.length === 0 ? (
          <Text className="text-on-surface-variant text-sm mb-6" style={{ fontFamily: "Inter_400Regular" }}>
            No threads in this view.
          </Text>
        ) : (
          <View className="mb-6 gap-2">
            {priorityItems.map((row) => {
              const active = selectedSummary?.id === row.id;
              const unread = (row.label_ids || []).includes("UNREAD");
              const timeLabel = formatPriorityTime(row.internal_date_ms ?? undefined);
              return (
                <TouchableOpacity
                  key={row.id}
                  onPress={() => openThread(row)}
                  className={`rounded-xl p-3 border ${active ? "border-secondary bg-secondary-container/40" : "border-outline-variant/20 bg-surface-container-lowest"
                    }`}
                >
                  <View className="flex-row items-start justify-between gap-2">
                    <Text
                      className="text-on-surface text-sm flex-1"
                      numberOfLines={1}
                      style={{ fontFamily: "Inter_600SemiBold" }}
                    >
                      {row.subject || "(no subject)"}
                    </Text>
                    <View className="flex-row items-center shrink-0 gap-1.5">
                      {unread ? (
                        <View className="bg-indigo-600 px-2 py-0.5 rounded-full">
                          <Text className="text-white text-[10px]" style={{ fontFamily: "Inter_600SemiBold" }}>
                            Unread
                          </Text>
                        </View>
                      ) : null}
                      {timeLabel ? (
                        <Text className="text-on-surface-variant text-[10px]" style={{ fontFamily: "Inter_500Medium" }}>
                          {timeLabel}
                        </Text>
                      ) : null}
                    </View>
                  </View>
                  <Text className="text-on-surface-variant text-xs mt-1" numberOfLines={1}>
                    {row.from_addr || ""}
                  </Text>
                  <Text className="text-on-surface-variant text-xs mt-1" numberOfLines={2}>
                    {row.snippet || ""}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>
        )}

        {selectedSummary && (
          <View className="mb-6">
            <View className="flex-row items-center justify-between mb-2">
              <Text
                className="text-primary text-xs tracking-widest uppercase"
                style={{ fontFamily: "Inter_600SemiBold" }}
              >
                Thread
              </Text>
              <TouchableOpacity onPress={clearThreadSelection}>
                <Text className="text-secondary text-xs" style={{ fontFamily: "Inter_600SemiBold" }}>
                  New mail
                </Text>
              </TouchableOpacity>
            </View>
            {loadingThread ? (
              <ActivityIndicator color="#4f46e5" />
            ) : threadDetail ? (
              <View className="rounded-xl border border-outline-variant/20 bg-surface-container-lowest p-3 max-h-64">
                <ScrollView nestedScrollEnabled>
                  {threadDetail.messages.map((m) => {
                    const isDraft = (m.labelIds || []).includes("DRAFT");
                    return (
                      <View key={m.id} className="mb-3 border-b border-outline-variant/10 pb-3 last:border-0">
                        {isDraft ? (
                          <Text
                            className="text-[10px] text-amber-800 bg-amber-50 border border-amber-200 self-start px-2 py-0.5 rounded-md mb-1"
                            style={{ fontFamily: "Inter_600SemiBold" }}
                          >
                            Draft — not sent
                          </Text>
                        ) : null}
                        <Text className="text-[10px] text-on-surface-variant uppercase mb-1">
                          {m.headers.from || "—"} → {m.headers.to || ""}
                        </Text>
                        {m.headers.subject ? (
                          <Text className="text-xs text-on-surface mb-1" style={{ fontFamily: "Inter_600SemiBold" }}>
                            {m.headers.subject}
                          </Text>
                        ) : null}
                        <Text className="text-xs text-on-surface-variant">{m.snippet || ""}</Text>
                      </View>
                    );
                  })}
                </ScrollView>
              </View>
            ) : null}
          </View>
        )}

        <Text
          className="text-primary text-xs tracking-widest mb-2 uppercase"
          style={{ fontFamily: "Inter_600SemiBold" }}
        >
          Compose draft
        </Text>
        <Text className="text-on-surface-variant text-xs mb-2" style={{ fontFamily: "Inter_400Regular" }}>
          To (comma-separated). Prefilled when you open a thread.
        </Text>
        <TextInput
          className="border border-outline-variant/30 rounded-xl px-3 py-2 text-on-surface text-sm mb-3 bg-surface-container-lowest"
          placeholder="recipient@example.com"
          placeholderTextColor="#94a3b8"
          value={toField}
          onChangeText={setToField}
          autoCapitalize="none"
          keyboardType="email-address"
        />
        <TextInput
          className="border border-outline-variant/30 rounded-xl px-3 py-2 text-on-surface text-sm mb-3 bg-surface-container-lowest"
          placeholder="Subject"
          placeholderTextColor="#94a3b8"
          value={subjectField}
          onChangeText={setSubjectField}
        />
        <TextInput
          className="border border-outline-variant/30 rounded-xl px-3 py-3 text-on-surface text-sm mb-3 bg-surface-container-lowest min-h-[120px]"
          placeholder="Draft body"
          placeholderTextColor="#94a3b8"
          value={bodyField}
          onChangeText={(t) => {
            setBodyField(t);
            if (draftId) resetDraftFlow();
          }}
          multiline
          textAlignVertical="top"
        />

        <TouchableOpacity
          className="bg-indigo-600 px-4 py-3 rounded-xl items-center mb-4"
          onPress={handleSuggestAiDraft}
          disabled={suggestingAi || !selectedSummary}
        >
          {suggestingAi ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text className="text-white text-sm" style={{ fontFamily: "Inter_600SemiBold" }}>
              Ask AI to draft
            </Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          className="bg-secondary px-4 py-3 rounded-xl items-center mb-4"
          onPress={handleCreateDraft}
          disabled={creating}
        >
          {creating ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text className="text-white text-sm" style={{ fontFamily: "Inter_600SemiBold" }}>
              Create draft
            </Text>
          )}
        </TouchableOpacity>

        {draftId ? (
          <View className="rounded-xl border border-outline-variant/20 bg-surface-container-lowest p-4 mb-4">
            <Text className="text-on-surface text-sm mb-3" style={{ fontFamily: "Inter_500Medium" }}>
              Draft id: {draftId}
            </Text>
            <View className="flex-row items-center justify-between mb-4">
              <Text className="text-on-surface text-sm flex-1 pr-3" style={{ fontFamily: "Inter_500Medium" }}>
                I reviewed this draft
              </Text>
              <Switch value={reviewed} onValueChange={setReviewed} trackColor={{ true: "#4f46e5", false: "#cbd5e1" }} />
            </View>
            <TouchableOpacity
              className={`px-4 py-3 rounded-xl items-center ${reviewed ? "bg-emerald-600" : "bg-slate-300"}`}
              onPress={handleSendDraft}
              disabled={!reviewed || sending}
            >
              {sending ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text className="text-white text-sm" style={{ fontFamily: "Inter_600SemiBold" }}>
                  Send draft
                </Text>
              )}
            </TouchableOpacity>
          </View>
        ) : null}
      </ScrollView>
    </View>
  );
}
