import React, { useEffect, useState } from "react";
import { View, Text, TouchableOpacity, Image, SafeAreaView, ActivityIndicator } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { MaterialIcons } from "@expo/vector-icons";
import * as WebBrowser from "expo-web-browser";
import * as Google from "expo-auth-session/providers/google";
import AsyncStorage from "@react-native-async-storage/async-storage";

WebBrowser.maybeCompleteAuthSession();

export default function LoginScreen() {
    const navigation = useNavigation<any>();
    const [isVerifying, setIsVerifying] = useState(false);

    const [request, response, promptAsync] = Google.useAuthRequest({
        webClientId: process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID,
        androidClientId: process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID,
    });

    useEffect(() => {
        if (response?.type === "success" && response.authentication?.idToken) {
            handleBackendSignIn(response.authentication.idToken);
        }
    }, [response]);

    const handleBackendSignIn = async (idToken: string) => {
        setIsVerifying(true);
        try {
            const res = await fetch(`${process.env.EXPO_PUBLIC_API_URL}/auth/google`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id_token: idToken }),
            });

            if (!res.ok) throw new Error("Backend authentication failed");

            const data = await res.json();
            if (data.access_token) {
                await AsyncStorage.setItem("jwt_token", data.access_token);
                await AsyncStorage.setItem("user_info", JSON.stringify(data.user));
                navigation.replace("Home");
            }
        } catch (e) {
            console.error(e);
            alert("Failed to authenticate with backend.");
        } finally {
            setIsVerifying(false);
        }
    };

    return (
        <SafeAreaView className="flex-1 bg-background justify-between items-center px-8 py-12">
            {/* Brand Header */}
            <View className="w-full flex items-center mb-8 mt-12">
                <View className="flex-col items-center gap-2">
                    <View className="w-16 h-16 rounded-xl bg-surface-container-lowest flex items-center justify-center border border-outline-variant/10 shadow-sm">
                        <MaterialIcons name="auto-awesome" size={36} color="#4e45e4" />
                    </View>
                    <Text
                        className="text-3xl tracking-tight text-on-surface"
                        style={{ fontFamily: "Manrope_800ExtraBold" }}
                    >
                        DailyPilot
                    </Text>
                </View>
            </View>

            {/* Main Content Canvas */}
            <View className="w-full max-w-sm flex-1 flex-col justify-center items-center">
                {/* Illustration/Assistant Visual */}
                <View className="relative mb-12 items-center justify-center">
                    <View
                        className="absolute -z-10 w-40 h-40 bg-secondary-container/30 rounded-full"
                    />
                    <View className="bg-surface-container-lowest p-6 rounded-2xl border border-outline-variant/10 text-center relative flex items-center shadow-sm w-64">
                        <View
                            className="absolute -top-3 -right-3 bg-secondary px-3 py-1 rounded-full"
                        >
                            <Text className="text-[10px] font-bold text-on-secondary tracking-widest uppercase">
                                AI Active
                            </Text>
                        </View>

                        <MaterialIcons name="smart-toy" size={48} color="#4135d8" className="mb-4" />
                        <Text
                            className="mt-4 text-on-surface-variant text-sm leading-relaxed text-center"
                            style={{ fontFamily: "Inter_400Regular" }}
                        >
                            "Your day, intelligently curated. Ready to navigate?"
                        </Text>
                    </View>
                </View>

                {/* Auth Actions */}
                <View className="w-full space-y-4 gap-4">
                    {/* Google Auth */}
                    <TouchableOpacity
                        className="w-full bg-surface-container-lowest py-4 px-6 rounded-lg border border-outline-variant/20 flex-row items-center justify-center gap-3"
                        onPress={() => promptAsync()}
                        disabled={!request || isVerifying}
                    >
                        {isVerifying ? (
                            <ActivityIndicator color="#4e45e4" size="small" />
                        ) : (
                            <Image
                                source={{ uri: "https://lh3.googleusercontent.com/aida-public/AB6AXuBzrcEO4WmlwRT96EDgA7nExM-mxDDhqJrZGeme_RlGVj7gHZNYqQVgAvmtw1Uayhs_QnMOlDQXi9pPozsXuSdQ8q4H3J9in019jIXNcHh-JYzdyeMnohkekaTYanbvrdgHrkIepfASbB7tVTxqroGUb-GiURJJSe-Zoso7GJ6CxbriLegRMaXtRlFl7EpXfdZ0d1H1YoNGJBFpcxKh0n5p4QsqWwbHiwWws_ASgdInDJJcxMtb-dPzhxK6xzoDWd1l2wVic5Eon9sT" }}
                                className="w-5 h-5"
                            />
                        )}
                        <Text
                            className="text-on-surface text-base"
                            style={{ fontFamily: "Inter_600SemiBold" }}
                        >
                            {isVerifying ? "Verifying..." : "Continue with Google"}
                        </Text>
                    </TouchableOpacity>

                    {/* GitHub Auth - Currently Mocks transition to Home */}
                    <TouchableOpacity
                        className="w-full bg-[#24292e] py-4 px-6 rounded-lg flex-row items-center justify-center gap-3"
                        onPress={() => navigation.navigate("Home")}
                    >
                        <MaterialIcons name="code" size={24} color="#ffffff" />
                        <Text
                            className="text-white text-base"
                            style={{ fontFamily: "Inter_600SemiBold" }}
                        >
                            Continue with GitHub
                        </Text>
                    </TouchableOpacity>
                </View>

                <View className="mt-8 flex-col items-center gap-4">
                    <View className="flex-row items-center gap-2">
                        <Text
                            className="text-on-surface-variant text-sm"
                            style={{ fontFamily: "Inter_500Medium" }}
                        >
                            New to DailyPilot?
                        </Text>
                        <TouchableOpacity>
                            <Text
                                className="text-secondary"
                                style={{ fontFamily: "Inter_600SemiBold", textDecorationLine: "underline" }}
                            >
                                Create account
                            </Text>
                        </TouchableOpacity>
                    </View>
                    <TouchableOpacity className="mt-4">
                        <Text
                            className="text-on-surface-variant/60 text-xs"
                            style={{ fontFamily: "Inter_500Medium" }}
                        >
                            Trouble signing in?
                        </Text>
                    </TouchableOpacity>
                </View>
            </View>

            {/* Simple Footer / Terms */}
            <View className="w-full pt-8 items-center border-t border-outline-variant/10">
                <Text
                    className="text-[10px] text-on-surface-variant/50 px-6 text-center"
                    style={{ fontFamily: "Inter_400Regular" }}
                >
                    By continuing, you agree to DailyPilot's{" "}
                    <Text style={{ textDecorationLine: "underline" }}>Terms of Service</Text> and{" "}
                    <Text style={{ textDecorationLine: "underline" }}>Privacy Policy</Text>.
                </Text>
            </View>
        </SafeAreaView>
    );
}
