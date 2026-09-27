import React, { useState, useMemo, useRef, useCallback, useEffect } from "react";
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    FlatList,
    ScrollView,
    LayoutChangeEvent,
    Animated,
    Keyboard,
    KeyboardAvoidingView,
    Platform,
    ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { MaterialIcons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useAuth } from "../context/AuthContext";
import { getApiUrl } from "../lib/api";

// ─── Types ──────────────────────────────────────────────────────────────────

interface Question {
    id: string;
    question: string;
    type: "text_input" | "date_picker" | "wheel_picker" | "textarea";
    placeholder?: string;
    prefill_from?: string;
    options?: string[];
    state_key: string;
    show_when?: Record<string, string>;
}

// ─── Constants ──────────────────────────────────────────────────────────────

const ITEM_HEIGHT = 44;
const VISIBLE_ITEMS = 5;
const PICKER_HEIGHT = ITEM_HEIGHT * VISIBLE_ITEMS;

const FALLBACK_QUESTIONS: Question[] = [
    { id: "nickname", question: "What should I call you?", type: "text_input", placeholder: "Your preferred name", prefill_from: "display_name", state_key: "nickname" },
    { id: "dob", question: "What's your Date of Birth?", type: "date_picker", state_key: "date_of_birth" },
    { id: "occupation", question: "What do you do?", type: "wheel_picker", options: ["Student", "Developer", "Teacher", "Housewife", "Chef", "Project Manager", "CTO", "Other"], state_key: "occupation" },
    { id: "student_detail", question: "What are you studying right now? Your current topic that interests you?", type: "text_input", placeholder: "e.g. Computer Science, Machine Learning...", state_key: "study_topic", show_when: { occupation: "Student" } },
    { id: "developer_detail", question: "Where do you work? Your favourite domain of technology?", type: "text_input", placeholder: "e.g. Google — Backend / AI / Mobile...", state_key: "work_domain", show_when: { occupation: "Developer" } },
    { id: "additional_info", question: "Anything more you want to add?", type: "textarea", placeholder: "Your hobbies, goals, constraints...", state_key: "additional_info" },
];

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DAYS = Array.from({ length: 31 }, (_, i) => String(i + 1));
const currentYear = new Date().getFullYear();
const YEARS = Array.from({ length: currentYear - 1930 - 12 }, (_, i) => String(currentYear - 13 - i));

// ─── Drum Picker Component ─────────────────────────────────────────────────

function DrumPicker({
    items,
    selectedIndex,
    onSelect,
    width = 80,
}: {
    items: string[];
    selectedIndex: number;
    onSelect: (index: number) => void;
    width?: number;
}) {
    const scrollRef = useRef<ScrollView>(null);
    const paddedItems = ["", "", ...items, "", ""];

    const scrollTimeout = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        // Scroll to selected on mount
        setTimeout(() => {
            scrollRef.current?.scrollTo({ y: selectedIndex * ITEM_HEIGHT, animated: false });
        }, 100);
        return () => {
            if (scrollTimeout.current) clearTimeout(scrollTimeout.current);
        };
    }, []);

    const handleScroll = (e: any) => {
        const offsetY = e.nativeEvent.contentOffset.y;
        if (scrollTimeout.current) clearTimeout(scrollTimeout.current);

        scrollTimeout.current = setTimeout(() => {
            const index = Math.round(offsetY / ITEM_HEIGHT);
            const clamped = Math.max(0, Math.min(index, items.length - 1));

            // Only update and snap if we actually stopped on a new item or if we're misaligned
            if (clamped !== selectedIndex) {
                onSelect(clamped);
            }
            scrollRef.current?.scrollTo({ y: clamped * ITEM_HEIGHT, animated: true });
        }, 150);
    };

    return (
        <View style={{ height: PICKER_HEIGHT, width, overflow: "hidden" }}>
            {/* Selection highlight bar */}
            <View
                pointerEvents="none"
                style={{
                    position: "absolute",
                    top: ITEM_HEIGHT * 2,
                    left: 0,
                    right: 0,
                    height: ITEM_HEIGHT,
                    backgroundColor: "rgba(78, 69, 228, 0.08)",
                    borderRadius: 10,
                    zIndex: 1,
                }}
            />
            <ScrollView
                ref={scrollRef}
                showsVerticalScrollIndicator={false}
                onScroll={handleScroll}
                scrollEventThrottle={16}
                contentContainerStyle={{ paddingVertical: 0 }}
            >
                {paddedItems.map((item, i) => {
                    const realIndex = i - 2;
                    const isSelected = realIndex === selectedIndex;
                    const isAdjacent = Math.abs(realIndex - selectedIndex) === 1;
                    return (
                        <TouchableOpacity
                            key={`${item}-${i}`}
                            activeOpacity={0.7}
                            onPress={() => {
                                if (realIndex >= 0 && realIndex < items.length) {
                                    onSelect(realIndex);
                                    scrollRef.current?.scrollTo({ y: realIndex * ITEM_HEIGHT, animated: true });
                                }
                            }}
                            style={{
                                height: ITEM_HEIGHT,
                                justifyContent: "center",
                                alignItems: "center",
                                width: "100%",
                            }}
                        >
                            <Text
                                style={{
                                    fontSize: isSelected ? 18 : 15,
                                    fontFamily: isSelected ? "Inter_600SemiBold" : "Inter_400Regular",
                                    color: isSelected ? "#2b3437" : isAdjacent ? "#586064" : "#abb3b7",
                                    opacity: item === "" ? 0 : isSelected ? 1 : isAdjacent ? 0.7 : 0.35,
                                }}
                            >
                                {item}
                            </Text>
                        </TouchableOpacity>
                    );
                })}
            </ScrollView>
        </View>
    );
}

