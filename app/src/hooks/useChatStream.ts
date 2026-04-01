import { useState, useRef, useCallback, useEffect } from 'react';
import * as Crypto from 'expo-crypto';
import EventSource from 'react-native-sse';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

export type ChatMessage = {
    id: string;
    role: 'user' | 'assistant';
    content: string;
};

const STORE_KEY = '@chat_session_id';

function getApiUrl(): string {
    const envUrl = process.env.EXPO_PUBLIC_API_URL;
    if (!Platform.OS || Platform.OS === 'web') return envUrl || 'http://localhost:8000';
    if (envUrl) return envUrl;
    if (Platform.OS === 'android') return 'http://10.0.2.2:8000';
    return 'http://localhost:8000';
}

function getWsUrl(): string {
    const apiUrl = getApiUrl();
    return `${apiUrl?.replace('http', 'ws')}/ws/transcribe`;
}

export function useChatStream() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [status, setStatus] = useState<'idle' | 'streaming' | 'error'>('idle');
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);

    const transcribeWsRef = useRef<WebSocket | null>(null);
    const [transcribedText, setTranscribedText] = useState('');

    useEffect(() => {
        initSession();
    }, []);

    const initSession = async () => {
        if (!sessionId) {
            const saved = await AsyncStorage.getItem(STORE_KEY);
            if (saved) {
                setSessionId(saved);
            } else {
                const newId = Crypto.randomUUID();
                await AsyncStorage.setItem(STORE_KEY, newId);
                setSessionId(newId);
            }
        }
    };

    const sendText = async (text: string) => {
        if (!text.trim()) return;
        await initSession();
        setIsWaitingForResponse(true);
        setStatus('streaming');

        setMessages(prev => [...prev, { id: Crypto.randomUUID(), role: 'user', content: text }]);

        try {
            const apiUrl = getApiUrl();
            const sid = sessionId || await AsyncStorage.getItem(STORE_KEY);
            const es = new EventSource(`${apiUrl}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: sid,
                    content: text
                })
            });

            let botMsgId = Crypto.randomUUID();
            let hasStarted = false;

            es.addEventListener('message', (event) => {
                if (!event.data) return;
                try {
                    const data = JSON.parse(event.data);

                    if (data.type === 'token') {
                        setIsWaitingForResponse(false);
                        if (!hasStarted) {
                            hasStarted = true;
                            setMessages(prev => [...prev, { id: botMsgId, role: 'assistant', content: data.content }]);
                        } else {
                            setMessages(prev => prev.map(m =>
                                m.id === botMsgId ? { ...m, content: m.content + data.content } : m
                            ));
                        }
                    } else if (data.type === 'done') {
                        es.close();
                        setStatus('idle');
                        setIsWaitingForResponse(false);
                    } else if (data.type === 'error') {
                        console.error("Chat SSE Error:", data.content);
                        es.close();
                        setStatus('error');
                        setIsWaitingForResponse(false);
                    }
                } catch (e) {
                    console.error("Failed to parse SSE JSON:", e);
                }
            });

            es.addEventListener('error', (err) => {
                console.error("SSE Connection Error:", err);
                es.close();
                setStatus('error');
                setIsWaitingForResponse(false);
            });

        } catch (error) {
            console.error("Failed to send text via SSE", error);
            setStatus('error');
            setIsWaitingForResponse(false);
        }
    };

    const startLiveTranscription = () => {
        const WS_URL = getWsUrl();
        const ws = new WebSocket(WS_URL);
        transcribeWsRef.current = ws;

        ws.onopen = () => {
            console.log("Transcribe WS connected");
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.text) {
                    setTranscribedText(prev => {
                        return prev + (prev.length > 0 && !prev.endsWith(' ') ? ' ' : '') + data.text;
                    });
                }
            } catch (e) {
                console.error(e);
            }
        };

        ws.onerror = (e) => console.error("Transcribe WS Error:", e);
    };

    const sendAudioChunk = (base64Chunk: string) => {
        if (transcribeWsRef.current?.readyState === WebSocket.OPEN) {
            transcribeWsRef.current.send(JSON.stringify({
                type: 'audio',
                data: base64Chunk
            }));
        }
    };

    const stopLiveTranscription = () => {
        if (transcribeWsRef.current) {
            transcribeWsRef.current.close();
            transcribeWsRef.current = null;
        }
    };

    const clearSession = async () => {
        const newId = Crypto.randomUUID();
        await AsyncStorage.setItem(STORE_KEY, newId);
        setSessionId(newId);
        setMessages([]);
    };

    const resetTranscription = () => setTranscribedText('');

    return {
        messages,
        status,
        sendText,
        clearSession,
        isWaitingForResponse,
        startLiveTranscription,
        sendAudioChunk,
        stopLiveTranscription,
        transcribedText,
        resetTranscription
    };
}
