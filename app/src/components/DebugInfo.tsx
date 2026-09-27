import { useEffect, useState } from 'react';
import { Platform } from 'react-native';
import { getApiUrl } from '../lib/api';

/**
 * Debug component - shows which API URL is being used
 * Add this to your ChatScreen to see which URL the app is connecting to
 */
export function DebugInfo() {
    const [apiUrl, setApiUrl] = useState('');
    const [wsUrl, setWsUrl] = useState('');

    useEffect(() => {
        const finalUrl = getApiUrl();

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
