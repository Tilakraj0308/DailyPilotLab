import React, { useState, useEffect } from "react";
import { Platform, Modal, View, Text, TouchableOpacity } from "react-native";
import { DeviceEventEmitter } from "react-native";

export interface AlertButton {
    text: string;
    style?: 'cancel' | 'destructive' | 'default';
    onPress?: () => void;
}

export default function GlobalAlertUI() {
    const [visible, setVisible] = useState(false);
    const [config, setConfig] = useState<{ title: string, message?: string, buttons?: AlertButton[] }>({
        title: ""
    });

    useEffect(() => {
        if (Platform.OS !== "web") return;
        const sub = DeviceEventEmitter.addListener("show_universal_alert", (alertConfig) => {
            setConfig(alertConfig);
            setVisible(true);
        });
        return () => sub.remove();
    }, []);

    if (Platform.OS !== "web" || !visible) return null;

    const handlePress = (onPress?: () => void) => {
        setVisible(false);
        if (onPress) onPress();
    };

    return (
        <Modal visible={visible} transparent animationType="fade">
            <View className="flex-1 bg-black/50 items-center justify-center p-4">
                <View className="bg-surface-container-lowest w-full max-w-sm rounded-[24px] p-6 shadow-xl border border-outline-variant/10">
                    <Text className="text-xl text-on-surface text-center mb-2" style={{ fontFamily: "Inter_600SemiBold" }}>
                        {config.title}
                    </Text>
                    {config.message ? (
                        <Text className="text-sm text-on-surface-variant text-center mb-6 leading-relaxed" style={{ fontFamily: "Inter_400Regular" }}>
                            {config.message}
                        </Text>
                    ) : null}

                    <View className="flex-col gap-3 mt-2">
                        {config.buttons && config.buttons.length > 0 ? (
                            config.buttons.map((btn, i) => (
                                <TouchableOpacity
                                    key={i}
                                    onPress={() => handlePress(btn.onPress)}
                                    className={`w-full py-3.5 rounded-xl items-center justify-center ${btn.style === 'destructive' ? 'bg-red-500' :
                                            btn.style === 'cancel' ? 'bg-surface-container' : 'bg-primary'
                                        }`}
                                >
                                    <Text
                                        className={`text-base ${btn.style === 'destructive' ? 'text-white' :
                                                btn.style === 'cancel' ? 'text-on-surface' : 'text-white'
                                            }`}
                                        style={{ fontFamily: btn.style === 'cancel' ? "Inter_500Medium" : "Inter_600SemiBold" }}
                                    >
                                        {btn.text}
                                    </Text>
                                </TouchableOpacity>
                            ))
                        ) : (
                            <TouchableOpacity
                                onPress={() => handlePress()}
                                className="w-full py-3.5 rounded-xl bg-primary items-center justify-center"
                            >
                                <Text className="text-white text-base" style={{ fontFamily: "Inter_600SemiBold" }}>
                                    OK
                                </Text>
                            </TouchableOpacity>
                        )}
                    </View>
                </View>
            </View>
        </Modal>
    );
}
