import "./global.css";
import React, { useEffect } from "react";
import { View, ActivityIndicator, Text, ScrollView } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { useFonts } from "expo-font";
import * as SplashScreen from "expo-splash-screen";
import { Inter_400Regular, Inter_500Medium, Inter_600SemiBold } from "@expo-google-fonts/inter";
import { Manrope_400Regular, Manrope_600SemiBold, Manrope_700Bold, Manrope_800ExtraBold } from "@expo-google-fonts/manrope";

import { AuthProvider, useAuth } from "./src/context/AuthContext";
import LoginScreen from "./src/screens/LoginScreen";
import HomeScreen from "./src/screens/HomeScreen";
import ChatScreen from "./src/screens/ChatScreen";
import { supabase } from "./src/lib/supabase";
import * as Linking from "expo-linking";
import * as QueryParams from "expo-auth-session/build/QueryParams";

const Stack = createNativeStackNavigator();

// Keep splash screen visible while we load fonts and auth state
SplashScreen.preventAutoHideAsync();

// Error Boundary to catch and display runtime crashes
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("🔴 ErrorBoundary caught:", error.message, info.componentStack);
  }
  render() {
    if (this.state.hasError) {
      SplashScreen.hideAsync();
      return (
        <View style={{ flex: 1, backgroundColor: "#1a1a2e", padding: 20, justifyContent: "center" }}>
          <Text style={{ color: "#ff6b6b", fontSize: 20, fontWeight: "bold", marginBottom: 12 }}>
            App Crashed
          </Text>
          <ScrollView style={{ backgroundColor: "#16213e", borderRadius: 8, padding: 12, maxHeight: 400 }}>
            <Text style={{ color: "#e2e8f0", fontSize: 13, fontFamily: "monospace" }}>
              {this.state.error?.message}
            </Text>
            <Text style={{ color: "#94a3b8", fontSize: 11, fontFamily: "monospace", marginTop: 8 }}>
              {this.state.error?.stack}
            </Text>
          </ScrollView>
        </View>
      );
    }
    return this.props.children;
  }
}

function AppNavigator() {
  const { session, isLoading } = useAuth();
  const incomingUrl = Linking.useURL();

  // Root-level listener specifically meant to catch deep links that WebBrowser drops.
  useEffect(() => {
    if (incomingUrl) {
      const { params, errorCode } = QueryParams.getQueryParams(incomingUrl);
      if (params?.access_token && params?.refresh_token) {
        supabase.auth.setSession({
          access_token: params.access_token,
          refresh_token: params.refresh_token,
        });
      } else if (params?.code) {
        supabase.auth.exchangeCodeForSession(params.code);
      }
    }
  }, [incomingUrl]);

  const [fontsLoaded, fontError] = useFonts({
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Manrope_400Regular,
    Manrope_600SemiBold,
    Manrope_700Bold,
    Manrope_800ExtraBold,
  });

  useEffect(() => {
    if ((fontsLoaded || fontError) && !isLoading) {
      SplashScreen.hideAsync();
    }
  }, [fontsLoaded, fontError, isLoading]);

  if (!fontsLoaded || isLoading) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#f8f9fa" }}>
        <ActivityIndicator size="large" color="#4e45e4" />
      </View>
    );
  }

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {session ? (
          <>
            <Stack.Screen name="Home" component={HomeScreen} />
            <Stack.Screen name="Chat" component={ChatScreen} />
          </>
        ) : (
          <Stack.Screen name="Login" component={LoginScreen} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AppNavigator />
      </AuthProvider>
    </ErrorBoundary>
  );
}

