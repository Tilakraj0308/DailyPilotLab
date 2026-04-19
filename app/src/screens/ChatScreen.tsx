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
    Animated as RNAnimated,
    NativeSyntheticEvent,
    NativeScrollEvent,
} from 'react-native';
import { universalAlert } from '../lib/alerts';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialIcons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import * as FileSystem from 'expo-file-system/legacy';
import { useChat, ChatMessage, ChatSessionSummary } from '../hooks/useChat';
import { useAudioRecorder, requestRecordingPermissionsAsync, setAudioModeAsync } from 'expo-audio';
import Animated, { useSharedValue, withTiming, FadeIn, FadeOut, withRepeat, withSequence, withDelay } from 'react-native-reanimated';
import SoundBarsEqualizer from '../components/SoundBarsEqualizer';
import SidebarDrawer from '../components/SidebarDrawer';

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

// Platform-aware TypingWave:
// On web, Reanimated shared value worklets don't execute, so we inject a CSS @keyframe animation.
// On native, we use Reanimated as before.
const TypingWave = () => {
    if (Platform.OS === 'web') {
        // Inject CSS once
        if (typeof document !== 'undefined' && !document.getElementById('typing-wave-style')) {
            const style = document.createElement('style');
            style.id = 'typing-wave-style';
            style.textContent = `
                @keyframes typingBounce {
                    0%, 100% { transform: translateY(0px); }
                    50% { transform: translateY(-5px); }
                }
                .typing-dot {
                    width: 8px; height: 8px; border-radius: 50%;
                    background-color: #586064;
                    display: inline-block;
                    animation: typingBounce 0.6s ease-in-out infinite;
                }
                .typing-dot:nth-child(2) { animation-delay: 0.15s; }
                .typing-dot:nth-child(3) { animation-delay: 0.30s; }
            `;
            document.head.appendChild(style);
        }
        return (
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                {/* @ts-ignore – web-only className on View is fine via react-native-web */}
                <div className="typing-dot" />
                <div className="typing-dot" />
                <div className="typing-dot" />
            </View>
        );
    }

    // Native: Reanimated path
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

// Skeleton loader for history sidebar — pulsing placeholder rows
const SKELETON_COUNT = 5;
const HistorySkeleton = () => {
    if (Platform.OS === 'web') {
        // Inject CSS once for pulse animation
        if (typeof document !== 'undefined' && !document.getElementById('skeleton-pulse-style')) {
            const style = document.createElement('style');
            style.id = 'skeleton-pulse-style';
            style.textContent = `
                @keyframes skeletonPulse {
                    0%, 100% { opacity: 0.3; }
                    50% { opacity: 0.7; }
                }
                .skeleton-bar {
                    background-color: #d1d5db;
                    border-radius: 8px;
                    animation: skeletonPulse 1.2s ease-in-out infinite;
                }
            `;
            document.head.appendChild(style);
        }
        return (
            <View style={{ padding: 8 }}>
                {Array.from({ length: SKELETON_COUNT }).map((_, i) => (
                    <View key={i} style={{ flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 12, paddingHorizontal: 12, paddingVertical: 12 }}>
                        {/* @ts-ignore */}
                        <div className="skeleton-bar" style={{ width: 20, height: 20, borderRadius: '50%', flexShrink: 0 }} />
                        {/* @ts-ignore */}
                        <div className="skeleton-bar" style={{ height: 14, flex: 1, animationDelay: `${i * 0.1}s` }} />
                    </View>
                ))}
            </View>
        );
    }

    // Native: use RN Animated for pulse
    const pulseAnim = useRef(new RNAnimated.Value(0.3)).current;
    useEffect(() => {
        const loop = RNAnimated.loop(
            RNAnimated.sequence([
                RNAnimated.timing(pulseAnim, { toValue: 0.7, duration: 600, useNativeDriver: true }),
                RNAnimated.timing(pulseAnim, { toValue: 0.3, duration: 600, useNativeDriver: true }),
            ])
        );
        loop.start();
        return () => loop.stop();
    }, []);

    return (
        <View style={{ padding: 8 }}>
            {Array.from({ length: SKELETON_COUNT }).map((_, i) => (
                <RNAnimated.View key={i} style={{ flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 12, paddingHorizontal: 12, paddingVertical: 12, opacity: pulseAnim }}>
                    <View style={{ width: 20, height: 20, borderRadius: 10, backgroundColor: '#d1d5db' }} />
                    <View style={{ height: 14, flex: 1, borderRadius: 8, backgroundColor: '#d1d5db' }} />
                </RNAnimated.View>
            ))}
        </View>
    );
};

const SESSIONS_PAGE_SIZE = 15;

export default function ChatScreen() {
    const navigation = useNavigation<any>();
    const { messages, status, sendText, sendAudio, clearSession, isWaitingForResponse, isLoadingHistory, getSessions, loadSession } = useChat();
    const [inputText, setInputText] = useState('');

    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [sessionsGrouped, setSessionsGrouped] = useState<{ title: string, data: ChatSessionSummary[] }[]>([]);
    const [isLoadingSessions, setIsLoadingSessions] = useState(false);
    const [sessionOffset, setSessionOffset] = useState(0);
    const [hasMoreSessions, setHasMoreSessions] = useState(true);
    const allSessionsRef = useRef<ChatSessionSummary[]>([]);
    const hasFetchedSessionsRef = useRef(false);

    const groupSessions = (sessions: ChatSessionSummary[]) => {
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
        return groups;
    };

    const fetchAndGroupSessions = async (offset: number = 0, append: boolean = false) => {
        setIsLoadingSessions(true);
        const sessions = await getSessions(SESSIONS_PAGE_SIZE, offset);

        if (sessions.length < SESSIONS_PAGE_SIZE) {
            setHasMoreSessions(false);
        }

        const updated = append ? [...allSessionsRef.current, ...sessions] : sessions;
        allSessionsRef.current = updated;
        setSessionsGrouped(groupSessions(updated));
        setSessionOffset(offset + sessions.length);
        setIsLoadingSessions(false);
    };

    const loadMoreSessions = () => {
        if (!isLoadingSessions && hasMoreSessions) {
            fetchAndGroupSessions(sessionOffset, true);
        }
    };

    const toggleSidebar = () => {
        const nextState = !isSidebarOpen;
        setIsSidebarOpen(nextState);
        if (nextState && !hasFetchedSessionsRef.current) {
            // First open: fetch from server, show skeleton
            fetchAndGroupSessions(0, false).then(() => {
                hasFetchedSessionsRef.current = true;
            });
        }
        // Subsequent opens: cached data is already in sessionsGrouped, shown instantly
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
                universalAlert("Permission Required", "Please grant audio recording permissions to use voice chat.");
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
            universalAlert("Recording Error", "Failed to start audio recording");
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
                universalAlert("Error", "Failed to get recording URI");
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
                universalAlert("Error", "Failed to transcribe audio: " + String(uploadErr));
            } finally {
                setIsUploadingAudio(false);
            }
        } catch (err) {
            console.error("Failed to stop recording", err);
            universalAlert("Error", "Failed to stop recording");
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
                <View className={`flex-row gap-2 items-end max-w-[85%] ${isUser ? 'flex-row-reverse' : ''}`} style={{ flexShrink: 1 }}>
                    <View className={`w-8 h-8 rounded-full items-center justify-center -mb-2 flex-shrink-0 ${isUser ? 'bg-surface-variant' : 'bg-secondary-container'}`}>
                        <MaterialIcons name={isUser ? "person" : "smart-toy"} size={18} color={isUser ? "#586064" : "#4e45e4"} />
                    </View>
                    <View className={`p-4 rounded-2xl ${isUser ? 'bg-secondary rounded-br-sm' : 'bg-surface-container rounded-bl-sm'}`} style={{ flexShrink: 1 }}>
                        <Text
                            className={`text-sm leading-relaxed ${isUser ? 'text-white' : 'text-on-surface'}`}
                            style={{ fontFamily: isUser ? "Inter_500Medium" : "Inter_400Regular", flexWrap: 'wrap' }}
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
    const [isKeyboardVisible, setIsKeyboardVisible] = useState(false);
    useEffect(() => {
        const showSub = Keyboard.addListener('keyboardDidShow', (e) => {
            setKeyboardHeight(e.endCoordinates.height);
            setIsKeyboardVisible(true);
        });
        const hideSub = Keyboard.addListener('keyboardDidHide', () => {
            setKeyboardHeight(0);
            setIsKeyboardVisible(false);
        });
        return () => {
            showSub.remove();
            hideSub.remove();
        };
    }, []);

    return (
        <SafeAreaView className="flex-1 bg-background" edges={['top']}>
            <SidebarDrawer isOpen={isSidebarOpen} onClose={toggleSidebar} width={300}>
                <SafeAreaView className="flex-1 bg-white" edges={['top', 'bottom']}>
                    <View className="flex-1 px-4 py-2">
                        <View className="flex-row items-center justify-between p-4 border-b border-outline-variant/10">
                            <Text className="text-lg font-bold text-on-surface" style={{ fontFamily: "Manrope_700Bold" }}>Recents</Text>
                            <TouchableOpacity onPress={toggleSidebar} className="p-1">
                                <MaterialIcons name="close" size={24} color="#586064" />
                            </TouchableOpacity>
                        </View>
                        <TouchableOpacity
                            onPress={() => { toggleSidebar(); clearSession(); }}
                            className="flex-row items-center gap-3 mx-2 mt-3 mb-1 px-3 py-3 rounded-lg bg-secondary/10 border border-secondary/20"
                        >
                            <MaterialIcons name="add-comment" size={20} color="#4e45e4" />
                            <Text className="text-sm font-medium text-secondary" style={{ fontFamily: "Inter_500Medium" }}>New Chat</Text>
                        </TouchableOpacity>
                        {isLoadingSessions && sessionsGrouped.length === 0 ? (
                            <HistorySkeleton />
                        ) : (
                            <ScrollView
                                className="flex-1 p-2 mt-2"
                                showsVerticalScrollIndicator={false}
                                onScroll={(e: NativeSyntheticEvent<NativeScrollEvent>) => {
                                    const { layoutMeasurement, contentOffset, contentSize } = e.nativeEvent;
                                    if (layoutMeasurement.height + contentOffset.y >= contentSize.height - 40) {
                                        loadMoreSessions();
                                    }
                                }}
                                scrollEventThrottle={400}
                            >
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
                                {sessionsGrouped.length === 0 && !isLoadingSessions && (
                                    <Text className="text-sm text-on-surface-variant p-4 text-center" style={{ fontFamily: "Inter_400Regular" }}>No history found.</Text>
                                )}
                                {isLoadingSessions && sessionsGrouped.length > 0 && <HistorySkeleton />}
                            </ScrollView>
                        )}
                    </View>
                </SafeAreaView>
            </SidebarDrawer>

            {/* Header */}
            <View className="flex-row items-center justify-between px-5 py-3 border-b border-outline-variant/10 bg-background">
                <View className="flex-row items-center gap-3">
                    <TouchableOpacity onPress={toggleSidebar} className="p-1">
                        <MaterialIcons name={isSidebarOpen ? "close" : "menu"} size={24} color="#2b3437" />
                    </TouchableOpacity>
                    <Text className="text-lg font-bold text-on-surface" style={{ fontFamily: "Manrope_700Bold" }}>
                        DailyPilot Chat
                    </Text>
                </View>
            </View>



            {/* Main Content */}
            <KeyboardAvoidingView
                style={{ flex: 1 }}
                behavior="padding"
            >
                <View className="flex-1">
                    {isLoadingHistory ? (
                        <View className="flex-1 justify-center items-center bg-background">
                            <ActivityIndicator size="large" color="#4e45e4" />
                            <Text className="text-sm mt-3 text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>Loading conversation...</Text>
                        </View>
                    ) : (
                    <ScrollView
                        ref={scrollViewRef}
                        className="flex-1 bg-background"
                        contentContainerStyle={{ paddingVertical: 16, paddingHorizontal: 16 }}
                        onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
                        showsVerticalScrollIndicator={false}
                        keyboardShouldPersistTaps="handled"
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
                    )}

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
            </KeyboardAvoidingView>
        </SafeAreaView>
    );
}
