import { useState, useEffect, useRef } from 'react';
import * as Crypto from 'expo-crypto';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform, Linking } from 'react-native';
import EventSource from 'react-native-sse';
import * as FileSystem from 'expo-file-system/legacy';
import { FileSystemUploadType } from 'expo-file-system/legacy';
import { supabase } from '../lib/supabase';
import { useAuth } from '../context/AuthContext';

export type ChatMessage = {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    created_at?: string;
    toolName?: string;
    toolArgs?: string;
};

export type ChatSessionSummary = {
    id: string;
    updated_at: string;
    created_at: string;
    title: string | null;
};


const STORE_KEY = '@chat_session_id';


/**
 * Get the API URL based on platform.
 */
function getApiUrl(): string {
    const envUrl = process.env.EXPO_PUBLIC_API_URL;

    // For web/expo-web
    if (!Platform.OS || Platform.OS === 'web') {
        return envUrl || 'http://localhost:8000';
    }

    // If environment variable is set, use it (physical device)
    if (envUrl) {
        return envUrl;
    }

    // For Android emulator ONLY (when envUrl is not set), use special 10.0.2.2 address
    if (Platform.OS === 'android') {
        return 'http://10.0.2.2:8000';
    }

    // For iOS simulator & physical devices without env var, use localhost
    return 'http://localhost:8000';
}

