import React, { useState, useRef, useEffect } from 'react';
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    ScrollView,
    KeyboardAvoidingView,
    Platform,
    ActivityIndicator,
    Keyboard,
    Alert
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialIcons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import * as FileSystem from 'expo-file-system/legacy';
import { useChat, ChatMessage } from '../hooks/useChat';
import { useAudioRecorder, requestRecordingPermissionsAsync, setAudioModeAsync } from 'expo-audio';

// Safely imported expo-audio
const isAudioAvailable = true;

const HIGH_QUALITY_OPTIONS = {
    extension: '.m4a',
    sampleRate: 44100,
    numberOfChannels: 2,
    bitRate: 128000,
    android: {
        outputFormat: 'mpeg4',
        audioEncoder: 'aac',
    },
    ios: {
        outputFormat: 'aac ',
        audioQuality: 127,
        linearPCMBitDepth: 16,
        linearPCMIsBigEndian: false,
        linearPCMIsFloat: false,
    },
    web: {
        mimeType: 'audio/webm',
        bitsPerSecond: 128000,
    },
} as any;

const MAX_RECORDING_MS = 60000; // 60s max per voice memo

export default function ChatScreen() {
    const navigation = useNavigation<any>();
    const { messages, status, sendText, sendAudio, clearSession, isWaitingForResponse } = useChat();
    const [inputText, setInputText] = useState('');

    // Audio recording state
    const [isRecording, setIsRecording] = useState(false);
    const [recordingDuration, setRecordingDuration] = useState(0);
    const [isUploadingAudio, setIsUploadingAudio] = useState(false);
    const recorder = useAudioRecorder(HIGH_QUALITY_OPTIONS);
    const timerRef = useRef<NodeJS.Timeout | null>(null);
    const silenceTimerRef = useRef<number>(0);
    const scrollViewRef = useRef<ScrollView>(null);

    // Setup audio permissions on mount
    useEffect(() => {
        setupAudioPermissions();
    }, []);

    const setupAudioPermissions = async () => {
        try {
            const { status } = await requestRecordingPermissionsAsync();
            if (status !== 'granted') {
                console.warn('Audio permissions not granted');
            }
            await setAudioModeAsync({
                allowsRecording: true,
                playsInSilentMode: true,
                interruptionMode: 'duckOthers',
                shouldRouteThroughEarpiece: false,
            });
        } catch (err) {
            console.error("Failed to setup audio", err);
        }
    };

    const handleSendText = () => {
        console.log("CALLED HANDLESENDTEXT")
        if (!inputText.trim()) return;
        sendText(inputText.trim());
        setInputText('');
    };

    const startRecording = async () => {
        try {
            console.log('🎤 Starting recording...');
            setIsRecording(true);
            setRecordingDuration(0);

            await recorder.prepareToRecordAsync();
            recorder.record();
            console.log('✅ Recording started');

            silenceTimerRef.current = 0;
            // Start timer
            timerRef.current = setInterval(() => {
                setRecordingDuration((prev) => prev + 1);

                silenceTimerRef.current += 1;
                if (silenceTimerRef.current >= 5) {
                    console.log('⏱️ 5 seconds of silence/inactivity detected, auto-stopping...');
                    stopRecording();
                }
            }, 1000);
        } catch (err) {
            console.error("Failed to start recording", err);
            setIsRecording(false);
            Alert.alert("Recording Error", "Failed to start audio recording");
        }
    };

    const stopRecording = async () => {
        try {
            console.log('🛑 Stopping recording...');

            setIsRecording(false);
            if (timerRef.current) {
                clearInterval(timerRef.current);
                timerRef.current = null;
            }

            await recorder.stop();
            const uri = recorder.uri;
            console.log('✅ Recording stopped, URI:', uri);

            if (!uri) {
                Alert.alert("Error", "Failed to get recording URI");
                return;
            }

            // Send audio to transcribe and place into input
            try {
                setIsUploadingAudio(true);
                console.log('📤 Sending audio for transcription...');
                const transcribedText = await sendAudio(uri);
                console.log('✅ Transcribed text received', transcribedText);
                if (transcribedText) {
                    setInputText(transcribedText);
                }
            } catch (uploadErr) {
                console.error('❌ Failed to transcribe audio:', uploadErr);
                Alert.alert("Error", "Failed to transcribe audio: " + String(uploadErr));
            } finally {
                setIsUploadingAudio(false);
            }
        } catch (err) {
            console.error("Failed to stop recording", err);
            Alert.alert("Error", "Failed to stop recording");
        }
    };

    const formatDuration = (seconds: number) => {
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m}:${s.toString().padStart(2, '0')}`;
    };

    const renderMessage = ({ item, index }: { item: ChatMessage, index: number }) => {
        if (!item.content && item.role === 'assistant') return null;
        const isUser = item.role === 'user';
        return (
            <View key={item.id || index} className={`w-full flex-col mb-4 ${isUser ? 'items-end' : 'items-start'}`}>
                <View className={`flex-row gap-2 items-end max-w-[85%] ${isUser ? 'flex-row-reverse' : ''}`}>
                    <View className={`w-8 h-8 rounded-full items-center justify-center -mb-2 ${isUser ? 'bg-surface-variant' : 'bg-secondary-container'}`}>
                        <MaterialIcons name={isUser ? "person" : "smart-toy"} size={18} color={isUser ? "#586064" : "#4e45e4"} />
                    </View>
                    <View className={`p-4 rounded-2xl ${isUser ? 'bg-secondary rounded-br-sm' : 'bg-surface-container rounded-bl-sm'}`}>
                        <Text
                            className={`text-sm leading-relaxed ${isUser ? 'text-white' : 'text-on-surface'}`}
                            style={{ fontFamily: isUser ? "Inter_500Medium" : "Inter_400Regular" }}
                        >
                            {item.content}
                        </Text>
                    </View>
                </View>
            </View>
        );
    };

    const isStreaming = messages.length > 0 && messages[messages.length - 1].role === 'assistant' && status === 'connected';

    return (
        <SafeAreaView className="flex-1 bg-background" edges={['top']} onTouchStart={() => { silenceTimerRef.current = 0; }}>
            {/* Header */}
            <View className="flex-row items-center justify-between px-5 py-3 border-b border-outline-variant/10 bg-background">
                <View className="flex-row items-center gap-3">
                    <TouchableOpacity onPress={() => navigation.goBack()} className="p-1">
                        <MaterialIcons name="arrow-back" size={24} color="#2b3437" />
                    </TouchableOpacity>
                    <Text className="text-lg font-bold text-on-surface" style={{ fontFamily: "Manrope_700Bold" }}>
                        DailyPilot Chat
                    </Text>
                </View>
                <TouchableOpacity onPress={clearSession} className="p-2 ml-auto" accessibilityLabel="New Chat">
                    <MaterialIcons name="add-comment" size={22} color="#4e45e4" />
                </TouchableOpacity>
            </View>

            {/* Connection Status Banner (if not connected) */}
            {status !== 'connected' && (
                <View className="bg-error-container/20 px-4 py-1 flex-row justify-center items-center gap-2">
                    {status === 'connecting' || status === 'reconnecting' ? (
                        <>
                            <ActivityIndicator size="small" color="#ef4444" />
                            <Text className="text-xs text-error" style={{ fontFamily: "Inter_500Medium" }}>Reconnecting...</Text>
                        </>
                    ) : (
                        <Text className="text-xs text-error" style={{ fontFamily: "Inter_500Medium" }}>Disconnected. Features limited.</Text>
                    )}
                </View>
            )}

            {/* Main Content - Using KeyboardAvoidingView + ScrollView for proper Android keyboard handling */}
            <KeyboardAvoidingView
                behavior={Platform.OS === "ios" ? "padding" : "height"}
                style={{ flex: 1 }}
                keyboardVerticalOffset={Platform.OS === "ios" ? 90 : 0}
            >
                <View className="flex-1">
                    {/* Chat Messages ScrollView */}
                    <ScrollView
                        ref={scrollViewRef}
                        className="flex-1 bg-background"
                        contentContainerStyle={{ paddingVertical: 16, paddingHorizontal: 16 }}
                        onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
                        showsVerticalScrollIndicator={false}
                    >
                        {messages.length === 0 ? (
                            <View className="flex-1 justify-center items-center py-32 opacity-50">
                                <MaterialIcons name="forum" size={64} color="#586064" />
                                <Text className="text-lg mt-4 text-on-surface-variant" style={{ fontFamily: "Inter_500Medium" }}>Start a conversation</Text>
                                <Text className="text-sm mt-1 text-center px-10 text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>
                                    Type a message and press Enter or click send to chat.
                                </Text>
                            </View>
                        ) : (
                            messages.map((item, index) => renderMessage({ item, index }))
                        )}

                        {/* Typing Indicator - Show while waiting for response */}
                        {isWaitingForResponse && (
                            <View className="py-2 flex-row items-center gap-2">
                                <View className="w-8 h-8 rounded-full items-center justify-center bg-secondary-container">
                                    <MaterialIcons name="smart-toy" size={16} color="#4e45e4" />
                                </View>
                                <View className="flex-row items-center gap-1">
                                    <View className="w-2 h-2 rounded-full bg-on-surface-variant" style={{ opacity: 0.5 }} />
                                    <View className="w-2 h-2 rounded-full bg-on-surface-variant" style={{ opacity: 0.7 }} />
                                    <View className="w-2 h-2 rounded-full bg-on-surface-variant" style={{ opacity: 0.9 }} />
                                </View>
                                <Text className="text-xs text-on-surface-variant ml-1" style={{ fontFamily: "Inter_400Regular" }}>AI is thinking...</Text>
                            </View>
                        )}
                    </ScrollView>

                    {/* Input Bar - Fixed at bottom, NOT inside scroll view */}
                    <View className="bg-surface border-t border-outline-variant/10 px-4 py-3">
                        <View className="flex-row items-end gap-3">
                            {/* Main Input Area */}
                            <View className="flex-1 flex-row items-center rounded-3xl bg-surface-container px-4 py-1 border border-outline-variant/20">
                                <TextInput
                                    className="flex-1 max-h-32 text-sm text-on-surface py-3"
                                    placeholder="Message DailyPilot..."
                                    placeholderTextColor="#586064"
                                    value={inputText}
                                    onChangeText={setInputText}
                                    onSubmitEditing={handleSendText}
                                    multiline
                                    style={{ fontFamily: "Inter_400Regular" }}
                                    returnKeyType="send"
                                    editable={status === 'connected'}
                                />

                                {/* Send or Mic Button inside the pill */}
                                {inputText.trim().length > 0 ? (
                                    <TouchableOpacity
                                        onPress={handleSendText}
                                        className="w-9 h-9 items-center justify-center bg-secondary rounded-full ml-2"
                                        disabled={status !== 'connected'}
                                    >
                                        <MaterialIcons name="arrow-upward" size={20} color="#ffffff" />
                                    </TouchableOpacity>
                                ) : isAudioAvailable ? (
                                    <View className="ml-2">
                                        {/* Microphone Recording Button */}
                                        {isUploadingAudio ? (
                                            <View className="w-10 h-10 items-center justify-center rounded-full">
                                                <ActivityIndicator size={22} color="#4e45e4" />
                                            </View>
                                        ) : (
                                            <TouchableOpacity
                                                onPress={() => {
                                                    if (isRecording) {
                                                        stopRecording();
                                                    } else {
                                                        silenceTimerRef.current = 0;
                                                        startRecording();
                                                    }
                                                }}
                                                className={`w-10 h-10 items-center justify-center rounded-full ${isRecording ? 'bg-secondary' : 'bg-surface-variant'
                                                    }`}
                                                disabled={status !== 'connected'}
                                            >
                                                {isRecording ? (
                                                    <View className="flex-row items-center justify-center gap-[2px]">
                                                        <View className="w-1.5 h-3 bg-white rounded-full animate-pulse" />
                                                        <View className="w-1.5 h-4 bg-white rounded-full animate-pulse" />
                                                        <View className="w-1.5 h-2.5 bg-white rounded-full animate-pulse" />
                                                    </View>
                                                ) : (
                                                    <MaterialIcons name="mic-none" size={22} color="#9CA4AA" />
                                                )}
                                            </TouchableOpacity>
                                        )}
                                    </View>
                                ) : (
                                    <View className="w-10 h-10 items-center justify-center rounded-full bg-gray-400 opacity-50">
                                        <MaterialIcons name="mic-off" size={22} color="#FFFFFF" />
                                    </View>
                                )}
                            </View>
                        </View>

                        {/* Recording Indicator */}
                        {isRecording && (
                            <View className="mt-3 flex-row items-center gap-2 bg-error-container/10 px-4 py-2 rounded-lg border border-error/30">
                                <View className="w-3 h-3 rounded-full bg-error animate-pulse" />
                                <Text className="text-sm text-error font-semibold" style={{ fontFamily: "Inter_600SemiBold" }}>
                                    Recording: {formatDuration(recordingDuration)}
                                </Text>
                                <Text className="text-xs text-error/70 ml-auto" style={{ fontFamily: "Inter_400Regular" }}>
                                    Release to send
                                </Text>
                            </View>
                        )}
                    </View>
                </View>
            </KeyboardAvoidingView>
        </SafeAreaView>
    );
}
