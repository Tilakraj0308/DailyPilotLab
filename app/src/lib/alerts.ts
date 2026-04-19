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
        DeviceEventEmitter.emit("show_universal_alert", { title, message, buttons });
        return;
    }

    // Native implementation
    Alert.alert(title, message, buttons);
}
