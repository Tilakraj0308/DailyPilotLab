import React from "react";
import { View, Text, TouchableOpacity, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { MaterialIcons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import ConnectorsSection from "../connectors/ConnectorsSection";

export default function ConnectorsScreen() {
    const navigation = useNavigation<any>();

    return (
        <SafeAreaView className="flex-1 bg-background">
            {/* Header */}
            <View className="flex-row items-center px-5 py-4 border-b border-outline-variant/10 bg-background">
                <TouchableOpacity onPress={() => navigation.goBack()} className="mr-3 p-1">
                    <MaterialIcons name="arrow-back" size={24} color="#2b3437" />
                </TouchableOpacity>
                <Text
                    className="text-lg font-bold text-on-surface flex-1"
                    style={{ fontFamily: "Manrope_700Bold" }}
                >
                    Connectors
                </Text>
            </View>

            {/* Content */}
            <ScrollView
                className="flex-1 px-5 pt-4"
                contentContainerStyle={{ paddingBottom: 100 }}
                showsVerticalScrollIndicator={false}
            >
                <View className="mb-6">
                    <Text
                        className="text-sm text-on-surface-variant"
                        style={{ fontFamily: "Inter_400Regular" }}
                    >
                        Connect external services to give your AI agent superpowers.
                    </Text>
                </View>

                <ConnectorsSection />
            </ScrollView>
        </SafeAreaView>
    );
}