export function useChat() {
    const { user, isLoading: authLoading } = useAuth();
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [status, setStatus] = useState<'connecting' | 'connected' | 'reconnecting' | 'error'>('connecting');
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
    const [isLoadingHistory, setIsLoadingHistory] = useState(true); // default true 
    const [hasMoreHistory, setHasMoreHistory] = useState(true);

    const pollingRef = useRef<NodeJS.Timeout | null>(null);

    const stopPolling = () => {
        if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
        }
    };

    const pollForResponse = () => {
        stopPolling();
        let attempts = 0;
        pollingRef.current = setInterval(async () => {
            attempts++;
            if (attempts > 8) {
                stopPolling();
                setIsWaitingForResponse(false);
                return;
            }

            try {
                const apiUrl = getApiUrl();
                const { data } = await supabase.auth.getSession();
                const token = data?.session?.access_token;
                const res = await fetch(`${apiUrl}/chat/history?limit=15&offset=0`, {
                    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
                });
                if (res.ok) {
                    const json = await res.json();
                    if (json.history && json.history.length > 0) {
                        const fetchedMessages = json.history.map((m: any) => ({
                            id: m.id || Crypto.randomUUID(),
                            role: m.role,
                            content: m.content,
                            created_at: m.created_at,
                            toolName: m.toolName
                        }));
                        if (fetchedMessages[0] && fetchedMessages[0].role === 'assistant') {
                            setMessages(fetchedMessages);
                            setIsWaitingForResponse(false);
                            stopPolling();
                        }
                    }
                }
            } catch (e) {
                console.error("Polling history error:", e);
            }
        }, 2000);
    };

    const fetchHistory = async (offset: number = 0, limit: number = 15, append: boolean = false) => {
        if (!append) {
            setIsLoadingHistory(true);
        }
        try {
            const apiUrl = getApiUrl();
            const { data } = await supabase.auth.getSession();
            const token = data?.session?.access_token;
            const res = await fetch(`${apiUrl}/chat/history?limit=${limit}&offset=${offset}`, {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });
            if (res.ok) {
                const json = await res.json();
                if (json.history) {
                    const newMessages = json.history.map((m: any) => ({
                        id: m.id || Crypto.randomUUID(),
                        role: m.role,
                        content: m.content,
                        created_at: m.created_at,
                        toolName: m.toolName,
                        toolArgs: m.toolArgs
                    }));
                    if (newMessages.length < limit) {
                        setHasMoreHistory(false);
                    }
                    if (append) {
                        setMessages(prev => [...prev, ...newMessages]);
                    } else {
                        // If the latest message in DB is from user, an assistant response is in progress
                        if (!append && newMessages.length > 0 && newMessages[0].role === 'user') {
                            setIsWaitingForResponse(true);
                            const pendingPlaceholder: ChatMessage = {
                                id: 'pending-assistant',
                                role: 'assistant',
                                content: '',
                                created_at: new Date().toISOString()
                            };
                            setMessages([pendingPlaceholder, ...newMessages]);
                            pollForResponse();
                        } else {
                            setIsWaitingForResponse(false);
                            setMessages(newMessages);
                        }
                    }
                    setIsLoadingHistory(false);
                    return json.history.length;
                }
            } else {
                setHasMoreHistory(false);
            }
        } catch (e) {
            console.error("Failed to fetch history:", e);
            setHasMoreHistory(false);
        }
        setIsLoadingHistory(false);
        return 0;
    };

    useEffect(() => {
        return () => {
            stopPolling();
        };
    }, []);

    useEffect(() => {
        // Fetch initial continuous history
        setStatus('connected');
        fetchHistory(0, 30, false).then(() => {
            // Check if returning from a successful OAuth flow
            if (Platform.OS === 'web' && typeof window !== 'undefined') {
                const params = new URLSearchParams(window.location.search);
                if (params.get('connector_status') === 'success') {
                    AsyncStorage.getItem('@pending_reauth_prompt').then(savedPrompt => {
                        if (savedPrompt) {
                            AsyncStorage.removeItem('@pending_reauth_prompt').catch(console.error);
                            if (window.history && window.history.replaceState) {
                                window.history.replaceState({}, document.title, window.location.pathname);
                            }
                            console.log('🔄 Auto-retrying prompt after re-authentication:', savedPrompt);
                            sendText(savedPrompt);
                        }
                    }).catch(console.error);
                }
            }
        });
    }, [authLoading, user?.id]);

    const sendText = async (text: string) => {
        if (!text.trim() || status !== 'connected') return;

        setIsWaitingForResponse(true);
        // Prepend new messages (index 0)
        setMessages(prev => [{ id: Crypto.randomUUID(), role: 'user', content: text, created_at: new Date().toISOString() }, ...prev]);

        try {
            const apiUrl = getApiUrl();
            let assistantMessageId = Crypto.randomUUID();
            let assistantMessageContent = '';

            // Add placeholder message at index 0
            setMessages(prev => [{ id: assistantMessageId, role: 'assistant', content: '', created_at: new Date().toISOString() }, ...prev]);

            // Get Supabase token
            const { data } = await supabase.auth.getSession();
            const token = data?.session?.access_token;

            const es = new EventSource(`${apiUrl}/chat/stream`, {
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                },
                method: 'POST',
                body: JSON.stringify({ session_id: "continuous", content: text })
            });

            es.addEventListener('message', (event: any) => {
                if (!event.data) return;
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'token') {
                        setIsWaitingForResponse(false);
                        assistantMessageContent += data.content;
                        setMessages(prev => {
                            // The assistant placeholder is at index 0
                            const rest = prev.slice(1);
                            return [{ id: assistantMessageId, role: 'assistant', content: assistantMessageContent, created_at: new Date().toISOString() }, ...rest];
                        });
                    } else if (data.type === 'tool_call') {
                        const toolMsgId = Crypto.randomUUID();
                        const oldAssistantId = assistantMessageId;
                        assistantMessageId = Crypto.randomUUID();
                        assistantMessageContent = '';

                        setMessages(prev => {
                            const filteredPrev = prev.filter(m => m.id !== oldAssistantId);
                            return [
                                // New empty bubble for future text (shows typing indicator)
                                { id: assistantMessageId, role: 'assistant', content: '', created_at: new Date().toISOString() },
                                // The tool call chip
                                { id: toolMsgId, role: 'assistant', content: '', toolName: data.tool_name, toolArgs: data.tool_args, created_at: new Date().toISOString() },
                                ...filteredPrev
                            ];
                        });
                    } else if (data.type === 'reauth_required') {
                        setIsWaitingForResponse(false);
                        es.removeAllEventListeners();
                        es.close();

                        // Clean up placeholder assistant message
                        setMessages(prev => prev.filter(m => m.id !== assistantMessageId));

                        if (data.auth_url) {
                            // Save current pending prompt for auto-retry after re-authentication
                            AsyncStorage.setItem('@pending_reauth_prompt', text).catch(console.error);

                            if (Platform.OS === 'web' && typeof window !== 'undefined') {
                                window.location.href = data.auth_url;
                            } else {
                                Linking.openURL(data.auth_url).catch(console.error);
                            }
                        }
                    } else if (data.type === 'done') {
                        setIsWaitingForResponse(false);
                        es.removeAllEventListeners();
                        es.close();
                    }
                } catch (e) {
                    console.error('Error parsing SSE data line:', e);
                }
            });

            es.addEventListener('error', (event: any) => {
                console.error('Chat SSE Error:', event);
                setIsWaitingForResponse(false);
                es.removeAllEventListeners();
                es.close();
            });

        } catch (error) {
            console.error('Chat Setup Error:', error);
            setIsWaitingForResponse(false);
        }
    };

    const sendAudio = async (uri: string, retryCount = 0): Promise<string | null> => {
        if (status !== 'connected') return null;

        try {
            if (retryCount > 0) {
                await new Promise(resolve => setTimeout(resolve, 500));
            }

            const apiUrl = getApiUrl();
            const { data: authData } = await supabase.auth.getSession();
            const token = authData?.session?.access_token;
            const authHeaders: Record<string, string> = token ? { 'Authorization': `Bearer ${token}` } : {};

            let responseJson: any;

            if (Platform.OS === 'web') {
                // On web, the uri is a blob:// URL — use fetch + FormData directly
                const blobResponse = await fetch(uri);
                const audioBlob = await blobResponse.blob();
                const formData = new FormData();
                formData.append('file', audioBlob, 'recording.webm');

                const uploadResponse = await fetch(`${apiUrl}/transcribe`, {
                    method: 'POST',
                    headers: authHeaders,
                    body: formData,
                });
                responseJson = await uploadResponse.json();
            } else {
                // On native, use expo-file-system for reliable multipart upload
                const fileUri = Platform.OS === 'android' && !uri.startsWith('file://') ? `file://${uri}` : uri;
                const response = await FileSystem.uploadAsync(`${apiUrl}/transcribe`, fileUri, {
                    httpMethod: 'POST',
                    headers: authHeaders,
                    uploadType: FileSystemUploadType.MULTIPART,
                    fieldName: 'file',
                    mimeType: 'audio/m4a',
                });
                responseJson = JSON.parse(response.body);
            }

            if (responseJson.success && responseJson.text) {
                return responseJson.text.trim();
            } else {
                throw new Error(responseJson.error || 'Failed to transcribe audio');
            }
        } catch (error: any) {
            console.error(`Audio Transcription Error (Attempt ${retryCount + 1}):`, error);

            const errorMessage = error?.message || String(error);
            if (retryCount < 2 && (errorMessage.includes('Network request failed') || errorMessage.includes('Socket closed'))) {
                console.log(`Retrying audio upload... (${retryCount + 1}/2)`);
                return sendAudio(uri, retryCount + 1);
            }

            return null;
        }
    };

    return { messages, status, sendText, sendAudio, isWaitingForResponse, isLoadingHistory, fetchHistory, hasMoreHistory };
}
