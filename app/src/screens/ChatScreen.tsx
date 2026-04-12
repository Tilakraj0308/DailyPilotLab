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
    Alert,
    Switch,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialIcons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import * as FileSystem from 'expo-file-system/legacy';
import { useChat, ChatMessage, ChatSessionSummary } from '../hooks/useChat';
import { useAudioRecorder, requestRecordingPermissionsAsync, setAudioModeAsync } from 'expo-audio';
import Animated, { useSharedValue, withTiming, FadeIn, FadeOut, withRepeat, withSequence, withDelay } from 'react-native-reanimated';
import SoundBarsEqualizer from '../components/SoundBarsEqualizer';

// Safely imported expo-audio
const isAudioAvailable = true;

const HIGH_QUALITY_OPTIONS = {
    extension: '.m4a',
    sampleRate: 44100,
    numberOfChannels: 2,
    bitRate: 128000,
    isMeteringEnabled: true,
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

const TypingWave = () => {
    const dot1 = useSharedValue(0);
    const dot2 = useSharedValue(0);
    const dot3 = useSharedValue(0);

    useEffect(() => {
        const animateDot = (dot: any, delay: number) => {
            dot.value = withDelay(delay, withRepeat(
                withSequence(
                    withTiming(-5, { duration: 300 }),
                    withTiming(0, { duration: 300 })
                ),
                -1,
                true
            ));
        };
        animateDot(dot1, 0);
        animateDot(dot2, 150);
        animateDot(dot3, 300);
    }, []);

    return (
        <View className="flex-row items-center gap-1">
            <Animated.View style={{ transform: [{ translateY: dot1 }] }} className="w-2 h-2 rounded-full bg-on-surface-variant" />
            <Animated.View style={{ transform: [{ translateY: dot2 }] }} className="w-2 h-2 rounded-full bg-on-surface-variant" />
            <Animated.View style={{ transform: [{ translateY: dot3 }] }} className="w-2 h-2 rounded-full bg-on-surface-variant" />
        </View>
    );
};

export default function ChatScreen() {
    const navigation = useNavigation<any>();
    const { messages, status, sendText, sendAudio, clearSession, isWaitingForResponse, getSessions, loadSession } = useChat();
    const [inputText, setInputText] = useState('');
    const [trainMemories, setTrainMemories] = useState(true);

    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const sidebarX = useSharedValue(-300);
    const [sessionsGrouped, setSessionsGrouped] = useState<{title: string, data: ChatSessionSummary[]}[]>([]);

    const fetchAndGroupSessions = async () => {
        const sessions = await getSessions();
        const now = new Date();
        const today: ChatSessionSummary[] = [];
        const yesterday: ChatSessionSummary[] = [];
        const previous7Days: ChatSessionSummary[] = [];
        const older: ChatSessionSummary[] = [];

        sessions.forEach(s => {
            const date = new Date(s.updated_at);
            const diffTime = Math.abs(now.getTime() - date.getTime());
            const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
            
            if (diffDays === 0 && now.getDate() === date.getDate()) {
                today.push(s);
            } else if (diffDays === 1 || (diffDays === 0 && now.getDate() !== date.getDate())) {
                yesterday.push(s);
            } else if (diffDays <= 7) {
                previous7Days.push(s);
            } else {
                older.push(s);
            }
        });

        const groups = [];
        if (today.length) groups.push({ title: 'Today', data: today });
        if (yesterday.length) groups.push({ title: 'Yesterday', data: yesterday });
        if (previous7Days.length) groups.push({ title: 'Previous 7 Days', data: previous7Days });
        if (older.length) groups.push({ title: 'Older', data: older });

        setSessionsGrouped(groups);
    };

    const toggleSidebar = () => {
        const nextState = !isSidebarOpen;
        setIsSidebarOpen(nextState);
        sidebarX.value = withTiming(nextState ? 0 : -300, { duration: 250 });
        if (nextState) {
            fetchAndGroupSessions();
        }
    };


    // Audio recording state
    const [isRecording, setIsRecording] = useState(false);
    const [recordingDuration, setRecordingDuration] = useState(0);
    const [isUploadingAudio, setIsUploadingAudio] = useState(false);
    const recorder = useAudioRecorder(HIGH_QUALITY_OPTIONS);
    const timerRef = useRef<NodeJS.Timeout | null>(null);
    const isCalibratingRef = useRef<boolean>(true);
    const noiseFloorRef = useRef<number>(-160);
    const calibrationSamplesRef = useRef<number[]>([]);
    const volumeHistoryRef = useRef<number[]>([]);
    const hasSpokenRef = useRef<boolean>(false);
    const silenceTicksRef = useRef<number>(0);
    const scrollViewRef = useRef<ScrollView>(null);
    const volumeAnim = useSharedValue(-60);
    const rawVolumeAnim = useSharedValue(-60); // Always-updated raw metering for equalizer
    const noiseFloorAnim = useSharedValue(-60); // Dynamic noise floor for equalizer normalization



    const setupAudioPermissions = async () => {
        try {
            const { status } = await requestRecordingPermissionsAsync();
            if (status !== 'granted') {
                console.warn('Audio permissions not granted');
                return false;
            }
            await setAudioModeAsync({
                allowsRecording: true,
                playsInSilentMode: true,
                interruptionMode: 'duckOthers',
                shouldRouteThroughEarpiece: false,
            });
            return true;
        } catch (err) {
            console.error("Failed to setup audio", err);
            return false;
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
            const hasPermission = await setupAudioPermissions();
            if (!hasPermission) {
                Alert.alert("Permission Required", "Please grant audio recording permissions to use voice chat.");
                return;
            }

            console.log('🎤 Starting recording...');
            setIsRecording(true);
            setRecordingDuration(0);

            // Reset refs
            isCalibratingRef.current = true;
            noiseFloorRef.current = -160;
            calibrationSamplesRef.current = [];
            volumeHistoryRef.current = [];
            hasSpokenRef.current = false;
            silenceTicksRef.current = 0;

            await recorder.prepareToRecordAsync();
            recorder.record();
            console.log('✅ Recording started');

            let totalTicks = 0;

            // Start timer (200ms = 1 tick)
            timerRef.current = setInterval(() => {
                try {
                    totalTicks++;
                    // Update UI duration every 5 ticks (1 second)
                    if (totalTicks % 5 === 0) {
                        setRecordingDuration((prev) => prev + 1);
                    }

                    const status = recorder.getStatus();
                    const currentVolume = status?.metering ?? -160;

                    // Phase 1: Calibration (First 1 second / 5 ticks)
                    if (isCalibratingRef.current) {
                        calibrationSamplesRef.current.push(currentVolume);
                        console.log(`[Calibration] Tick ${totalTicks}, Volume: ${currentVolume}dB`);

                        // Always feed raw volume to equalizer
                        rawVolumeAnim.value = currentVolume;

                        if (totalTicks >= 5) {
                            const avg = calibrationSamplesRef.current.reduce((a, b) => a + b, 0) / calibrationSamplesRef.current.length;
                            noiseFloorRef.current = avg;
                            noiseFloorAnim.value = avg;
                            isCalibratingRef.current = false;
                            console.log(`[Calibration Complete] Noise Floor set to: ${noiseFloorRef.current}dB`);
                        }
                        return;
                    }

                    // Always feed raw volume to equalizer
                    rawVolumeAnim.value = currentVolume;

                    // Phase 2: Variance-Based Detection
                    volumeHistoryRef.current.push(currentVolume);
                    if (volumeHistoryRef.current.length > 5) {
                        volumeHistoryRef.current.shift();
                    }

                    const speechThreshold = noiseFloorRef.current + 12;

                    if (currentVolume > speechThreshold) {
                        const maxVol = Math.max(...volumeHistoryRef.current);
                        const minVol = Math.min(...volumeHistoryRef.current);
                        const variance = maxVol - minVol;

                        if (variance > 5) {
                            if (!hasSpokenRef.current) {
                                console.log('🗣️ Speech detected! Started listening.');
                            }
                            hasSpokenRef.current = true;
                            silenceTicksRef.current = 0;
                            console.log(`[Speech] Vol: ${currentVolume.toFixed(2)}dB, Var: ${variance.toFixed(2)}dB`);

                            // Animate wave only for active speech
                            volumeAnim.value = withTiming(currentVolume, { duration: 100 });
                        } else {
                            silenceTicksRef.current++;
                            console.log(`[Steady Noise] Vol: ${currentVolume.toFixed(2)}dB, Var: ${variance.toFixed(2)}dB -> Silence Tick: ${silenceTicksRef.current}`);

                            // Retract wave when not speaking
                            volumeAnim.value = withTiming(-60, { duration: 200 });
                        }
                    } else {
                        silenceTicksRef.current++;
                        console.log(`[Silence] Vol: ${currentVolume.toFixed(2)}dB (under threshold ${speechThreshold.toFixed(2)}dB) -> Silence Tick: ${silenceTicksRef.current}`);

                        // Retract wave on silence
                        volumeAnim.value = withTiming(-60, { duration: 200 });
                    }

                    // Phase 3: Auto-Stop Triggers

                    // Scenario 1: Initial Silence (10 seconds = 50 ticks)
                    if (!hasSpokenRef.current && silenceTicksRef.current >= 50) {
                        console.log('⏱️ 10 seconds of initial silence detected, stopping and discarding...');
                        stopRecording(true);
                        return;
                    }

                    // Scenario 2: Speech Ended (5 seconds = 25 ticks)
                    if (hasSpokenRef.current && silenceTicksRef.current >= 25) {
                        console.log('⏱️ 5 seconds of silence after speech detected, stopping and processing...');
                        stopRecording(false);
                        return;
                    }

                    // Scenario 3: Absolute Max (60 seconds = 300 ticks)
                    if (totalTicks >= 300) {
                        console.log('⏱️ Absolute max time reached (60s), stopping and processing...');
                        stopRecording(false);
                        return;
                    }
                } catch (e) {
                    console.error("Error in recording interval:", e);
                }
            }, 200);
        } catch (err) {
            console.error("Failed to start recording", err);
            setIsRecording(false);
            Alert.alert("Recording Error", "Failed to start audio recording");
        }
    };

    const stopRecording = async (discard: boolean = false) => {
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

            if (discard) {
                console.log('🗑️ Recording discarded (initial silence constraint)');
                return;
            }

            // If no speech was detected, skip Whisper and preserve existing input text
            if (!hasSpokenRef.current) {
                console.log('🔇 No speech detected, skipping transcription');
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

    // Manual keyboard height tracking to avoid residual padding
    const [keyboardHeight, setKeyboardHeight] = useState(0);
    useEffect(() => {
        const showSub = Keyboard.addListener('keyboardDidShow', (e) => {
            setKeyboardHeight(e.endCoordinates.height);
        });
        const hideSub = Keyboard.addListener('keyboardDidHide', () => {
            setKeyboardHeight(0);
        });
        return () => {
            showSub.remove();
            hideSub.remove();
        };
    }, []);

    return (
        <SafeAreaView className="flex-1 bg-background" edges={['top', 'bottom']}>
            {/* Sidebar Overlay */}
            {isSidebarOpen && (
                <View style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 40, backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <TouchableOpacity
                        style={{ flex: 1 }}
                        activeOpacity={1}
                        onPress={toggleSidebar}
                    />
                </View>
            )}

            {/* Sidebar animated view */}
            <Animated.View style={{ transform: [{ translateX: sidebarX }], position: 'absolute', top: 0, left: 0, bottom: 0, width: 300, zIndex: 50, backgroundColor: '#ffffff', shadowColor: '#000', shadowOffset: { width: 4, height: 0 }, shadowOpacity: 0.1, shadowRadius: 10, elevation: 10 }}>
                <SafeAreaView className="flex-1" edges={['top', 'bottom']}>
                    <View className="flex-row items-center justify-between p-4 border-b border-outline-variant/10">
                        <Text className="text-lg font-bold text-on-surface" style={{ fontFamily: "Manrope_700Bold" }}>Chat History</Text>
                        <TouchableOpacity onPress={toggleSidebar} className="p-1">
                            <MaterialIcons name="close" size={24} color="#586064" />
                        </TouchableOpacity>
                    </View>
                    <ScrollView className="flex-1 p-2" showsVerticalScrollIndicator={false}>
                        {sessionsGrouped.map(group => (
                            <View key={group.title} className="mb-4">
                                <Text className="text-xs font-bold text-on-surface-variant mb-2 px-2" style={{ fontFamily: "Inter_500Medium" }}>{group.title}</Text>
                                {group.data.map(session => (
                                    <TouchableOpacity 
                                        key={session.id} 
                                        className="px-3 py-3 rounded-lg flex-row items-center gap-3 mb-1 bg-surface-container/30"
                                        onPress={() => { toggleSidebar(); loadSession(session.id); }}
                                    >
                                        <MaterialIcons name="chat-bubble-outline" size={18} color="#586064" />
                                        <Text className="text-sm text-on-surface flex-1" numberOfLines={1} style={{ fontFamily: "Inter_400Regular" }}>
                                            {session.title || "New Chat"}
                                        </Text>
                                    </TouchableOpacity>
                                ))}
                            </View>
                        ))}
                        {sessionsGrouped.length === 0 && (
                             <Text className="text-sm text-on-surface-variant p-4 text-center" style={{ fontFamily: "Inter_400Regular" }}>No history found.</Text>
                        )}
                    </ScrollView>
                </SafeAreaView>
            </Animated.View>

            {/* Header */}
            <View className="flex-row items-center justify-between px-5 py-3 border-b border-outline-variant/10 bg-background">
                <View className="flex-row items-center gap-3">
                    <TouchableOpacity onPress={() => navigation.goBack()} className="p-1">
                        <MaterialIcons name="arrow-back" size={24} color="#2b3437" />
                    </TouchableOpacity>
                    <TouchableOpacity onPress={toggleSidebar} className="p-1 ml-1">
                        <MaterialIcons name="menu" size={24} color="#2b3437" />
                    </TouchableOpacity>
                    <Text className="text-lg font-bold text-on-surface" style={{ fontFamily: "Manrope_700Bold" }}>
                        DailyPilot Chat
                    </Text>
                </View>
                <TouchableOpacity onPress={clearSession} className="p-2 ml-auto" accessibilityLabel="New Chat">
                    <MaterialIcons name="add-comment" size={22} color="#4e45e4" />
                </TouchableOpacity>
            </View>

            {/* Train Memories Toggle */}
            <View className="flex-row items-center justify-between px-5 py-2 border-b border-outline-variant/10 bg-surface">
                <View className="flex-row items-center gap-2">
                    <MaterialIcons name="psychology" size={20} color="#4e45e4" />
                    <Text className="text-sm font-medium text-on-surface" style={{ fontFamily: "Inter_500Medium" }}>Use chat to train memories</Text>
                </View>
                <Switch 
                    value={trainMemories} 
                    onValueChange={setTrainMemories} 
                    trackColor={{ false: '#e2e8f0', true: '#4e45e4' }}
                    thumbColor={'#ffffff'}
                />
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

            {/* Main Content */}
            <View style={{ flex: 1, paddingBottom: keyboardHeight }}>
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
                                <TypingWave />
                            </View>
                        )}
                    </ScrollView>

                    {/* Input Bar - Fixed at bottom, NOT inside scroll view */}
                    <View className="bg-surface border-t border-outline-variant/10 px-4 py-3">
                        <View className="flex-row items-end gap-3">
                            {/* Main Input Area */}
                            {!isRecording ? (
                                <View className="flex-1 flex-row items-end rounded-3xl bg-surface-container px-4 min-h-[48px] py-1 border border-outline-variant/20">
                                    <TextInput
                                        className="flex-1 max-h-[120px] text-sm text-on-surface"
                                        placeholder="Message DailyPilot..."
                                        placeholderTextColor="#586064"
                                        value={inputText}
                                        onChangeText={setInputText}
                                        onSubmitEditing={handleSendText}
                                        multiline
                                        style={{ fontFamily: "Inter_400Regular", minHeight: 40, paddingTop: 10, paddingBottom: 10, textAlignVertical: 'top' }}
                                        returnKeyType="send"
                                        editable={status === 'connected'}
                                    />

                                    {/* Mic and Send Buttons */}
                                    <View className="ml-2 flex-row items-center">
                                        {/* Microphone Recording Button */}
                                        {isUploadingAudio ? (
                                            <View className="w-10 h-10 items-center justify-center rounded-full">
                                                <ActivityIndicator size={22} color="#4e45e4" />
                                            </View>
                                        ) : !isAudioAvailable ? (
                                            <View className="w-10 h-10 items-center justify-center rounded-full bg-gray-400 opacity-50">
                                                <MaterialIcons name="mic-off" size={22} color="#FFFFFF" />
                                            </View>
                                        ) : (
                                            <TouchableOpacity
                                                onPress={() => startRecording()}
                                                className="w-10 h-10 items-center justify-center rounded-full bg-surface-variant"
                                                disabled={status !== 'connected'}
                                            >
                                                <MaterialIcons name="mic-none" size={22} color="#9CA4AA" />
                                            </TouchableOpacity>
                                        )}

                                        {inputText.trim().length > 0 && (
                                            <Animated.View entering={FadeIn.duration(200)} exiting={FadeOut.duration(150)}>
                                                <TouchableOpacity
                                                    onPress={handleSendText}
                                                    className="w-10 h-10 items-center justify-center bg-surface-variant rounded-full ml-1"
                                                    disabled={status !== 'connected'}
                                                >
                                                    <MaterialIcons name="arrow-upward" size={22} color="#9CA4AA" />
                                                </TouchableOpacity>
                                            </Animated.View>
                                        )}
                                    </View>
                                </View>
                            ) : (
                                <View className="flex-1 flex-row items-center justify-center rounded-3xl bg-surface-container overflow-hidden h-12 relative border border-outline-variant/20">
                                    <SoundBarsEqualizer volumeLevel={rawVolumeAnim} noiseFloorLevel={noiseFloorAnim} />
                                    {/* <SoundBarsEqualizer volumeLevel={volumeAnim} /> */}
                                    <TouchableOpacity
                                        onPress={() => stopRecording()}
                                        className="absolute right-1 z-10 w-10 h-10 items-center justify-center bg-surface-variant rounded-full"
                                    >
                                        <MaterialIcons name="stop" size={24} color="#9CA4AA" />
                                    </TouchableOpacity>
                                </View>
                            )}
                        </View>


                    </View>
                </View>
            </View>
        </SafeAreaView>
    );
}
