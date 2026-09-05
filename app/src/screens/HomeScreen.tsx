import React, { useState, useRef, useEffect } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    Image,
    ScrollView
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { MaterialIcons, Feather } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import { useAuth } from "../context/AuthContext";
import SidebarDrawer from "../components/SidebarDrawer";

export default function HomeScreen() {
    const { user } = useAuth();
    const navigation = useNavigation<any>();
    const [drawerOpen, setDrawerOpen] = useState(false);

    const closeDrawer = () => setDrawerOpen(false);

    const openDrawer = () => setDrawerOpen(true);

    const getGreeting = () => {
        const hour = new Date().getHours();
        if (hour < 12) return "Good morning";
        if (hour < 18) return "Good afternoon";
        return "Good evening";
    };

    const getFormattedDate = () => {
        const date = new Date();
        return date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
    };

    return (
        <SafeAreaView className="flex-1 bg-[#f8f9fa]" edges={['top']}>
            {/* Top Navigation */}
            <View className="flex-row items-center justify-between px-5 py-4">
                <TouchableOpacity onPress={openDrawer}>
                    <MaterialIcons name="menu" size={28} color="#2b3437" />
                </TouchableOpacity>
                <Text
                    className="text-xl text-[#2b3437]"
                    style={{ fontFamily: "Inter_600SemiBold" }}
                >
                    Sanctuary
                </Text>
                <TouchableOpacity onPress={() => navigation.navigate("Profile")}>
                    <Image
                        source={{ uri: user?.user_metadata?.avatar_url || "https://i.pravatar.cc/150?img=11" }}
                        className="w-9 h-9 rounded-full bg-gray-300"
                    />
                </TouchableOpacity>
            </View>

            <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 100 }}>
                <View className="px-5 pt-4 pb-6">
                    {/* Greeting Section */}
                    <View className="mb-6">
                        <Text
                            className="text-[32px] text-[#2b3437] leading-tight"
                            style={{ fontFamily: "Inter_600SemiBold", letterSpacing: -0.5 }}
                        >
                            {getGreeting()}, {user?.user_metadata?.full_name?.split(' ')[0] || "Alex"}
                        </Text>
                        <Text
                            className="text-[#586064] text-base mt-1"
                            style={{ fontFamily: "Inter_400Regular" }}
                        >
                            {getFormattedDate()}
                        </Text>
                    </View>

                    {/* App Shortcuts */}
                    <View className="flex-row justify-between">
                        {/* Todos Button */}
                        <TouchableOpacity
                            className="bg-white rounded-[24px] p-5 w-[48%] shadow-sm"
                            onPress={() => { /* Redirect to Todo */ }}
                        >
                            <View className="w-10 h-10 rounded-full bg-[#f1f3f5] items-center justify-center mb-6">
                                <MaterialIcons name="list-alt" size={20} color="#2b3437" />
                            </View>
                            <Text
                                className="text-lg text-[#2b3437] mb-1"
                                style={{ fontFamily: "Inter_600SemiBold" }}
                            >
                                Todos
                            </Text>
                            <Text
                                className="text-[#586064] text-xs"
                                style={{ fontFamily: "Inter_400Regular" }}
                            >
                                3 items remaining
                            </Text>
                        </TouchableOpacity>

                        {/* Chat Button */}
                        <TouchableOpacity
                            className="bg-[#35436b] rounded-[24px] p-5 w-[48%] shadow-sm overflow-hidden"
                            onPress={() => navigation.navigate("Chat")}
                        >
                            <View className="absolute right-[-10px] top-[20px] opacity-20">
                                <MaterialIcons name="chat-bubble" size={70} color="#ffffff" />
                            </View>
                            <View className="w-10 h-10 rounded-full bg-white/20 items-center justify-center mb-6">
                                <MaterialIcons name="chat-bubble" size={20} color="#ffffff" />
                            </View>
                            <Text
                                className="text-lg text-white mb-1"
                                style={{ fontFamily: "Inter_600SemiBold" }}
                            >
                                Chat
                            </Text>
                            <Text
                                className="text-white/80 text-xs"
                                style={{ fontFamily: "Inter_400Regular" }}
                            >
                                Continue conversation
                            </Text>
                        </TouchableOpacity>
                    </View>
                </View>
            </ScrollView>

            {/* Custom Drawer Overlay */}
            <SidebarDrawer isOpen={drawerOpen} onClose={closeDrawer} width={300}>
                <SafeAreaView className="flex-1 bg-white h-full shadow-lg" edges={['top', 'bottom']}>
                    <View className="flex-1 px-6 pt-12">
                        {/* Profile Header */}
                        <View className="flex-row items-center justify-between mb-12">
                            <View className="flex-row items-center">
                                <Image
                                    source={{ uri: user?.user_metadata?.avatar_url || "https://i.pravatar.cc/150?img=11" }}
                                    className="w-12 h-12 rounded-full mr-3 border border-gray-100"
                                />
                                <View>
                                    <Text className="text-xl text-[#35436b]" style={{ fontFamily: "Inter_600SemiBold" }}>
                                        {user?.user_metadata?.full_name || "Alex Rivers"}
                                    </Text>
                                    <Text className="text-sm text-[#586064]" style={{ fontFamily: "Inter_400Regular" }}>
                                        Pro Member
                                    </Text>
                                </View>
                            </View>
                            <MaterialIcons name="keyboard-arrow-down" size={24} color="#586064" />
                        </View>

                        {/* Top Links */}
                        <View className="flex-1">
                            <TouchableOpacity
                                className="flex-row items-center mb-8"
                                onPress={() => { navigation.navigate('Connectors'); closeDrawer(); }}
                            >
                                <View className="w-6 items-center mr-4">
                                    <Feather name="share-2" size={22} color="#35436b" />
                                </View>
                                <Text className="text-base text-[#35436b]" style={{ fontFamily: "Inter_500Medium" }}>
                                    Connectors
                                </Text>
                            </TouchableOpacity>

                            <TouchableOpacity
                                className="flex-row items-center mb-8"
                                onPress={() => { navigation.navigate('Settings'); closeDrawer(); }}
                            >
                                <View className="w-6 items-center mr-4">
                                    <Feather name="settings" size={22} color="#35436b" />
                                </View>
                                <Text className="text-base text-[#35436b]" style={{ fontFamily: "Inter_500Medium" }}>
                                    Settings
                                </Text>
                            </TouchableOpacity>

                            <TouchableOpacity
                                className="flex-row items-center mb-8"
                                onPress={() => { /* Contact Support */ closeDrawer(); }}
                            >
                                <View className="w-6 items-center mr-4">
                                    <MaterialIcons name="support-agent" size={24} color="#35436b" />
                                </View>
                                <Text className="text-base text-[#35436b]" style={{ fontFamily: "Inter_500Medium" }}>
                                    Contact Support
                                </Text>
                            </TouchableOpacity>
                        </View>

                        {/* Bottom Links */}
                        <View className="mt-auto border-t border-gray-100 pt-6">
                            <TouchableOpacity
                                className="flex-row items-center mb-6"
                                onPress={() => { navigation.navigate('Profile'); closeDrawer(); }}
                            >
                                <View className="w-6 items-center mr-4">
                                    <Feather name="user" size={22} color="#35436b" />
                                </View>
                                <Text className="text-base text-[#35436b]" style={{ fontFamily: "Inter_500Medium" }}>
                                    Profile
                                </Text>
                            </TouchableOpacity>

                            <TouchableOpacity
                                className="flex-row items-center mb-4"
                                onPress={() => { /* Pricing */ closeDrawer(); }}
                            >
                                <View className="w-6 items-center mr-4">
                                    <MaterialIcons name="payments" size={22} color="#35436b" />
                                </View>
                                <Text className="text-base text-[#35436b]" style={{ fontFamily: "Inter_500Medium" }}>
                                    Pricing
                                </Text>
                            </TouchableOpacity>
                        </View>
                    </View>
                </SafeAreaView>
            </SidebarDrawer>
        </SafeAreaView>
    );
}
