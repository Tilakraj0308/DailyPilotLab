import React from "react";
import {
    View,
    Text,
    TouchableOpacity,
    Modal,
    TouchableWithoutFeedback,
} from "react-native";
import { MaterialIcons } from "@expo/vector-icons";

interface ConsentModalProps {
    visible: boolean;
    onConfirm: () => void;
    onCancel: () => void;
    loading?: boolean;
}

export default function ConsentModal({
    visible,
    onConfirm,
    onCancel,
    loading = false,
}: ConsentModalProps) {
    return (
        <Modal
            visible={visible}
            transparent
            animationType="fade"
            onRequestClose={onCancel}
        >
            <TouchableWithoutFeedback onPress={onCancel}>
                <View className="flex-1 bg-black/40 justify-center items-center px-6">
                    <TouchableWithoutFeedback>
                        <View className="bg-surface-container-lowest rounded-2xl p-6 w-full max-w-sm shadow-lg border border-outline-variant/15">
                            {/* Header */}
                            <View className="flex-row items-center gap-3 mb-5">
                                <View className="w-11 h-11 rounded-xl bg-secondary-container items-center justify-center">
                                    <MaterialIcons name="event" size={24} color="#4e45e4" />
                                </View>
                                <Text
                                    className="text-lg text-on-surface"
                                    style={{ fontFamily: "Manrope_700Bold" }}
                                >
                                    Connect Google Calendar
                                </Text>
                            </View>

                            {/* Permissions */}
                            <Text
                                className="text-sm text-on-surface-variant mb-3"
                                style={{ fontFamily: "Inter_500Medium" }}
                            >
                                We will request access to:
                            </Text>

                            <View className="bg-surface-container rounded-xl p-4 mb-4">
                                <View className="flex-row items-center gap-2.5 mb-2.5">
                                    <MaterialIcons name="check-circle" size={18} color="#4e45e4" />
                                    <Text
                                        className="text-sm text-on-surface"
                                        style={{ fontFamily: "Inter_500Medium" }}
                                    >
                                        View your calendar events
                                    </Text>
                                </View>
                                <View className="flex-row items-center gap-2.5">
                                    <MaterialIcons name="check-circle" size={18} color="#4e45e4" />
                                    <Text
                                        className="text-sm text-on-surface"
                                        style={{ fontFamily: "Inter_500Medium" }}
                                    >
                                        See event details & times
                                    </Text>
                                </View>
                            </View>

                            {/* Read-only disclaimer */}
                            <View className="bg-secondary-container/30 rounded-lg p-3 mb-4 flex-row items-start gap-2">
                                <MaterialIcons name="lock" size={14} color="#4e45e4" style={{ marginTop: 1 }} />
                                <Text
                                    className="text-xs text-on-surface-variant flex-1 leading-relaxed"
                                    style={{ fontFamily: "Inter_400Regular" }}
                                >
                                    This is read-only access. We cannot create, edit, or delete any of your events.
                                </Text>
                            </View>

                            {/* Why we need this */}
                            <Text
                                className="text-xs text-on-surface-variant mb-2"
                                style={{ fontFamily: "Inter_600SemiBold" }}
                            >
                                Why we need this:
                            </Text>

                            <View className="mb-6">
                                {[
                                    "Show your upcoming schedule",
                                    "Help you find time gaps",
                                    "Surface conflicts with tasks",
                                ].map((item, idx) => (
                                    <View key={idx} className="flex-row items-center gap-2 mb-1.5">
                                        <View className="w-1 h-1 rounded-full bg-on-surface-variant" />
                                        <Text
                                            className="text-xs text-on-surface-variant"
                                            style={{ fontFamily: "Inter_400Regular" }}
                                        >
                                            {item}
                                        </Text>
                                    </View>
                                ))}
                            </View>

                            {/* Actions */}
                            <View className="flex-row gap-3">
                                <TouchableOpacity
                                    className="flex-1 py-3 rounded-full border border-outline-variant/20 items-center"
                                    onPress={onCancel}
                                    disabled={loading}
                                >
                                    <Text
                                        className="text-sm text-on-surface-variant"
                                        style={{ fontFamily: "Inter_600SemiBold" }}
                                    >
                                        Cancel
                                    </Text>
                                </TouchableOpacity>
                                <TouchableOpacity
                                    className="flex-1 py-3 rounded-full bg-secondary items-center"
                                    onPress={onConfirm}
                                    disabled={loading}
                                >
                                    <Text
                                        className="text-sm text-on-secondary"
                                        style={{ fontFamily: "Inter_600SemiBold" }}
                                    >
                                        {loading ? "Opening…" : "Continue"}
                                    </Text>
                                </TouchableOpacity>
                            </View>
                        </View>
                    </TouchableWithoutFeedback>
                </View>
            </TouchableWithoutFeedback>
        </Modal>
    );
}