// ─── Date Picker Component ──────────────────────────────────────────────────

function DatePickerWheel({
    value,
    onChange,
}: {
    value: { day: number; month: number; year: number };
    onChange: (val: { day: number; month: number; year: number }) => void;
}) {
    return (
        <View style={{ flexDirection: "row", justifyContent: "center", gap: 8 }}>
            <View style={{ alignItems: "center" }}>
                <Text style={{ fontSize: 11, color: "#586064", fontFamily: "Inter_500Medium", marginBottom: 6 }}>Day</Text>
                <DrumPicker
                    items={DAYS}
                    selectedIndex={value.day - 1}
                    onSelect={(i) => onChange({ ...value, day: i + 1 })}
                    width={60}
                />
            </View>
            <View style={{ alignItems: "center" }}>
                <Text style={{ fontSize: 11, color: "#586064", fontFamily: "Inter_500Medium", marginBottom: 6 }}>Month</Text>
                <DrumPicker
                    items={MONTHS}
                    selectedIndex={value.month}
                    onSelect={(i) => onChange({ ...value, month: i })}
                    width={70}
                />
            </View>
            <View style={{ alignItems: "center" }}>
                <Text style={{ fontSize: 11, color: "#586064", fontFamily: "Inter_500Medium", marginBottom: 6 }}>Year</Text>
                <DrumPicker
                    items={YEARS}
                    selectedIndex={YEARS.indexOf(String(value.year))}
                    onSelect={(i) => onChange({ ...value, year: parseInt(YEARS[i]) })}
                    width={75}
                />
            </View>
        </View>
    );
}

// ─── Occupation Picker Component ────────────────────────────────────────────

function OccupationPicker({
    options,
    selectedIndex,
    onSelect,
    otherText,
    onOtherTextChange,
}: {
    options: string[];
    selectedIndex: number;
    onSelect: (index: number) => void;
    otherText: string;
    onOtherTextChange: (text: string) => void;
}) {
    const showOtherInput = options[selectedIndex] === "Other";
    const fadeAnim = useRef(new Animated.Value(showOtherInput ? 1 : 0)).current;

    useEffect(() => {
        Animated.timing(fadeAnim, {
            toValue: showOtherInput ? 1 : 0,
            duration: 200,
            useNativeDriver: false,
        }).start();
    }, [showOtherInput]);

    return (
        <View style={{ alignItems: "center" }}>
            <DrumPicker
                items={options}
                selectedIndex={selectedIndex}
                onSelect={onSelect}
                width={220}
            />
            <Animated.View
                style={{
                    opacity: fadeAnim,
                    maxHeight: fadeAnim.interpolate({ inputRange: [0, 1], outputRange: [0, 60] }),
                    overflow: "hidden",
                    width: "100%",
                    marginTop: 12,
                }}
            >
                <TextInput
                    style={{
                        backgroundColor: "#f1f4f6",
                        borderRadius: 12,
                        paddingHorizontal: 16,
                        paddingVertical: 12,
                        fontSize: 16,
                        fontFamily: "Inter_400Regular",
                        color: "#2b3437",
                        borderWidth: 1,
                        borderColor: "rgba(171, 179, 183, 0.2)",
                    }}
                    placeholder="Type your occupation…"
                    placeholderTextColor="#737c7f"
                    value={otherText}
                    onChangeText={onOtherTextChange}
                />
            </Animated.View>
        </View>
    );
}

