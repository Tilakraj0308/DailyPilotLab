import "./global.css";
import React, { useEffect } from "react";
import { View, ActivityIndicator, Text, ScrollView, Platform } from "react-native";
import { NavigationContainer, createNavigationContainerRef } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { useFonts } from "expo-font";
import * as SplashScreen from "expo-splash-screen";
import { Inter_400Regular, Inter_500Medium, Inter_600SemiBold } from "@expo-google-fonts/inter";
import { Manrope_400Regular, Manrope_600SemiBold, Manrope_700Bold, Manrope_800ExtraBold } from "@expo-google-fonts/manrope";

import { AuthProvider, useAuth } from "./src/context/AuthContext";
import LoginScreen from "./src/screens/LoginScreen";
import HomeScreen from "./src/screens/HomeScreen";
import ChatScreen from "./src/screens/ChatScreen";
import SettingsScreen from "./src/screens/SettingsScreen";
import ProfileScreen from "./src/screens/ProfileScreen";
import ToolAccessScreen from "./src/connectors/ToolAccessScreen";
import GmailConnectorScreen from "./src/connectors/GmailConnectorScreen";
import GlobalAlertUI from "./src/components/GlobalAlertUI";
import { supabase } from "./src/lib/supabase";
import * as Linking from "expo-linking";
import * as QueryParams from "expo-auth-session/build/QueryParams";

const Stack = createNativeStackNavigator();

/** Used to navigate after OAuth returns with ?connector_status= on web */
export const navigationRef = createNavigationContainerRef();

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
    if (incomingUrl && Platform.OS !== 'web') {
      // Connector OAuth return — not a Supabase session URL
      if (
        incomingUrl.includes("connectors/callback") ||
        incomingUrl.includes("connector_status=")
      ) {
        return;
      }
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

  // OAuth return on web: land on Profile so ConnectorsSection mounts and shows alerts
  useEffect(() => {
    if (!session || Platform.OS !== "web" || typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (!params.get("connector_status")) return;
    const id = requestAnimationFrame(() => {
      if (navigationRef.isReady()) {
        navigationRef.navigate("Profile" as never);
      }
    });
    return () => cancelAnimationFrame(id);
  }, [session]);

  // Native deep link: open Profile when OAuth appends connector_status to URL
  useEffect(() => {
    if (!session || !incomingUrl || Platform.OS === "web") return;
    if (incomingUrl.includes("connector_status=") && navigationRef.isReady()) {
      navigationRef.navigate("Profile" as never);
    }
  }, [incomingUrl, session]);

  if (!fontsLoaded || isLoading) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#f8f9fa" }}>
        <ActivityIndicator size="large" color="#4e45e4" />
      </View>
    );
  }

  return (
    <NavigationContainer ref={navigationRef}>
      {session ? (
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          <Stack.Screen name="Home" component={HomeScreen} />
          <Stack.Screen name="Chat" component={ChatScreen} />
          <Stack.Screen name="Profile" component={ProfileScreen} />
          <Stack.Screen name="Settings" component={SettingsScreen} />
          <Stack.Screen name="ToolAccess" component={ToolAccessScreen} />
          <Stack.Screen name="GmailConnector" component={GmailConnectorScreen} />
        </Stack.Navigator>
      ) : (
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          <Stack.Screen name="Login" component={LoginScreen} />
        </Stack.Navigator>
      )}
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <View style={{ flex: 1, backgroundColor: Platform.OS === 'web' ? '#e2e9ec' : 'transparent' }}>
          <View style={[
            { flex: 1 },
            Platform.OS === 'web' && {
              maxWidth: 480,
              width: '100%',
              marginHorizontal: 'auto',
              backgroundColor: '#f8f9fa',
              boxShadow: '0 25px 50px -12px rgb(0 0 0 / 0.25)',
              borderLeftWidth: 1,
              borderRightWidth: 1,
              borderColor: 'rgba(171, 179, 183, 0.2)',
              // Clip the sliding sidebar so it doesn't escape into the gray background
              overflow: 'hidden',
              position: 'relative',
            }
          ]}>
            <AppNavigator />
            <GlobalAlertUI />
          </View>
        </View>
      </AuthProvider>
    </ErrorBoundary>
  );
}

