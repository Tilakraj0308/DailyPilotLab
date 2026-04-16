import React from "react";
import { View, Text, TouchableOpacity, ScrollView, Image } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { MaterialIcons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import { useAuth } from "../context/AuthContext";
import Animated, { FadeIn, FadeOut } from "react-native-reanimated";
import ConnectorsSection from "../connectors/ConnectorsSection";
import MainBottomNav from "../components/MainBottomNav";
import { universalAlert } from "../lib/alerts";

export default function ProfileScreen() {
  const navigation = useNavigation<any>();
  const { signOut, user } = useAuth();

  const displayName =
    user?.user_metadata?.full_name ||
    user?.user_metadata?.name ||
    user?.email?.split("@")[0] ||
    "Account";

  const handleSignOut = () => {
    universalAlert("Sign Out", "Are you sure you want to sign out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Sign Out",
        style: "destructive",
        onPress: async () => {
          await signOut();
        },
      },
    ]);
  };

  return (
    <SafeAreaView className="flex-1 bg-background">
      <View className="flex-row items-center px-5 py-4 border-b border-outline-variant/10 bg-background">
        <TouchableOpacity onPress={() => navigation.navigate("Home")} className="mr-3 p-1">
          <MaterialIcons name="arrow-back" size={24} color="#2b3437" />
        </TouchableOpacity>
        <Text
          className="text-lg font-bold text-on-surface flex-1"
          style={{ fontFamily: "Manrope_700Bold" }}
        >
          Profile
        </Text>
      </View>

      <ScrollView
        className="flex-1 px-5 pt-6"
        contentContainerStyle={{ paddingBottom: 120 }}
        showsVerticalScrollIndicator={false}
      >
        <View className="items-center mb-8">
          <Image
            source={{
              uri:
                user?.user_metadata?.avatar_url ||
                "https://i.pravatar.cc/150?u=a042581f4e29026704d",
            }}
            className="w-24 h-24 rounded-full border-2 border-outline-variant/20 mb-4"
          />
          <Text
            className="text-2xl text-on-surface text-center"
            style={{ fontFamily: "Manrope_700Bold" }}
          >
            {displayName}
          </Text>
          <Text
            className="text-sm text-on-surface-variant mt-1 text-center"
            style={{ fontFamily: "Inter_400Regular" }}
          >
            {user?.email ?? ""}
          </Text>
        </View>

        <View className="mb-8">
          <ConnectorsSection />
        </View>

        <Text
          className="text-[10px] uppercase text-on-surface-variant font-semibold tracking-widest mb-3"
          style={{ fontFamily: "Inter_600SemiBold" }}
        >
          Account
        </Text>
        <TouchableOpacity
          onPress={() => navigation.navigate("Settings")}
          className="bg-surface-container-lowest rounded-2xl p-4 border border-outline-variant/15 flex-row items-center justify-between mb-4 shadow-sm"
        >
          <View className="flex-row items-center gap-3">
            <View className="w-10 h-10 rounded-full bg-surface-container items-center justify-center">
              <MaterialIcons name="tune" size={22} color="#586064" />
            </View>
            <View>
              <Text
                className="text-base text-on-surface"
                style={{ fontFamily: "Inter_600SemiBold" }}
              >
                Settings
              </Text>
              <Text
                className="text-xs text-on-surface-variant"
                style={{ fontFamily: "Inter_400Regular" }}
              >
                App preferences
              </Text>
            </View>
          </View>
          <MaterialIcons name="chevron-right" size={24} color="#586064" />
        </TouchableOpacity>

        <TouchableOpacity
          onPress={handleSignOut}
          className="bg-surface-container-lowest rounded-2xl p-4 border border-red-200/60 flex-row items-center justify-center gap-2 mb-6"
        >
          <MaterialIcons name="logout" size={22} color="#ef4444" />
          <Text className="text-red-500 text-base" style={{ fontFamily: "Inter_600SemiBold" }}>
            Sign out
          </Text>
        </TouchableOpacity>
      </ScrollView>

      <MainBottomNav active="me" />
    </SafeAreaView>
  );
}
