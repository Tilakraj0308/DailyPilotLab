import React from "react";
import { View, Text, TouchableOpacity, ActivityIndicator } from "react-native";
import { MaterialIcons } from "@expo/vector-icons";

export interface ConnectorCardProps {
    title: string;
    description: string;
    iconName: keyof typeof MaterialIcons.glyphMap;
    pill: { label: string; bg: string; text: string };
    errorMessage?: string | null;
    isConnected: boolean;
    isReauth: boolean;
    isConnecting: boolean;
    isError: boolean;
    isBusy: boolean;
    onPressCard: () => void;
}

export default function ConnectorCard({
    title,
    description,
    iconName,
    pill,
    errorMessage,
    isConnected,
    isReauth,
    isConnecting,
    isError,
    isBusy,
    onPressCard,
}: ConnectorCardProps) {
    const showChevron = isConnected && !isReauth;

    return (
        <TouchableOpacity
            onPress={onPressCard}
            disabled={isBusy}
            className="bg-surface-container-lowest rounded-2xl p-5 border border-outline-variant/15 shadow-sm"
        >
            <View pointerEvents={isBusy ? "none" : "auto"}>
                <View className="flex-row items-center justify-between gap-3">
                    <View className="flex-row items-center gap-3 flex-1">
                        <View className="w-11 h-11 rounded-2xl bg-secondary-container items-center justify-center">
                            <MaterialIcons name={iconName} size={24} color="#4e45e4" />
                        </View>
                        <View className="flex-1 min-w-0">
                            <Text
                                className="text-base text-on-surface"
                                style={{ fontFamily: "Inter_600SemiBold" }}
                                numberOfLines={1}
                            >
                                {title}
                            </Text>
                            <Text
                                className="text-xs text-on-surface-variant mt-0.5"
                                style={{ fontFamily: "Inter_400Regular" }}
                                numberOfLines={2}
                            >
                                {description}
                            </Text>
                        </View>
                    </View>

                    {isBusy ? (
                        <ActivityIndicator color="#4e45e4" size="small" />
                    ) : (
                        <View className="flex-row items-center gap-2">
                            <View className={`px-2.5 py-1 rounded-full ${pill.bg}`}>
                                <Text
                                    className={`text-[10px] font-semibold ${pill.text}`}
                                    style={{ fontFamily: "Inter_600SemiBold" }}
                                >
                                    {pill.label}
                                </Text>
                            </View>
                            {showChevron && (
                                <MaterialIcons name="chevron-right" size={20} color="#94a3b8" />
                            )}
                        </View>
                    )}
                </View>

                {(isReauth || isError || isConnecting) && errorMessage ? (
                    <Text
                        className="text-xs text-red-600 mt-4 leading-snug"
                        style={{ fontFamily: "Inter_400Regular" }}
                    >
                        {errorMessage}
                    </Text>
                ) : null}

                {(!isConnected || isReauth) && !isBusy && (
                    <View className="w-full mt-4 py-3 px-4 rounded-xl bg-secondary flex-row items-center justify-center gap-2 shadow-sm">
                        <MaterialIcons name="link" size={20} color="#ffffff" />
                        <Text className="text-white text-sm" style={{ fontFamily: "Inter_600SemiBold" }}>
                            {isReauth || isError || isConnecting ? "Reconnect" : "Connect"}
                        </Text>
                    </View>
                )}
            </View>
        </TouchableOpacity>
    );
}
