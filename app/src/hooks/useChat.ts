import { useState, useEffect } from 'react';
import * as Crypto from 'expo-crypto';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import EventSource from 'react-native-sse';
export type ChatMessage = {
    id: string;
    role: 'user' | 'assistant';
    content: string;
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
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [status, setStatus] = useState<'connecting' | 'connected' | 'reconnecting' | 'error'>('connecting');
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);

    useEffect(() => {
        const initSession = async () => {
            const saved = await AsyncStorage.getItem(STORE_KEY);
            if (saved) {
                setSessionId(saved);
            } else {
                const newId = Crypto.randomUUID();
                await AsyncStorage.setItem(STORE_KEY, newId);
                setSessionId(newId);
            }
            setStatus('connected');
        };
        initSession();
    }, []);

    const sendText = async (text: string) => {
        if (!text.trim() || status !== 'connected' || !sessionId) return;

        setIsWaitingForResponse(true);
        setMessages(prev => [...prev, { id: Crypto.randomUUID(), role: 'user', content: text }]);

        try {
            const apiUrl = getApiUrl();
            let assistantMessageId = Crypto.randomUUID();
            let assistantMessageContent = '';

            // Add placeholder message
            setMessages(prev => [...prev, { id: assistantMessageId, role: 'assistant', content: '' }]);

            const es = new EventSource(`${apiUrl}/chat/stream`, {
                headers: { 'Content-Type': 'application/json' },
                method: 'POST',
                body: JSON.stringify({ session_id: sessionId, content: text })
            });

            es.addEventListener('message', (event: any) => {
                if (!event.data) return;
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'token') {
                        setIsWaitingForResponse(false);
                        assistantMessageContent += data.content;
                        setMessages(prev => {
                            const rest = prev.slice(0, -1);
                            return [...rest, { id: assistantMessageId, role: 'assistant', content: assistantMessageContent }];
                        });
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

    const sendAudio = async (uri: string): Promise<string | null> => {
        if (status !== 'connected' || !sessionId) return null;

        try {
            const formData = new FormData();
            formData.append('file', {
                uri,
                name: 'audio.m4a',
                type: 'audio/m4a'
            } as any);

            const apiUrl = getApiUrl();
            const response = await fetch(`${apiUrl}/transcribe`, {
                method: 'POST',
                body: formData,
                headers: {
                    'Accept': 'application/json'
                }
            });

            const data = await response.json();
            if (data.success && data.text) {
                return data.text;
            } else {
                throw new Error(data.error || 'Failed to transcribe audio');
            }
        } catch (error) {
            console.error('Audio Transcription Error:', error);
            return null;
        }
    };

    const clearSession = async () => {
        const newId = Crypto.randomUUID();
        await AsyncStorage.setItem(STORE_KEY, newId);
        setMessages([]);
        setSessionId(newId);
    };

    return { messages, status, sendText, sendAudio, clearSession, isWaitingForResponse };
}
