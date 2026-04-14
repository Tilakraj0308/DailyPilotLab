import { Alert, Platform } from 'react-native';

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
        // If buttons are provided, try to find a primary/destructive action besides cancel
        if (buttons && buttons.length > 0) {
            const hasCancel = buttons.some(b => b.style === 'cancel');
            const confirmAction = buttons.find(b => b.style !== 'cancel');
            
            // If there's a mix of confirm and cancel, use window.confirm
            if (hasCancel && confirmAction) {
                const confirmed = window.confirm(`${title}\n${message ? message : ''}`);
                if (confirmed && confirmAction.onPress) {
                    confirmAction.onPress();
                } else {
                    const cancelAction = buttons.find(b => b.style === 'cancel');
                    if (cancelAction && cancelAction.onPress) {
                        cancelAction.onPress();
                    }
                }
                return;
            }
            
            // If it's just a single button (like "OK"), default to alert and execute onPress
            window.alert(`${title}\n${message ? message : ''}`);
            if (buttons[0].onPress) {
                buttons[0].onPress();
            }
            return;
        }

        // Just an informational alert
        window.alert(`${title}\n${message ? message : ''}`);
        return;
    }

    // Native implementation
    Alert.alert(title, message, buttons);
}