// ─── Main OnboardingScreen ──────────────────────────────────────────────────

export default function OnboardingScreen() {
    const { session, user, setOnboardingCompleted } = useAuth();
    const flatListRef = useRef<FlatList>(null);

    // Measure actual container width (critical for web where app is inside a 480px wrapper)
    const [containerWidth, setContainerWidth] = useState(0);

    // State
    const [allQuestions, setAllQuestions] = useState<Question[]>(FALLBACK_QUESTIONS);
    const [answers, setAnswers] = useState<Record<string, any>>({});
    const [currentIndex, setCurrentIndex] = useState(0);
    const [occupationIndex, setOccupationIndex] = useState(0);
    const [otherOccupationText, setOtherOccupationText] = useState("");
    const [dateValue, setDateValue] = useState({ day: 1, month: 0, year: 2000 });

    // Pre-fill default nickname from Google profile
    useEffect(() => {
        setAnswers((prev) => {
            const newAnswers = { ...prev };

            // Prefill Google display name
            const displayName = user?.user_metadata?.full_name || user?.user_metadata?.name || "";
            if (displayName && !newAnswers.nickname) {
                newAnswers.nickname = displayName;
            }

            return newAnswers;
        });
    }, [user]);

    // Load questions from backend (fallback to hardcoded)
    useEffect(() => {
        loadQuestions();
        loadDraft();
    }, []);

    const loadQuestions = async () => {
        try {
            const apiUrl = getApiUrl();
            const resp = await fetch(`${apiUrl}/onboarding/questions`, {
                headers: { Authorization: `Bearer ${session?.access_token}` },
            });
            if (resp.ok) {
                const data = await resp.json();
                if (data.questions?.length) setAllQuestions(data.questions);
            }
        } catch {
            // Use fallback questions
        }
    };

    const loadDraft = async () => {
        try {
            const draft = await AsyncStorage.getItem("@onboarding_draft");
            if (draft) {
                const parsed = JSON.parse(draft);
                setAnswers((prev) => ({ ...prev, ...parsed }));
            }
        } catch { }
    };

    const saveDraft = async (newAnswers: Record<string, any>) => {
        try {
            await AsyncStorage.setItem("@onboarding_draft", JSON.stringify(newAnswers));
        } catch { }
    };

    // Filter questions based on branching logic
    const activeQuestions = useMemo(() => {
        return allQuestions.filter((q) => {
            if (!q.show_when) return true;
            return Object.entries(q.show_when).every(
                ([key, value]) => answers[key] === value
            );
        });
    }, [allQuestions, answers.occupation]);

    const currentQuestion = activeQuestions[currentIndex];

    // Card width for FlatList rendering — based on measured container, not window
    const cardMargin = 20;
    const cardWidth = containerWidth > 0 ? containerWidth : 300;

    const onCarouselLayout = (e: LayoutChangeEvent) => {
        const { width } = e.nativeEvent.layout;
        if (width > 0 && width !== containerWidth) {
            setContainerWidth(width);
        }
    };

    const updateAnswer = (key: string, value: any) => {
        const updated = { ...answers, [key]: value };
        setAnswers(updated);
        saveDraft(updated);
    };

    const goNext = () => {
        Keyboard.dismiss();

        // If the user clicks Next/Done but left the picker untouched, save the default value
        const currentQ = activeQuestions[currentIndex];
        let currentAnswers = { ...answers };

        if (!currentAnswers[currentQ.state_key]) {
            if (currentQ.type === "date_picker") {
                const dateStr = `${dateValue.year}-${String(dateValue.month + 1).padStart(2, "0")}-${String(dateValue.day).padStart(2, "0")}`;
                currentAnswers[currentQ.state_key] = dateStr;
                updateAnswer(currentQ.state_key, dateStr);
            } else if (currentQ.type === "wheel_picker" && currentQ.options?.[0]) {
                const defaultOcc = currentQ.options[0];
                currentAnswers[currentQ.state_key] = defaultOcc;
                updateAnswer(currentQ.state_key, defaultOcc);
            }
        }

        if (currentIndex === activeQuestions.length - 1) {
            handleSubmit(currentAnswers);
            return;
        }
        const nextIndex = Math.min(currentIndex + 1, activeQuestions.length - 1);
        setCurrentIndex(nextIndex);
        flatListRef.current?.scrollToOffset({ offset: nextIndex * cardWidth, animated: true });
    };

    const goBack = () => {
        Keyboard.dismiss();
        const prevIndex = Math.max(currentIndex - 1, 0);
        setCurrentIndex(prevIndex);
        flatListRef.current?.scrollToOffset({ offset: prevIndex * cardWidth, animated: true });
    };

    const handleSubmit = (finalAnswers = answers) => {
        console.log("Submitting answers:", JSON.stringify({ answers: finalAnswers }));

        const apiUrl = getApiUrl();
        fetch(`${apiUrl}/onboarding/complete`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${session?.access_token}`,
            },
            body: JSON.stringify({ answers: finalAnswers }),
        })
            .then((resp) => {
                if (!resp.ok) {
                    saveDraft(finalAnswers);
                    alert(`Server returned ${resp.status}: Request reached server but failed.`);
                } else {
                    // Success! Delay closing just to be completely safe
                    setTimeout(() => {
                        setOnboardingCompleted(true);
                        AsyncStorage.removeItem("@onboarding_draft").catch(() => { });
                    }, 100);
                }
            })
            .catch((e) => {
                saveDraft(finalAnswers);
                alert(`Network Error: ${e.message}\nAPI URL: ${apiUrl}\nCould not reach the backend!`);
            });
    };

    const handleSkip = () => {
        // Immediately unlock app navigation
        setOnboardingCompleted(true);
        AsyncStorage.removeItem("@onboarding_draft").catch(() => { });

        // Fire-and-forget sync to backend
        const apiUrl = getApiUrl();
        if (session?.access_token && apiUrl) {
            fetch(`${apiUrl}/onboarding/complete`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${session.access_token}`,
                },
                body: JSON.stringify({ answers: answers || {} }),
            }).catch((e) => {
                console.warn("Background onboarding complete sync error:", e);
            });
        }
    };

    // ─── Render Question Content ────────────────────────────────────────

    const renderQuestionContent = (question: Question) => {
        switch (question.type) {
            case "text_input":
                return (
                    <TextInput
                        style={{
                            backgroundColor: "#f1f4f6",
                            borderRadius: 16,
                            paddingHorizontal: 20,
                            paddingVertical: 16,
                            fontSize: 17,
                            fontFamily: "Inter_400Regular",
                            color: "#2b3437",
                            borderWidth: 1,
                            borderColor: "rgba(171, 179, 183, 0.2)",
                        }}
                        placeholder={question.placeholder || "Type here..."}
                        placeholderTextColor="#737c7f"
                        value={answers[question.state_key] || ""}
                        onChangeText={(text) => updateAnswer(question.state_key, text)}
                        accessibilityLabel={question.question}
                        autoFocus={false}
                    />
                );

            case "textarea":
                return (
                    <TextInput
                        style={{
                            backgroundColor: "#f1f4f6",
                            borderRadius: 16,
                            paddingHorizontal: 20,
                            paddingVertical: 16,
                            fontSize: 16,
                            fontFamily: "Inter_400Regular",
                            color: "#2b3437",
                            minHeight: 120,
                            textAlignVertical: "top",
                            borderWidth: 1,
                            borderColor: "rgba(171, 179, 183, 0.2)",
                        }}
                        placeholder={question.placeholder || "Type here..."}
                        placeholderTextColor="#737c7f"
                        value={answers[question.state_key] || ""}
                        onChangeText={(text) => updateAnswer(question.state_key, text)}
                        multiline
                        accessibilityLabel={question.question}
                    />
                );

            case "date_picker":
                return (
                    <DatePickerWheel
                        value={dateValue}
                        onChange={(val) => {
                            setDateValue(val);
                            const dateStr = `${val.year}-${String(val.month + 1).padStart(2, "0")}-${String(val.day).padStart(2, "0")}`;
                            updateAnswer(question.state_key, dateStr);
                        }}
                    />
                );

            case "wheel_picker":
                return (
                    <OccupationPicker
                        options={question.options || []}
                        selectedIndex={occupationIndex}
                        onSelect={(i) => {
                            setOccupationIndex(i);
                            const selected = question.options?.[i] || "";
                            if (selected === "Other") {
                                updateAnswer(question.state_key, otherOccupationText || "Other");
                            } else {
                                updateAnswer(question.state_key, selected);
                                setOtherOccupationText("");
                            }
                        }}
                        otherText={otherOccupationText}
                        onOtherTextChange={(text) => {
                            setOtherOccupationText(text);
                            updateAnswer(question.state_key, text || "Other");
                        }}
                    />
                );

            default:
                return null;
        }
    };

    // ─── Render Card ────────────────────────────────────────────────────

    const renderCard = useCallback(
        ({ item, index }: { item: Question; index: number }) => {
            const isFirst = index === 0;
            const isLast = index === activeQuestions.length - 1;

            return (
                <View
                    style={{
                        width: cardWidth,
                        paddingHorizontal: cardMargin,
                    }}
                >
                    <View
                        style={{
                            backgroundColor: "#ffffff",
                            borderRadius: 28,
                            padding: 28,
                            borderWidth: 1,
                            borderColor: "rgba(171, 179, 183, 0.2)",
                            shadowColor: "#000",
                            shadowOffset: { width: 0, height: 2 },
                            shadowOpacity: 0.06,
                            shadowRadius: 12,
                            elevation: 3,
                            minHeight: 360,
                            justifyContent: "space-between",
                        }}
                    >
                        {/* Progress Dots */}
                        <View style={{ flexDirection: "row", justifyContent: "center", gap: 8, marginBottom: 28 }}>
                            {activeQuestions.map((_, i) => (
                                <View
                                    key={i}
                                    style={{
                                        width: i === index ? 24 : 8,
                                        height: 8,
                                        borderRadius: 4,
                                        backgroundColor: i <= index ? "#4e45e4" : "transparent",
                                        borderWidth: i <= index ? 0 : 1.5,
                                        borderColor: "#4e45e4",
                                    }}
                                />
                            ))}
                        </View>

                        {/* Question Text */}
                        <Text
                            style={{
                                fontSize: 22,
                                fontFamily: "Inter_600SemiBold",
                                color: "#2b3437",
                                textAlign: "center",
                                marginBottom: 28,
                                lineHeight: 30,
                            }}
                        >
                            {item.question}
                        </Text>

                        {/* Input Area */}
                        <View style={{ flex: 1, justifyContent: "center" }}>
                            {renderQuestionContent(item)}
                        </View>

                        {/* Navigation Arrows */}
                        <View
                            style={{
                                flexDirection: "row",
                                justifyContent: "space-between",
                                alignItems: "center",
                                marginTop: 28,
                            }}
                        >
                            <TouchableOpacity
                                onPress={goBack}
                                disabled={isFirst}
                                style={{
                                    width: 48,
                                    height: 48,
                                    borderRadius: 24,
                                    backgroundColor: isFirst ? "#f1f4f6" : "#eaeff1",
                                    justifyContent: "center",
                                    alignItems: "center",
                                }}
                                accessibilityLabel="Previous question"
                                accessibilityRole="button"
                            >
                                <MaterialIcons
                                    name="arrow-back-ios"
                                    size={18}
                                    color={isFirst ? "#abb3b7" : "#2b3437"}
                                    style={{ marginLeft: 4 }}
                                />
                            </TouchableOpacity>

                            <TouchableOpacity
                                onPress={goNext}
                                style={{
                                    height: 48,
                                    borderRadius: 24,
                                    backgroundColor: "#4e45e4",
                                    justifyContent: "center",
                                    alignItems: "center",
                                    paddingHorizontal: isLast ? 28 : 0,
                                    width: isLast ? undefined : 48,
                                    flexDirection: "row",
                                    gap: 8,
                                }}
                                accessibilityLabel={isLast ? "Finish onboarding" : "Next question"}
                                accessibilityRole="button"
                            >
                                {isLast ? (
                                    <>
                                        <Text style={{ color: "#fff", fontSize: 16, fontFamily: "Inter_600SemiBold" }}>
                                            Done
                                        </Text>
                                        <MaterialIcons name="check" size={20} color="#fff" />
                                    </>
                                ) : (
                                    <MaterialIcons name="arrow-forward-ios" size={18} color="#fff" />
                                )}
                            </TouchableOpacity>
                        </View>
                    </View>
                </View>
            );
        },
        [currentIndex, answers, activeQuestions, dateValue, occupationIndex, otherOccupationText]
    );

    return (
        <SafeAreaView style={{ flex: 1, backgroundColor: "#f8f9fa" }} edges={["top", "bottom"]}>
            <KeyboardAvoidingView
                style={{ flex: 1 }}
                behavior={Platform.OS === "ios" ? "padding" : "height"}
            >
                {/* Header */}
                <View style={{ alignItems: "center", paddingTop: 24, paddingBottom: 8 }}>
                    <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                        <MaterialIcons name="auto-awesome" size={24} color="#4e45e4" />
                        <Text
                            style={{
                                fontSize: 20,
                                fontFamily: "Manrope_700Bold",
                                color: "#2b3437",
                                letterSpacing: -0.3,
                            }}
                        >
                            Let's get to know you
                        </Text>
                    </View>
                    <Text
                        style={{
                            fontSize: 14,
                            fontFamily: "Inter_400Regular",
                            color: "#586064",
                            marginTop: 6,
                        }}
                    >
                        This helps me personalize your experience
                    </Text>
                </View>

                {/* Card Carousel */}
                <View style={{ flex: 1, justifyContent: "center" }} onLayout={onCarouselLayout}>
                    {containerWidth > 0 && (
                        <FlatList
                            ref={flatListRef}
                            data={activeQuestions}
                            renderItem={renderCard}
                            keyExtractor={(item) => item.id}
                            horizontal
                            pagingEnabled
                            scrollEnabled={false}
                            showsHorizontalScrollIndicator={false}
                            getItemLayout={(_, index) => ({
                                length: cardWidth,
                                offset: cardWidth * index,
                                index,
                            })}
                            extraData={currentIndex}
                        />
                    )}
                </View>

                {/* Bottom Progress Bar */}
                <View style={{ width: "100%", paddingHorizontal: 24, paddingBottom: 12 }}>
                    <View
                        style={{
                            height: 6,
                            backgroundColor: "rgba(78, 69, 228, 0.15)",
                            borderRadius: 3,
                            overflow: "hidden",
                        }}
                    >
                        <Animated.View
                            style={{
                                height: "100%",
                                backgroundColor: "#4e45e4",
                                borderRadius: 3,
                                width: `${((currentIndex + 1) / (activeQuestions.length || 1)) * 100}%`,
                            }}
                        />
                    </View>
                </View>

                {/* Skip Link */}
                <View style={{ alignItems: "center", paddingBottom: 16 }}>
                    <TouchableOpacity
                        onPress={handleSkip}
                        accessibilityLabel="Skip onboarding"
                        accessibilityRole="button"
                    >
                        <Text
                            style={{
                                fontSize: 14,
                                fontFamily: "Inter_500Medium",
                                color: "#586064",
                                textDecorationLine: "underline",
                            }}
                        >
                            Skip for now
                        </Text>
                    </TouchableOpacity>
                </View>
            </KeyboardAvoidingView>
        </SafeAreaView>
    );
}
