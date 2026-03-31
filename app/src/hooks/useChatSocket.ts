import { useState, useEffect, useRef, useCallback } from 'react';
import * as Crypto from 'expo-crypto';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

export type ChatMessage = {
    id: string;
    role: 'user' | 'assistant';
    content: string;
};

const STORE_KEY = '@chat_session_id';

/**
 * Get the API URL based on platform.
 * - Web: localhost:8000
 * - Android Emulator: 10.0.2.2:8000 (if EXPO_PUBLIC_API_URL not set)
 * - Physical Android/iOS: EXPO_PUBLIC_API_URL (must set for physical devices)
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

function getWsUrl(): string {
    const apiUrl = getApiUrl();
    return `${apiUrl?.replace('http', 'ws')}/ws/chat`;
}

export function useChatSocket() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [status, setStatus] = useState<'connecting' | 'connected' | 'reconnecting' | 'error'>('connecting');
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);

    const wsRef = useRef<WebSocket | null>(null);
    const reconnectAttempt = useRef(0);
    const streamingText = useRef('');
    const lastUpdate = useRef(0);
    const updateTimeout = useRef<NodeJS.Timeout | null>(null);
    const isManuallyClosed = useRef(false);

    // Initialize session and test connectivity
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
            
            // Test HTTP connectivity to backend before creating WebSocket
            testBackendConnectivity();
        };
        initSession();
    }, []);

    // Test if backend HTTP endpoint is reachable
    const testBackendConnectivity = async () => {
        try {
            const apiUrl = getApiUrl();
            const response = await fetch(`${apiUrl}/ping`, { 
                method: 'GET',
                timeout: 5000 
            });
            if (response.ok) {
                console.log(`✓ Backend reachable at ${apiUrl}`);
            }
        } catch (e) {
            console.warn(`⚠️ Backend NOT reachable at ${getApiUrl()} - will keep retrying`);
        }
    };

    const connect = useCallback(() => {
        if (!sessionId || isManuallyClosed.current) return;

        setStatus(prev => prev === 'error' || prev === 'reconnecting' ? prev : 'connecting');

        const WS_URL = getWsUrl();
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log(`✓ WebSocket connected to ${WS_URL}`);
            setStatus('connected');
            reconnectAttempt.current = 0;
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                // Handle server keepalive pings
                if (data.type === 'ping') {
                    console.debug('Received keepalive ping from server');
                    return;  // Ignore pings, just keep connection alive
                }

                if (data.type === 'token') {
                    // Response started, no longer waiting
                    if (isWaitingForResponse) {
                        setIsWaitingForResponse(false);
                    }
                    streamingText.current += data.content;
                    throttleUpdate();
                } else if (data.type === 'done') {
                    flushUpdate();
                    streamingText.current = '';
                    setIsWaitingForResponse(false);
                } else if (data.type === 'transcription') {
                    setMessages(prev => [...prev, { id: Crypto.randomUUID(), role: 'user', content: data.content }]);
                } else if (data.type === 'error') {
                    console.error("Chat WS Error:", data.content);
                    setIsWaitingForResponse(false);
                }
            } catch (e) {
                console.error("Failed to parse WebSocket message:", e);
                setIsWaitingForResponse(false);
            }
        };

        ws.onclose = () => {
            if (isManuallyClosed.current) return;

            console.warn('WebSocket closed, attempting to reconnect...');
            setStatus('reconnecting');
            const delays = [500, 1000, 2000, 4000, 8000];
            const delay = delays[Math.min(reconnectAttempt.current, delays.length - 1)];
            reconnectAttempt.current++;

            console.debug(`Reconnecting in ${delay}ms (attempt ${reconnectAttempt.current})`);
            setTimeout(() => {
                if (!isManuallyClosed.current) connect();
            }, delay);
        };

        ws.onerror = (error) => {
            console.error("WebSocket error:", error);
            setStatus('error');
        };

    }, [sessionId]);

    useEffect(() => {
        isManuallyClosed.current = false;
        if (sessionId) connect();

        return () => {
            isManuallyClosed.current = true;
            wsRef.current?.close();
        };
    }, [connect, sessionId]);

    const throttleUpdate = () => {
        const now = Date.now();
        if (now - lastUpdate.current > 50) {
            flushUpdate();
            lastUpdate.current = now;
        } else if (!updateTimeout.current) {
            updateTimeout.current = setTimeout(() => {
                flushUpdate();
                updateTimeout.current = null;
            }, 50);
        }
    };

    const flushUpdate = () => {
        const text = streamingText.current;
        setMessages(prev => {
            const last = prev[prev.length - 1];
            if (last && last.role === 'assistant') {
                const rest = prev.slice(0, -1);
                return [...rest, { ...last, content: text }];
            } else {
                return [...prev, { id: Crypto.randomUUID(), role: 'assistant', content: text }];
            }
        });
    };

    const sendText = (text: string) => {
        if (!text.trim() || status !== 'connected' || !sessionId) return;

        setIsWaitingForResponse(true);
        setMessages(prev => [...prev, { id: Crypto.randomUUID(), role: 'user', content: text }]);
        streamingText.current = '';

        wsRef.current?.send(JSON.stringify({
            type: 'text',
            content: text,
            session_id: sessionId
        }));
    };

    const sendAudio = (base64Data: string) => {
        if (status !== 'connected' || !sessionId) return;

        // Transcription will be sent back from server to show what user said
        streamingText.current = '';

        wsRef.current?.send(JSON.stringify({
            type: 'audio',
            audio_data: base64Data,
            session_id: sessionId
        }));
    };

    const clearSession = async () => {
        isManuallyClosed.current = true;
        wsRef.current?.close();

        const newId = Crypto.randomUUID();
        await AsyncStorage.setItem(STORE_KEY, newId);
        setMessages([]);
        setSessionId(newId);

        // Let effect auto-reconnect with new ID
        isManuallyClosed.current = false;
    };

    return { messages, status, sendText, sendAudio, clearSession, isWaitingForResponse };
}
