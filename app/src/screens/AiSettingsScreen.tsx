import React, { useState, useEffect } from "react";
import { View, Text, TouchableOpacity, ScrollView, TextInput, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { MaterialIcons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import { useAuth } from "../context/AuthContext";
import { universalAlert } from "../lib/alerts";
import { getApiUrl } from "../lib/api";

export default function AiSettingsScreen() {
  const navigation = useNavigation<any>();
  const { session } = useAuth();
  const apiUrl = getApiUrl();

  const [provider, setProvider] = useState("openai");
  const [model, setModel] = useState("gpt-4o-mini");
  const [apiKey, setApiKey] = useState("");
  
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [hasExistingKey, setHasExistingKey] = useState(false);

  // Flow State
  const [viewMode, setViewMode] = useState<'view' | 'setup'>('view');
  const [wizardStep, setWizardStep] = useState<1 | 2 | 3>(1);

  const openAiModels = [
    { label: "GPT-4o Mini", value: "gpt-4o-mini" },
    { label: "GPT-4o", value: "gpt-4o" },
    { label: "GPT-4", value: "gpt-4" },
    { label: "GPT-5", value: "gpt-5" },
  ];

  const openRouterModels = [
    { label: "Llama 3.1 70B", value: "meta-llama/llama-3.1-70b-instruct" },
    { label: "Claude 3.5 Sonnet", value: "anthropic/claude-3.5-sonnet" },
    { label: "Google Gemini Flash", value: "google/gemini-1.5-flash" },
    {label: "z-ai glm", value: "z-ai/glm-5.3-flash"}
  ];

  const models = provider === "openrouter" ? openRouterModels : openAiModels;

  const providers = [
    { label: "OpenAI", value: "openai" },
    { label: "OpenRouter", value: "openrouter" }
  ];

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    if (!session?.access_token || !apiUrl) return;
    setLoading(true);
    try {
      const response = await fetch(`${apiUrl}/settings/ai-settings`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });
      const data = await response.json();
      if (data && data.ai_provider) {
        setProvider(data.ai_provider);
        setModel(data.ai_model || (data.ai_provider === 'openrouter' ? "meta-llama/llama-3.1-70b-instruct" : "gpt-4o-mini"));
        setHasExistingKey(data.has_api_key);
        if (data.has_api_key) {
          setViewMode('view');
        } else {
          setViewMode('setup');
          setWizardStep(1);
        }
      } else {
        setViewMode('setup');
        setWizardStep(1);
      }
    } catch (error) {
      console.log("Error fetching AI settings", error);
      setViewMode('setup');
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    if (!apiKey && !hasExistingKey) {
      universalAlert("Error", "Please enter an API key.");
      return;
    }
    if (!session?.access_token || !apiUrl) return;
    
    setSaving(true);
    try {
      const response = await fetch(`${apiUrl}/settings/ai-settings`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          ai_provider: provider,
          ai_model: model,
          api_key: apiKey
        })
      });
      
      if (!response.ok) {
        throw new Error("Failed to save settings");
      }
      
      universalAlert("Success", "AI Settings saved successfully.");
      setHasExistingKey(true);
      setApiKey(""); // Clear the input field for security
      setViewMode('view');
    } catch (error) {
      console.error(error);
      universalAlert("Error", "Failed to save settings.");
    } finally {
      setSaving(false);
    }
  };

  const deleteSettings = async () => {
    universalAlert("Remove API Key", "Are you sure you want to remove your API key?", [
      { text: "Cancel", style: "cancel" },
      { 
        text: "Remove", 
        style: "destructive", 
        onPress: async () => {
          if (!session?.access_token || !apiUrl) return;
          setSaving(true);
          try {
            const response = await fetch(`${apiUrl}/settings/ai-settings`, {
              method: "DELETE",
              headers: {
                Authorization: `Bearer ${session.access_token}`,
              }
            });
            if (!response.ok) throw new Error("Delete failed");
            
            setHasExistingKey(false);
            setProvider("openai");
            setModel("gpt-4o-mini");
            setApiKey("");
            setViewMode('setup');
            setWizardStep(1);
            universalAlert("Success", "API Key removed. Falling back to default settings.");
          } catch (e) {
            console.error(e);
            universalAlert("Error", "Failed to remove API key.");
          } finally {
            setSaving(false);
          }
        } 
      }
    ]);
  };

  const renderViewMode = () => (
    <View className="flex-1">
      <View className="bg-surface-container-low rounded-2xl p-5 border border-outline-variant/15 mb-6 shadow-sm">
        <View className="flex-row items-center mb-4 pb-4 border-b border-outline-variant/10">
          <View className="w-12 h-12 rounded-xl bg-primary/10 items-center justify-center mr-4">
            <MaterialIcons name="memory" size={26} color="#4e45e4" />
          </View>
          <View>
            <Text className="text-sm text-on-surface-variant font-medium" style={{ fontFamily: "Inter_500Medium" }}>
              Active Configuration
            </Text>
            <Text className="text-lg text-on-surface font-bold mt-1" style={{ fontFamily: "Manrope_700Bold" }}>
              Custom API Key
            </Text>
          </View>
        </View>

        <View className="flex-row justify-between mb-4">
          <Text className="text-sm text-on-surface-variant" style={{ fontFamily: "Inter_500Medium" }}>Provider</Text>
          <Text className="text-sm text-on-surface font-bold capitalize" style={{ fontFamily: "Inter_600SemiBold" }}>
            {provider}
          </Text>
        </View>

        <View className="flex-row justify-between">
          <Text className="text-sm text-on-surface-variant" style={{ fontFamily: "Inter_500Medium" }}>Model</Text>
          <Text className="text-sm text-on-surface font-bold" style={{ fontFamily: "Inter_600SemiBold" }}>
            {models.find(m => m.value === model)?.label || model}
          </Text>
        </View>
      </View>

      <TouchableOpacity
        onPress={() => {
          setViewMode('setup');
          setWizardStep(1);
        }}
        className="bg-primary py-4 rounded-xl items-center justify-center mb-4 flex-row"
      >
        <MaterialIcons name="edit" size={20} color="white" style={{ marginRight: 8 }} />
        <Text className="text-white font-bold text-base" style={{ fontFamily: "Manrope_700Bold" }}>
          Update Configuration
        </Text>
      </TouchableOpacity>

      <TouchableOpacity
        onPress={deleteSettings}
        disabled={saving}
        className="bg-surface-container py-4 rounded-xl items-center justify-center flex-row border border-red-500/20"
      >
        {saving ? (
          <ActivityIndicator color="#ef4444" />
        ) : (
          <>
            <MaterialIcons name="delete-outline" size={20} color="#ef4444" style={{ marginRight: 8 }} />
            <Text className="text-red-500 font-bold text-base" style={{ fontFamily: "Manrope_700Bold" }}>
              Remove Key
            </Text>
          </>
        )}
      </TouchableOpacity>
    </View>
  );

  const renderSetupWizard = () => (
    <View className="flex-1">
      {/* Wizard Progress Indicators */}
      <View className="flex-row items-center justify-center mb-8 px-4">
        <View className={`w-8 h-8 rounded-full items-center justify-center ${wizardStep >= 1 ? 'bg-primary' : 'bg-surface-container border border-outline-variant/30'}`}>
          <Text className={`font-bold ${wizardStep >= 1 ? 'text-white' : 'text-on-surface-variant'}`}>1</Text>
        </View>
        <View className={`h-1 flex-1 mx-2 ${wizardStep >= 2 ? 'bg-primary' : 'bg-surface-container'}`} />
        <View className={`w-8 h-8 rounded-full items-center justify-center ${wizardStep >= 2 ? 'bg-primary' : 'bg-surface-container border border-outline-variant/30'}`}>
          <Text className={`font-bold ${wizardStep >= 2 ? 'text-white' : 'text-on-surface-variant'}`}>2</Text>
        </View>
        <View className={`h-1 flex-1 mx-2 ${wizardStep >= 3 ? 'bg-primary' : 'bg-surface-container'}`} />
        <View className={`w-8 h-8 rounded-full items-center justify-center ${wizardStep >= 3 ? 'bg-primary' : 'bg-surface-container border border-outline-variant/30'}`}>
          <Text className={`font-bold ${wizardStep >= 3 ? 'text-white' : 'text-on-surface-variant'}`}>3</Text>
        </View>
      </View>

      {/* Step 1: Provider */}
      {wizardStep === 1 && (
        <View className="flex-1 min-h-[300px]">
          <Text className="text-xl font-bold text-on-surface mb-2" style={{ fontFamily: "Manrope_700Bold" }}>
            Select Provider
          </Text>
          <Text className="text-sm text-on-surface-variant mb-6" style={{ fontFamily: "Inter_400Regular" }}>
            Choose the AI platform you want to connect.
          </Text>
          
          {providers.map((p) => (
            <TouchableOpacity
              key={p.value}
              onPress={() => {
                setProvider(p.value);
                if (p.value === "openrouter") setModel("meta-llama/llama-3.1-70b-instruct");
                else setModel("gpt-4o-mini");
              }}
              className={`p-4 rounded-xl border flex-row items-center justify-between mb-4 ${
                provider === p.value ? 'bg-primary/10 border-primary' : 'bg-surface-container-low border-outline-variant/20'
              }`}
            >
              <Text className={`text-base font-bold ${provider === p.value ? 'text-primary' : 'text-on-surface'}`}>{p.label}</Text>
              {provider === p.value && <MaterialIcons name="check-circle" size={24} color="#4e45e4" />}
            </TouchableOpacity>
          ))}

          <View className="flex-1 justify-end mt-8">
            <TouchableOpacity
              onPress={() => setWizardStep(2)}
              className="bg-primary py-4 rounded-xl items-center justify-center"
            >
              <Text className="text-white font-bold text-base" style={{ fontFamily: "Manrope_700Bold" }}>Continue</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* Step 2: API Key */}
      {wizardStep === 2 && (
        <View className="flex-1 min-h-[300px]">
          <Text className="text-xl font-bold text-on-surface mb-2" style={{ fontFamily: "Manrope_700Bold" }}>
            Enter API Key
          </Text>
          <Text className="text-sm text-on-surface-variant mb-6" style={{ fontFamily: "Inter_400Regular" }}>
            Your key will be securely encrypted via AWS KMS before being stored in the database.
          </Text>
          
          <TextInput
            className="bg-surface-container-low border border-outline-variant/30 rounded-xl px-4 py-4 text-on-surface text-base mb-2"
            placeholder={hasExistingKey ? "•••••••••••••••••••• (Leave blank to keep saved)" : "sk-..."}
            placeholderTextColor="#9ca3af"
            secureTextEntry={true}
            value={apiKey}
            onChangeText={setApiKey}
            autoCapitalize="none"
            autoCorrect={false}
            style={{ fontFamily: "Inter_500Medium" }}
          />
          
          <View className="flex-1 justify-end mt-8 flex-row items-end">
            <TouchableOpacity
              onPress={() => setWizardStep(1)}
              className="bg-surface-container py-4 rounded-xl items-center justify-center mr-3 px-6"
            >
              <MaterialIcons name="arrow-back" size={20} color="#94a3b8" />
            </TouchableOpacity>
            
            <TouchableOpacity
              onPress={() => {
                if (!apiKey && !hasExistingKey) {
                  universalAlert("Required", "Please provide an API key to continue.");
                  return;
                }
                setWizardStep(3);
              }}
              className="bg-primary py-4 rounded-xl items-center justify-center flex-1"
            >
              <Text className="text-white font-bold text-base" style={{ fontFamily: "Manrope_700Bold" }}>Continue</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* Step 3: Model */}
      {wizardStep === 3 && (
        <View className="flex-1 min-h-[300px]">
          <Text className="text-xl font-bold text-on-surface mb-2" style={{ fontFamily: "Manrope_700Bold" }}>
            Select Model
          </Text>
          <Text className="text-sm text-on-surface-variant mb-6" style={{ fontFamily: "Inter_400Regular" }}>
            Choose the default model to use for chat and generation. We recommend a mini model for faster responses.
          </Text>
          
          <View className="mb-6">
            {models.map((m) => (
              <TouchableOpacity
                key={m.value}
                onPress={() => setModel(m.value)}
                className={`p-4 rounded-xl border flex-row items-center justify-between mb-3 ${
                  model === m.value ? 'bg-primary/10 border-primary' : 'bg-surface-container-low border-outline-variant/20'
                }`}
              >
                <Text className={`text-base font-bold ${model === m.value ? 'text-primary' : 'text-on-surface'}`}>{m.label}</Text>
                {model === m.value && <MaterialIcons name="check-circle" size={24} color="#4e45e4" />}
              </TouchableOpacity>
            ))}
          </View>
          
          <View className="flex-1 justify-end mt-4 flex-row items-end">
            <TouchableOpacity
              onPress={() => setWizardStep(2)}
              className="bg-surface-container py-4 rounded-xl items-center justify-center mr-3 px-6"
              disabled={saving}
            >
              <MaterialIcons name="arrow-back" size={20} color="#94a3b8" />
            </TouchableOpacity>
            
            <TouchableOpacity
              onPress={saveSettings}
              disabled={saving}
              className={`py-4 rounded-xl items-center justify-center flex-1 flex-row ${saving ? 'bg-primary/70' : 'bg-primary'}`}
            >
              {saving ? (
                <ActivityIndicator color="white" />
              ) : (
                <>
                  <MaterialIcons name="save" size={20} color="white" style={{ marginRight: 8 }} />
                  <Text className="text-white font-bold text-base" style={{ fontFamily: "Manrope_700Bold" }}>Save Settings</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        </View>
      )}
    </View>
  );

  return (
    <SafeAreaView className="flex-1 bg-background">
      <View className="flex-row items-center px-5 py-4 border-b border-outline-variant/10 bg-background">
        <TouchableOpacity 
          onPress={() => {
            if (viewMode === 'setup' && hasExistingKey) {
              setViewMode('view');
            } else {
              navigation.goBack();
            }
          }} 
          className="mr-3 p-1"
        >
          <MaterialIcons name="arrow-back" size={24} color="#2b3437" />
        </TouchableOpacity>
        <Text
          className="text-lg font-bold text-on-surface flex-1"
          style={{ fontFamily: "Manrope_700Bold" }}
        >
          AI Configuration
        </Text>
      </View>

      <ScrollView className="flex-1 px-5 pt-6" contentContainerStyle={{ paddingBottom: 40 }}>
        {loading ? (
          <View className="items-center justify-center flex-1 min-h-[300px]">
            <ActivityIndicator size="large" color="#4e45e4" />
            <Text className="mt-4 text-on-surface-variant font-medium">Loading settings...</Text>
          </View>
        ) : (
          viewMode === 'view' ? renderViewMode() : renderSetupWizard()
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
