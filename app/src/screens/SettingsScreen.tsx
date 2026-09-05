import React from "react";
import { View, Text, TouchableOpacity, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { MaterialIcons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";

export default function SettingsScreen() {
  const navigation = useNavigation<any>();

  return (
    <SafeAreaView className="flex-1 bg-background">
      <View className="flex-row items-center px-5 py-4 border-b border-outline-variant/10 bg-background">
        <TouchableOpacity onPress={() => navigation.goBack()} className="mr-3 p-1">
          <MaterialIcons name="arrow-back" size={24} color="#2b3437" />
        </TouchableOpacity>
        <Text
          className="text-lg font-bold text-on-surface flex-1"
          style={{ fontFamily: "Manrope_700Bold" }}
        >
          Settings
        </Text>
      </View>

      <ScrollView className="flex-1 px-5 pt-4" contentContainerStyle={{ paddingBottom: 32 }}>
        <Text
          className="text-sm text-on-surface-variant mb-4"
          style={{ fontFamily: "Inter_400Regular" }}
        >
          Manage app preferences, view token consumption, and configure external services.
        </Text>

        {/* Token Usage & Analytics Button */}
        <TouchableOpacity
          onPress={() => navigation.navigate("TokenUsage")}
          className="bg-surface-container-low p-4 rounded-2xl border border-outline-variant/15 flex-row items-center justify-between mb-3 active:opacity-80"
        >
          <View className="flex-row items-center gap-3 flex-1">
            <View className="w-10 h-10 rounded-xl bg-primary/10 items-center justify-center">
              <MaterialIcons name="analytics" size={22} color="#4e45e4" />
            </View>
            <View className="flex-1">
              <Text className="text-base font-bold text-on-surface" style={{ fontFamily: "Manrope_700Bold" }}>
                Token Usage & Costs
              </Text>
              <Text className="text-xs text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>
                Request-level timeline & token traceability
              </Text>
            </View>
          </View>
          <MaterialIcons name="chevron-right" size={22} color="#94a3b8" />
        </TouchableOpacity>

        {/* Profile Navigation Card */}
        <TouchableOpacity
          onPress={() => navigation.navigate("Profile")}
          className="bg-surface-container-low p-4 rounded-2xl border border-outline-variant/15 flex-row items-center justify-between active:opacity-80"
        >
          <View className="flex-row items-center gap-3 flex-1">
            <View className="w-10 h-10 rounded-xl bg-secondary/10 items-center justify-center">
              <MaterialIcons name="person" size={22} color="#6366f1" />
            </View>
            <View className="flex-1">
              <Text className="text-base font-bold text-on-surface" style={{ fontFamily: "Manrope_700Bold" }}>
                Profile & Connectors
              </Text>
              <Text className="text-xs text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>
                Manage account, preferences, and Google integrations
              </Text>
            </View>
          </View>
          <MaterialIcons name="chevron-right" size={22} color="#94a3b8" />
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}
