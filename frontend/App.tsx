import React, { useState, useCallback } from 'react';
import { StatusBar, StyleSheet, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { NavigationContainer } from '@react-navigation/native';
import {
  createDrawerNavigator,
  DrawerContentComponentProps,
} from '@react-navigation/drawer';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import {
  HomeScreen,
  DrawerContent,
  PersonalizeScreen,
  SettingsSheet,
  ChatScreen,
  SelectModelSheet,
  WebSearchSheet,
} from './src/screens';

const Drawer = createDrawerNavigator();

function CustomDrawerContent(
  props: DrawerContentComponentProps & {
    onOpenPersonalize: () => void;
    onOpenSettings: () => void;
  },
) {
  return (
    <DrawerContent
      onClose={() => props.navigation.closeDrawer()}
      onOpenPersonalize={() => {
        props.navigation.closeDrawer();
        setTimeout(() => props.onOpenPersonalize(), 300);
      }}
      onOpenSettings={() => {
        props.navigation.closeDrawer();
        setTimeout(() => props.onOpenSettings(), 300);
      }}
    />
  );
}

function HomeScreenWrapper({
  navigation,
  onOpenChat,
}: {
  navigation: any;
  onOpenChat: () => void;
}) {
  return (
    <HomeScreen
      onOpenDrawer={() => navigation.openDrawer()}
      onOpenChat={onOpenChat}
    />
  );
}

function App() {
  // Global sheet/modal state
  const [personalizeVisible, setPersonalizeVisible] = useState(false);
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [chatVisible, setChatVisible] = useState(false);
  const [modelPickerVisible, setModelPickerVisible] = useState(false);
  const [webSearchVisible, setWebSearchVisible] = useState(false);
  const [selectedModel, setSelectedModel] = useState('TwinMind Auto');

  const handleOpenPersonalize = useCallback(
    () => setPersonalizeVisible(true),
    [],
  );
  const handleOpenSettings = useCallback(() => setSettingsVisible(true), []);
  const handleOpenChat = useCallback(() => setChatVisible(true), []);

  const handleOpenModelSelect = useCallback(() => {
    setModelPickerVisible(true);
  }, []);

  const handleSelectModel = useCallback((model: string) => {
    setSelectedModel(model);
    setModelPickerVisible(false);
  }, []);

  return (
    <GestureHandlerRootView style={styles.root}>
      <SafeAreaProvider>
        <StatusBar
          barStyle="dark-content"
          backgroundColor="transparent"
          translucent
        />
        <NavigationContainer>
          <View style={styles.root}>
            <Drawer.Navigator
              screenOptions={{
                headerShown: false,
                drawerType: 'front',
                drawerStyle: {
                  width: '85%',
                },
                swipeEnabled: true,
              }}
              drawerContent={props => (
                <CustomDrawerContent
                  {...props}
                  onOpenPersonalize={handleOpenPersonalize}
                  onOpenSettings={handleOpenSettings}
                />
              )}>
              <Drawer.Screen name="Home">
                {props => (
                  <HomeScreenWrapper
                    navigation={props.navigation}
                    onOpenChat={handleOpenChat}
                  />
                )}
              </Drawer.Screen>
            </Drawer.Navigator>

            {/* Modals & Sheets */}
            <PersonalizeScreen
              visible={personalizeVisible}
              onClose={() => setPersonalizeVisible(false)}
            />

            <ChatScreen
              visible={chatVisible}
              onClose={() => setChatVisible(false)}
              onOpenModelSelect={handleOpenModelSelect}
            />

            {/* Overlay Sheets */}
            <SettingsSheet
              visible={settingsVisible}
              onClose={() => setSettingsVisible(false)}
              onOpenPersonalize={() => {
                setSettingsVisible(false);
                setTimeout(handleOpenPersonalize, 300);
              }}
            />

            <WebSearchSheet
              visible={webSearchVisible}
              onClose={() => setWebSearchVisible(false)}
            />

            <SelectModelSheet
              visible={modelPickerVisible}
              onClose={() => setModelPickerVisible(false)}
              onSelectModel={handleSelectModel}
            />
          </View>
        </NavigationContainer>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
});

export default App;
