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
          className="text-sm text-on-surface-variant mb-2"
          style={{ fontFamily: "Inter_400Regular" }}
        >
          App preferences will live here. Connect Google Calendar and other services from{" "}
          <Text style={{ fontFamily: "Inter_600SemiBold" }}>Profile</Text>.
        </Text>
        <TouchableOpacity
          onPress={() => navigation.navigate("Profile")}
          className="mt-4 bg-secondary py-3 px-4 rounded-xl flex-row items-center justify-center gap-2"
        >
          <MaterialIcons name="person" size={22} color="#ffffff" />
          <Text className="text-white text-base" style={{ fontFamily: "Inter_600SemiBold" }}>
            Open Profile
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}
