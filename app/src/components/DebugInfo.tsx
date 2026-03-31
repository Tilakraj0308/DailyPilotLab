import { useEffect, useState } from 'react';
import { Platform } from 'react-native';

/**
 * Debug component - shows which API URL is being used
 * Add this to your ChatScreen to see which URL the app is connecting to
 */
export function DebugInfo() {
    const [apiUrl, setApiUrl] = useState('');
    const [wsUrl, setWsUrl] = useState('');

    useEffect(() => {
        const envUrl = process.env.EXPO_PUBLIC_API_URL;
        let finalUrl = '';

        // Replicate the same logic from useChatSocket and AuthContext
        if (!Platform.OS || Platform.OS === 'web') {
            finalUrl = envUrl || 'http://localhost:8000';
        } else if (Platform.OS === 'android') {
            finalUrl = 'http://10.0.2.2:8000';
        } else {
            finalUrl = envUrl || 'http://localhost:8000';
        }

        setApiUrl(finalUrl);
        setWsUrl(finalUrl?.replace('http', 'ws') + '/ws/chat');
    }, []);

    return (
        <div style={{
            position: 'fixed',
            bottom: 10,
            right: 10,
            background: '#000',
            color: '#0f0',
            padding: '10px',
            fontSize: '10px',
            fontFamily: 'monospace',
            maxWidth: '300px',
            zIndex: 9999,
            borderRadius: '4px',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all'
        }}>
            {`DEBUG INFO:
Platform: ${Platform.OS}
ENV_URL: ${process.env.EXPO_PUBLIC_API_URL || 'Not set'}
API_URL: ${apiUrl}
WS_URL: ${wsUrl}`}
        </div>
    );
}
