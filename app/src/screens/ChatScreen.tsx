import React, { useState, useRef, useEffect } from 'react';
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    FlatList,
    KeyboardAvoidingView,
    Platform,
    ActivityIndicator,
    Keyboard,
    Alert,
    Animated as RNAnimated,
} from 'react-native';
import Markdown from 'react-native-markdown-display';
import * as Clipboard from 'expo-clipboard';
import { universalAlert } from '../lib/alerts';
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

const ToolGroupView = ({ item, prevMessage, renderDateDivider }: { item: any, prevMessage: any, renderDateDivider: any }) => {
    const [expanded, setExpanded] = useState(false);
    const dateDivider = renderDateDivider(item.created_at || new Date().toISOString(), prevMessage?.created_at);

    return (
        <View key={item.id}>
            {dateDivider}
            <View className="items-start mb-4 ml-10">
                <TouchableOpacity
                    onPress={() => setExpanded(!expanded)}
                    className="flex-row items-center bg-surface-variant/30 px-3 py-1.5 rounded-full border border-outline-variant/20 gap-2"
                >
                    <MaterialIcons name="build" size={14} color="#4e45e4" />
                    <Text className="text-xs text-on-surface-variant font-medium" style={{ fontFamily: "Inter_500Medium" }}>
                        {item.tools.length} tool {item.tools.length === 1 ? 'call' : 'calls'}
                    </Text>
                    <MaterialIcons name={expanded ? "expand-less" : "expand-more"} size={16} color="#4e45e4" />
                </TouchableOpacity>

                {expanded && (
                    <View className="mt-2 ml-2 pl-2 border-l border-outline-variant/20 gap-2">
                        {item.tools.map((tool: any, idx: number) => (
                            <View key={tool.id || idx} className="flex-row items-center gap-2">
                                <MaterialIcons name="auto-awesome" size={12} color="#586064" />
                                <Text className="text-xs text-on-surface-variant" style={{ fontFamily: "Inter_400Regular", textTransform: 'capitalize' }}>
                                    {tool.toolName.replace(/_/g, ' ')}
                                </Text>
                            </View>
                        ))}
                    </View>
                )}
            </View>
        </View>
    );
};

