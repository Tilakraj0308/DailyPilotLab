import React, { useState } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    Image,
    SafeAreaView,
    ScrollView,
    TextInput,
    KeyboardAvoidingView,
    Platform,
} from "react-native";
import { MaterialIcons } from "@expo/vector-icons";

export default function HomeScreen() {
    const [chatInput, setChatInput] = useState("");

    const getGreeting = () => {
        const hour = new Date().getHours();
        if (hour < 12) return "Good morning";
        if (hour < 18) return "Good afternoon";
        return "Good evening";
    };

    return (
        <SafeAreaView className="flex-1 bg-background">
            {/* 1. Top App Bar (Fixed) */}
            <View className="flex-row items-center justify-between px-5 py-4 border-b border-outline-variant/10 bg-background z-10">
                <TouchableOpacity>
                    <MaterialIcons name="menu" size={28} color="#2b3437" />
                </TouchableOpacity>
                <Text
                    className="text-lg font-bold text-on-surface"
                    style={{ fontFamily: "Manrope_700Bold" }}
                >
                    DailyPilot
                </Text>
                <TouchableOpacity>
                    <Image
                        source={{ uri: "https://i.pravatar.cc/150?u=a042581f4e29026704d" }}
                        className="w-9 h-9 rounded-full border border-outline-variant/20"
                    />
                </TouchableOpacity>
            </View>

            {/* Main Scrollable Content */}
            <ScrollView
                showsVerticalScrollIndicator={false}
                contentContainerStyle={{ paddingBottom: 100 }}
            >
                <View className="px-5 pt-6 pb-6">
                    {/* 2. Greeting Section */}
                    <View className="mb-6">
                        <Text
                            className="text-sm text-on-surface-variant mb-1"
                            style={{ fontFamily: "Inter_400Regular" }}
                        >
                            Tuesday, Oct 24
                        </Text>
                        <Text
                            className="text-4xl text-on-surface"
                            style={{ fontFamily: "Manrope_800ExtraBold" }}
                        >
                            {getGreeting()}, Alex
                        </Text>
                    </View>

                    {/* 3. Active Memory Card */}
                    <View className="bg-surface-container-lowest rounded-2xl p-5 border border-outline-variant/15 shadow-sm mb-6">
                        <View className="flex-row justify-between items-center mb-3">
                            <Text
                                className="text-[10px] uppercase text-on-surface-variant font-semibold tracking-widest"
                                style={{ fontFamily: "Inter_600SemiBold" }}
                            >
                                ACTIVE MEMORY
                            </Text>
                            <View className="relative w-2.5 h-2.5">
                                <View
                                    className="absolute inset-0 bg-secondary rounded-full opacity-50"
                                />
                                <View className="absolute inset-0 bg-secondary rounded-full w-2.5 h-2.5" />
                            </View>
                        </View>
                        <Text
                            className="text-base text-on-surface mb-4 leading-snug"
                            style={{ fontFamily: "Inter_500Medium" }}
                        >
                            Preparing for the 'Apollo Project' presentation tomorrow at 10 AM.
                        </Text>
                        <View className="self-start bg-surface-container px-3 py-1 rounded-full">
                            <Text
                                className="text-xs text-on-surface-variant"
                                style={{ fontFamily: "Inter_500Medium" }}
                            >
                                Key Focus: Slides 4–7
                            </Text>
                        </View>
                    </View>

                    {/* 4. Insight + Time Gap Row */}
                    <View className="flex-row flex-wrap justify-between mb-6">
                        {/* Left Card */}
                        <View className="bg-surface-container-lowest rounded-2xl p-4 border border-outline-variant/15 shadow-sm w-[48%]">
                            <View className="w-8 h-8 rounded-full bg-secondary-container items-center justify-center mb-3">
                                <MaterialIcons name="lightbulb" size={18} color="#4e45e4" />
                            </View>
                            <Text
                                className="text-[10px] uppercase text-on-surface-variant tracking-wider mb-1"
                                style={{ fontFamily: "Inter_600SemiBold" }}
                            >
                                NEW INSIGHT
                            </Text>
                            <Text
                                className="text-sm text-on-surface leading-tight"
                                style={{ fontFamily: "Inter_600SemiBold" }}
                            >
                                Caffeine peaks 45m after intake.
                            </Text>
                        </View>

                        {/* Right Card */}
                        <View className="bg-surface-container-lowest rounded-2xl p-4 border border-outline-variant/15 shadow-sm w-[48%]">
                            <View className="w-8 h-8 rounded-full bg-secondary-container items-center justify-center mb-3">
                                <MaterialIcons name="schedule" size={18} color="#4e45e4" />
                            </View>
                            <Text
                                className="text-[10px] uppercase text-on-surface-variant tracking-wider mb-1"
                                style={{ fontFamily: "Inter_600SemiBold" }}
                            >
                                TIME GAP
                            </Text>
                            <Text
                                className="text-sm text-on-surface leading-tight"
                                style={{ fontFamily: "Inter_600SemiBold" }}
                            >
                                2h focus block available now.
                            </Text>
                        </View>
                    </View>

                    {/* 5. Recent Memories Row */}
                    <View className="mb-6">
                        <View className="flex-row justify-between items-center mb-3">
                            <Text
                                className="text-base text-on-surface"
                                style={{ fontFamily: "Inter_600SemiBold" }}
                            >
                                Recent Memories
                            </Text>
                            <TouchableOpacity>
                                <Text
                                    className="text-sm text-secondary"
                                    style={{ fontFamily: "Inter_500Medium" }}
                                >
                                    Search all
                                </Text>
                            </TouchableOpacity>
                        </View>
                        <ScrollView
                            horizontal
                            showsHorizontalScrollIndicator={false}
                            className="flex-row gap-2"
                            contentContainerStyle={{ paddingBottom: 4 }}
                        >
                            {[
                                { title: "Project Apollo Strate...", icon: "history" },
                                { title: "Grocery list for toni...", icon: "history" },
                                { title: "Gym workout Oct 23...", icon: "history" },
                            ].map((item, idx) => (
                                <View
                                    key={idx}
                                    className="bg-surface-container rounded-xl px-3 py-2.5 flex-row items-center gap-2 mr-2"
                                >
                                    <MaterialIcons name={item.icon as any} size={14} color="#586064" />
                                    <Text
                                        className="text-xs text-on-surface"
                                        style={{ fontFamily: "Inter_500Medium" }}
                                    >
                                        {item.title}
                                    </Text>
                                </View>
                            ))}
                        </ScrollView>
                    </View>

                    {/* 6. AI Chat Thread */}
                    <View className="flex-col gap-6 w-full">
                        {/* AI Bubble */}
                        <View className="w-full">
                            <View className="flex-row gap-2 items-end">
                                <View className="w-9 h-9 rounded-full bg-secondary-container items-center justify-center -mb-2">
                                    <MaterialIcons name="smart-toy" size={20} color="#4e45e4" />
                                </View>
                                <View className="bg-surface-container p-4 rounded-2xl rounded-bl-sm max-w-[80%]">
                                    <Text
                                        className="text-sm text-on-surface leading-relaxed"
                                        style={{ fontFamily: "Inter_400Regular" }}
                                    >
                                        I've organized your notes for tomorrow's presentation. Want me to draft an outline for the first 3 slides?
                                    </Text>
                                </View>
                            </View>
                            <Text
                                className="text-[11px] text-on-surface-variant/60 ml-12 mt-1"
                                style={{ fontFamily: "Inter_400Regular" }}
                            >
                                DailyPilot • 18:42
                            </Text>
                        </View>

                        {/* User Bubble */}
                        <View className="w-full flex-col items-end">
                            <View className="flex-row-reverse gap-2 items-end">
                                <View className="w-9 h-9 rounded-full bg-surface-container items-center justify-center -mb-2">
                                    <MaterialIcons name="person" size={20} color="#586064" />
                                </View>
                                <View className="bg-secondary p-4 rounded-2xl rounded-br-sm max-w-[80%]">
                                    <Text
                                        className="text-sm text-white"
                                        style={{ fontFamily: "Inter_500Medium" }}
                                    >
                                        Yes please, focus on the Q3 metrics first.
                                    </Text>
                                </View>
                            </View>
                            <Text
                                className="text-[11px] text-on-surface-variant/60 mr-12 mt-1"
                                style={{ fontFamily: "Inter_400Regular" }}
                            >
                                You • 18:43
                            </Text>
                        </View>

                        {/* AI Typing State */}
                        <View className="w-full">
                            <View className="flex-row gap-2 items-end">
                                <View className="w-9 h-9 rounded-full bg-secondary-container items-center justify-center -mb-2 relative">
                                    <View
                                        className="absolute inset-0 bg-secondary/40 rounded-full"
                                    />
                                    <MaterialIcons name="smart-toy" size={20} color="#4e45e4" />
                                </View>
                                <View className="p-2 justify-center pb-3">
                                    <Text
                                        className="text-sm text-on-surface-variant italic"
                                        style={{ fontFamily: "Inter_400Regular" }}
                                    >
                                        Drafting outline focusing on Q3...
                                    </Text>
                                </View>
                            </View>
                        </View>
                    </View>
                </View>
            </ScrollView>

            {/* 7. Chat Input Bar */}
            <KeyboardAvoidingView
                behavior={Platform.OS === "ios" ? "padding" : "height"}
                className="bg-surface border-t border-outline-variant/10 px-4 py-3 pb-8"
            >
                <View className="flex-row items-center gap-3">
                    <TextInput
                        className="flex-1 rounded-full bg-surface-container px-4 py-3 text-sm text-on-surface"
                        placeholder="Ask DailyPilot anything..."
                        placeholderTextColor="#586064"
                        value={chatInput}
                        onChangeText={setChatInput}
                        style={{ fontFamily: "Inter_400Regular" }}
                    />
                    <TouchableOpacity
                        className={`w-12 h-12 rounded-full items-center justify-center ${chatInput.trim() ? "bg-secondary" : "bg-outline-variant/30"
                            }`}
                        disabled={!chatInput.trim()}
                    >
                        <MaterialIcons
                            name="arrow-upward"
                            size={24}
                            color={chatInput.trim() ? "#ffffff" : "#f8f9fa"}
                        />
                    </TouchableOpacity>
                </View>
            </KeyboardAvoidingView>

            {/* 8. Fixed Bottom Nav Bar (Visual only inside HomeScreen for demo) */}
            <View className="absolute bottom-0 w-full flex-row justify-between bg-surface-container-lowest px-2 py-2 pb-6 border-t border-outline-variant/10 px-5">
                {[
                    { label: "Home", icon: "home", active: true },
                    { label: "Tasks", icon: "check-circle", active: false },
                    { label: "Updates", icon: "calendar-view-month", active: false },
                    { label: "Library", icon: "auto-stories", active: false },
                    { label: "Me", icon: "person", active: false },
                ].map((tab, idx) => (
                    <TouchableOpacity key={idx} className="items-center justify-center flex-1">
                        <View
                            className={`px-4 py-1 rounded-xl mb-1 ${tab.active ? "opacity-100" : "opacity-100"
                                }`}
                        >
                            <MaterialIcons
                                name={tab.icon as any}
                                size={24}
                                color={tab.active ? "#4e45e4" : "#586064"}
                            />
                        </View>
                        <Text
                            className="text-[10px]"
                            style={{
                                fontFamily: "Inter_500Medium",
                                color: tab.active ? "#4e45e4" : "#586064",
                            }}
                        >
                            {tab.label}
                        </Text>
                    </TouchableOpacity>
                ))}
            </View>
        </SafeAreaView>
    );
}
