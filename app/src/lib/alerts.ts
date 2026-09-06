import { Alert, Platform, DeviceEventEmitter } from 'react-native';

interface AlertButton {
    text: string;
    style?: 'cancel' | 'destructive' | 'default';
    onPress?: () => void;
}

export function universalAlert(
    title: string,
    message?: string,
    buttons?: AlertButton[]
) {
    if (Platform.OS === 'web') {
        if (buttons && buttons.length > 0) {
            // Find the destructive or primary action
            const actionBtn = buttons.find(b => b.style === 'destructive' || b.text !== 'Cancel');
            if (actionBtn && actionBtn.onPress) {
                // If it's a confirmation
                if (window.confirm(`${title}\n\n${message || ''}`)) {
                    actionBtn.onPress();
                }
            } else {
                window.alert(`${title}\n\n${message || ''}`);
            }
        } else {
            window.alert(`${title}\n\n${message || ''}`);
        }
        return;
    }

    // Native implementation
    Alert.alert(title, message, buttons);
}