export default function ChatScreen() {
    const navigation = useNavigation<any>();
    const { messages, status, sendText, sendAudio, isWaitingForResponse, isLoadingHistory, fetchHistory, hasMoreHistory } = useChat();
    const [inputText, setInputText] = useState('');
    const [isFetchingMore, setIsFetchingMore] = useState(false);

    const [toastMessage, setToastMessage] = useState<string | null>(null);
    const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
    const toastTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const copyTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const toastOpacity = useRef(new RNAnimated.Value(0)).current;

    const showToast = (msg: string) => {
        if (toastTimeoutRef.current) {
            clearTimeout(toastTimeoutRef.current);
        }
        setToastMessage(msg);
        toastOpacity.setValue(0);
        RNAnimated.timing(toastOpacity, {
            toValue: 1,
            duration: 150,
            useNativeDriver: Platform.OS !== 'web',
        }).start();

        toastTimeoutRef.current = setTimeout(() => {
            RNAnimated.timing(toastOpacity, {
                toValue: 0,
                duration: 200,
                useNativeDriver: Platform.OS !== 'web',
            }).start(() => {
                setToastMessage(null);
            });
        }, 2000);
    };

    const handleCopyMessage = async (id: string, content: string) => {
        if (!content) return;
        await Clipboard.setStringAsync(content);
        showToast('Copied');
        setCopiedMessageId(id);
        if (copyTimeoutRef.current) {
            clearTimeout(copyTimeoutRef.current);
        }
        copyTimeoutRef.current = setTimeout(() => {
            setCopiedMessageId(null);
        }, 2000);
    };

    useEffect(() => {
        return () => {
            if (toastTimeoutRef.current) {
                clearTimeout(toastTimeoutRef.current);
            }
            if (copyTimeoutRef.current) {
                clearTimeout(copyTimeoutRef.current);
            }
        };
    }, []);

    const groupedMessages = React.useMemo(() => {
        const result: any[] = [];
        let currentToolGroup: any = null;

        for (let i = 0; i < messages.length; i++) {
            const msg = messages[i];
            if (msg.toolName) {
                if (!currentToolGroup) {
                    currentToolGroup = {
                        id: `group-${msg.id}`,
                        isToolGroup: true,
                        tools: [msg],
                        created_at: msg.created_at,
                        role: 'assistant',
                        content: ''
                    };
                    result.push(currentToolGroup);
                } else {
                    currentToolGroup.tools.unshift(msg);
                }
            } else {
                currentToolGroup = null;
                result.push(msg);
            }
        }
        return result;
    }, [messages]);

    const loadMoreMessages = async () => {
        if (!isLoadingHistory && !isFetchingMore && hasMoreHistory) {
            setIsFetchingMore(true);
            await fetchHistory(messages.length, 30, true);
            setIsFetchingMore(false);
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
    const flatListRef = useRef<FlatList>(null);
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
        if (!inputText.trim() || isWaitingForResponse) return;
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
    const renderDateDivider = (currentDateStr: string, prevDateStr: string | undefined) => {
        if (!currentDateStr) return null;
        const current = new Date(currentDateStr);
        const prev = prevDateStr ? new Date(prevDateStr) : null;

        let showDivider = false;
        if (!prev) {
            showDivider = true; // Last item in array (oldest overall)
        } else if (current.getDate() !== prev.getDate() || current.getMonth() !== prev.getMonth() || current.getFullYear() !== prev.getFullYear()) {
            showDivider = true;
        }

        if (showDivider) {
            // Formatting exactly like WhatsApp (Today, Yesterday, April 18)
            const now = new Date();
            let label = "";
            const diffMs = now.getTime() - current.getTime();
            const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

            if (diffDays === 0 && now.getDate() === current.getDate()) {
                label = "Today";
            } else if (diffDays === 1 || (diffDays === 0 && now.getDate() !== current.getDate())) {
                label = "Yesterday";
            } else {
                label = current.toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: current.getFullYear() !== now.getFullYear() ? 'numeric' : undefined });
            }

            return (
                <View className="items-center my-4">
                    <View className="bg-surface-variant/50 px-3 py-1 rounded-full border border-outline-variant/10">
                        <Text className="text-xs text-on-surface-variant font-medium" style={{ fontFamily: "Inter_500Medium" }}>{label}</Text>
                    </View>
                </View>
            );
        }
        return null;
    };

    const renderMessage = ({ item, index }: { item: any, index: number }) => {
        if (item.isToolGroup) {
            return <ToolGroupView key={item.id} item={item} prevMessage={groupedMessages[index + 1]} renderDateDivider={renderDateDivider} />;
        }

        const isUser = item.role === 'user';
        const isTyping = item.content === '' && item.role === 'assistant' && isWaitingForResponse && !item.toolName;

        if (!item.content && item.role === 'assistant' && !isTyping && !item.toolName) return null;

        // In descending list, groupedMessages[index + 1] is the older message.
        const prevMessage = groupedMessages[index + 1];
        const dateDivider = renderDateDivider(item.created_at || new Date().toISOString(), prevMessage?.created_at);

        return (
            <View key={item.id || index}>
                {dateDivider}
                <View className={`w-full flex-col mb-4 ${isUser ? 'items-end' : 'items-start'}`}>
                    <View className={`flex-row gap-2 items-end max-w-[85%] ${isUser ? 'flex-row-reverse' : ''}`} style={{ flexShrink: 1 }}>
                        <View className={`w-8 h-8 rounded-full items-center justify-center -mb-2 flex-shrink-0 ${isUser ? 'bg-surface-variant' : 'bg-secondary-container'}`}>
                            <MaterialIcons name={isUser ? "person" : "smart-toy"} size={18} color={isUser ? "#586064" : "#4e45e4"} />
                        </View>
                        <View className={`p-4 rounded-2xl ${isUser ? 'bg-secondary rounded-br-sm' : 'bg-surface-container rounded-bl-sm'} ${isTyping ? 'py-5' : ''}`} style={{ flexShrink: 1, minWidth: isTyping ? 50 : 'auto' }}>
                            {isTyping ? (
                                <TypingWave />
                            ) : (
                                <Markdown
                                    style={{
                                        body: {
                                            color: isUser ? '#FFFFFF' : '#2b3437',
                                            fontFamily: isUser ? "Inter_500Medium" : "Inter_400Regular",
                                            fontSize: 14,
                                            lineHeight: 22,
                                        },
                                        paragraph: {
                                            marginTop: 0,
                                            marginBottom: 8,
                                        },
                                        link: {
                                            color: isUser ? '#E0E7FF' : '#4e45e4',
                                        },
                                        list_item: {
                                            flexDirection: 'row',
                                        },
                                        code_inline: {
                                            backgroundColor: isUser ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.05)',
                                            color: isUser ? '#FFFFFF' : '#2b3437',
                                            borderRadius: 4,
                                            paddingHorizontal: 4,
                                            paddingVertical: 2,
                                            fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
                                        },
                                        code_block: {
                                            backgroundColor: isUser ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.05)',
                                            color: isUser ? '#FFFFFF' : '#2b3437',
                                            borderRadius: 8,
                                            padding: 8,
                                            fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
                                        }
                                    }}
                                >
                                    {item.content}
                                </Markdown>
                            )}
                        </View>
                    </View>

                    {!isUser && !isTyping && (
                        <View className="flex-row items-center mt-1 ml-11 gap-4">
                            <Text className="text-[10px] text-on-surface-variant/70 font-medium tracking-wide">
                                Gemini 3.1 Pro
                            </Text>
                            <TouchableOpacity
                                onPress={() => handleCopyMessage(item.id || index.toString(), item.content)}
                                className="p-1"
                            >
                                <MaterialIcons
                                    name={copiedMessageId === (item.id || index.toString()) ? "check" : "content-copy"}
                                    size={13}
                                    color={copiedMessageId === (item.id || index.toString()) ? "#4ADE80" : "#9CA4AA"}
                                />
                            </TouchableOpacity>
                        </View>
                    )}

                    {isUser && !isTyping && (
                        <View className="flex-row items-center mt-1 mr-11 justify-end gap-4">
                            <TouchableOpacity
                                onPress={() => handleCopyMessage(item.id || index.toString(), item.content)}
                                className="p-1"
                            >
                                <MaterialIcons
                                    name={copiedMessageId === (item.id || index.toString()) ? "check" : "content-copy"}
                                    size={13}
                                    color={copiedMessageId === (item.id || index.toString()) ? "#4ADE80" : "#9CA4AA"}
                                />
                            </TouchableOpacity>
                        </View>
                    )}
                </View>
            </View>
        );
    };

    const isStreaming = messages.length > 0 && messages[0].role === 'assistant' && status === 'connected';

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
            {/* Header */}
            <View className="flex-row items-center justify-between px-5 py-3 border-b border-outline-variant/10 bg-background">
                <View className="flex-row items-center gap-3">
                    <TouchableOpacity onPress={() => {
                        navigation.goBack();
                    }} className="p-1">
                        <MaterialIcons name="arrow-back" size={24} color="#2b3437" />
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
                <View className="flex-1 relative">
                    {messages.length === 0 && isLoadingHistory ? (
                        <View className="flex-1 justify-center items-center bg-background">
                            <ActivityIndicator size="large" color="#4e45e4" />
                            <Text className="text-sm mt-3 text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>Loading conversation...</Text>
                        </View>
                    ) : messages.length === 0 && !isLoadingHistory ? (
                        <View className="flex-1 justify-center items-center py-32 opacity-50">
                            <MaterialIcons name="forum" size={64} color="#586064" />
                            <Text className="text-lg mt-4 text-on-surface-variant" style={{ fontFamily: "Inter_500Medium" }}>Start a conversation</Text>
                            <Text className="text-sm mt-1 text-center px-10 text-on-surface-variant" style={{ fontFamily: "Inter_400Regular" }}>
                                Type a message and press Enter or click send to chat.
                            </Text>
                        </View>
                    ) : (
                        <FlatList
                            ref={flatListRef}
                            className="flex-1 bg-background"
                            contentContainerStyle={{ paddingVertical: 16, paddingHorizontal: 16 }}
                            data={groupedMessages}
                            keyExtractor={(item, index) => item.id || index.toString()}
                            renderItem={renderMessage}
                            inverted={true}
                            showsVerticalScrollIndicator={false}
                            keyboardShouldPersistTaps="handled"
                            onEndReached={loadMoreMessages}
                            onEndReachedThreshold={0.5}
                            ListFooterComponent={isFetchingMore || isLoadingHistory ? (
                                <ActivityIndicator size="small" color="#4e45e4" style={{ marginVertical: 10 }} />
                            ) : null}
                        />
                    )}

                    {/* Floating Toast Notification Chip (Above Text Field at Bottom Left) */}
                    {toastMessage && (
                        <RNAnimated.View
                            style={{
                                position: 'absolute',
                                bottom: 84,
                                left: 12,
                                zIndex: 9999,
                                opacity: toastOpacity,
                                backgroundColor: '#2b3437',
                                paddingHorizontal: 14,
                                paddingVertical: 8,
                                borderRadius: 8,
                                shadowColor: '#000',
                                shadowOffset: { width: 0, height: 2 },
                                shadowOpacity: 0.25,
                                shadowRadius: 3.84,
                                elevation: 5,
                            }}
                        >
                            <Text style={{ color: '#ffffff', fontSize: 12, fontFamily: 'Inter_500Medium', fontWeight: '500' }}>
                                {toastMessage}
                            </Text>
                        </RNAnimated.View>
                    )}

                    {/* Input Bar - Fixed at bottom, NOT inside scroll view */}
                    <View className="bg-surface border-t border-outline-variant/10 px-4 py-3">
                        <View className="flex-row items-end gap-3">
                            {/* Main Input Area */}
                            {!isRecording ? (
                                <View className="flex-1 flex-row items-end rounded-3xl bg-surface-container px-4 min-h-[48px] py-1 border border-outline-variant/20">
                                    <TextInput
                                        className="flex-1 max-h-[120px] text-sm text-on-surface"
                                        placeholder={isWaitingForResponse ? "DailyPilot is thinking..." : "Message DailyPilot..."}
                                        placeholderTextColor="#586064"
                                        value={inputText}
                                        onChangeText={setInputText}
                                        onSubmitEditing={handleSendText}
                                        multiline
                                        style={{ fontFamily: "Inter_400Regular", minHeight: 40, paddingTop: 10, paddingBottom: 10, textAlignVertical: 'top', ...(Platform.OS === 'web' ? { outlineStyle: 'none' } : {}) as any }}
                                        returnKeyType="send"
                                        editable={status === 'connected' && !isWaitingForResponse}
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
                                                className={`w-10 h-10 items-center justify-center rounded-full bg-surface-variant ${isWaitingForResponse ? 'opacity-40' : ''}`}
                                                disabled={status !== 'connected' || isWaitingForResponse}
                                            >
                                                <MaterialIcons name="mic-none" size={22} color="#9CA4AA" />
                                            </TouchableOpacity>
                                        )}

                                        {inputText.trim().length > 0 && (
                                            <Animated.View entering={FadeIn.duration(200)} exiting={FadeOut.duration(150)}>
                                                <TouchableOpacity
                                                    onPress={handleSendText}
                                                    className={`w-10 h-10 items-center justify-center bg-surface-variant rounded-full ml-1 ${isWaitingForResponse ? 'opacity-40' : ''}`}
                                                    disabled={status !== 'connected' || isWaitingForResponse}
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
