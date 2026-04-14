import React from "react";
import { View, Text, TouchableOpacity } from "react-native";
import { MaterialIcons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";

export type BottomNavTab = "home" | "chat" | "me";

type TabKey = "home" | "tasks" | "chat" | "library" | "me";

type TabConfig = { key: TabKey; label: string; icon: keyof typeof MaterialIcons.glyphMap; navigable: boolean };

const TABS: TabConfig[] = [
  { key: "home", label: "Home", icon: "home", navigable: true },
  { key: "tasks", label: "Tasks", icon: "check-circle", navigable: false },
  { key: "chat", label: "Chat", icon: "chat-bubble", navigable: true },
  { key: "library", label: "Library", icon: "auto-stories", navigable: false },
  { key: "me", label: "Me", icon: "person", navigable: true },
];

type Props = {
  active: BottomNavTab;
};

/**
 * Shared bottom bar for Home and Profile so Me / Home stay consistent.
 */
export default function MainBottomNav({ active }: Props) {
  const navigation = useNavigation<any>();

  const isTabActive = (key: TabKey): boolean => {
    if (active === "home" && key === "home") return true;
    if (active === "chat" && key === "chat") return true;
    if (active === "me" && key === "me") return true;
    return false;
  };

  return (
    <View className="absolute bottom-0 w-full flex-row justify-between bg-surface-container-lowest px-2 py-2 pb-6 border-t border-outline-variant/10 px-5">
      {TABS.map((tab) => {
        const isActive = isTabActive(tab.key);
        const onPress = () => {
          if (tab.key === "home") navigation.navigate("Home");
          else if (tab.key === "chat") navigation.navigate("Chat");
          else if (tab.key === "me") navigation.navigate("Profile");
        };

        return (
          <TouchableOpacity
            key={tab.key}
            className="items-center justify-center flex-1"
            onPress={tab.navigable ? onPress : undefined}
            disabled={!tab.navigable}
          >
            <View className="px-4 py-1 rounded-xl mb-1">
              <MaterialIcons
                name={tab.icon as any}
                size={24}
                color={isActive ? "#4e45e4" : "#586064"}
              />
            </View>
            <Text
              className="text-[10px]"
              style={{
                fontFamily: "Inter_500Medium",
                color: isActive ? "#4e45e4" : "#586064",
              }}
            >
              {tab.label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}
