import React, { useState } from 'react';
import {
    View,
    Text,
    TextInput,
    StyleSheet,
    TouchableOpacity,
    Modal,
    KeyboardAvoidingView,
    Platform,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { PromptSuggestion } from '../components';
import { Colors, Typography, Spacing, BorderRadius } from '../theme';

interface ChatScreenProps {
    visible: boolean;
    onClose: () => void;
    onOpenModelSelect?: () => void;
}

export function ChatScreen({
    visible,
    onClose,
    onOpenModelSelect,
}: ChatScreenProps) {
    const insets = useSafeAreaInsets();
    const [message, setMessage] = useState('');
    const [memoriesEnabled, setMemoriesEnabled] = useState(true);

    const suggestions = [
        'Prioritize things I need to do today',
        'Prepare me for my next meeting',
        'Recap memorable moments of the week',
    ];

    return (
        <Modal visible={visible} animationType="slide" presentationStyle="pageSheet">
            <KeyboardAvoidingView
                style={styles.container}
                behavior={Platform.OS === 'ios' ? 'padding' : undefined}
                keyboardVerticalOffset={0}>
                <View style={[styles.inner, { paddingTop: insets.top }]}>
                    {/* Navigation Bar */}
                    <View style={styles.navBar}>
                        <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
                            <Text style={styles.closeBtnText}>✕</Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                            onPress={onOpenModelSelect}
                            style={styles.modelSelector}>
                            <Text style={styles.modelSelectorText}>Auto Select</Text>
                            <Icon
                                name="chevron-down"
                                size={16}
                                color={Colors.primaryMid}
                            />
                        </TouchableOpacity>
                        <View style={{ width: 44 }} />
                    </View>

                    {/* Conversation Area (Empty) */}
                    <View style={styles.conversationArea}>
                        {/* Prompt Suggestions at bottom of conversation area */}
                        <View style={styles.suggestionsContainer}>
                            {suggestions.map((s, i) => (
                                <PromptSuggestion
                                    key={i}
                                    text={s}
                                    onPress={() => setMessage(s)}
                                />
                            ))}
                        </View>
                    </View>

                    {/* Chat Input Bar */}
                    <View
                        style={[
                            styles.inputBar,
                            { paddingBottom: Math.max(insets.bottom, 12) },
                        ]}>
                        <View style={styles.inputRow}>
                            {/* Attach Button */}
                            <TouchableOpacity style={styles.attachBtn}>
                                <Icon name="add" size={22} color={Colors.textSubdued} />
                            </TouchableOpacity>

                            {/* Memories Toggle */}
                            <TouchableOpacity
                                style={[
                                    styles.memoriesToggle,
                                    memoriesEnabled && styles.memoriesToggleActive,
                                ]}
                                onPress={() => setMemoriesEnabled(!memoriesEnabled)}>
                                <Text
                                    style={[
                                        styles.memoriesText,
                                        memoriesEnabled && styles.memoriesTextActive,
                                    ]}>
                                    Memories
                                </Text>
                                <View
                                    style={[
                                        styles.memoriesDot,
                                        {
                                            backgroundColor: memoriesEnabled
                                                ? Colors.primaryMid
                                                : Colors.textPlaceholder,
                                        },
                                    ]}
                                />
                            </TouchableOpacity>

                            {/* Text Input */}
                            <View style={styles.textInputContainer}>
                                <TextInput
                                    style={styles.textInput}
                                    placeholder="Ask TwinMind…"
                                    placeholderTextColor={Colors.textPlaceholder}
                                    value={message}
                                    onChangeText={setMessage}
                                    multiline={false}
                                />
                            </View>

                            {/* Mic Button */}
                            <TouchableOpacity style={styles.iconBtn}>
                                <Icon name="mic-outline" size={22} color={Colors.textSubdued} />
                            </TouchableOpacity>

                            {/* Send Button */}
                            <TouchableOpacity style={styles.sendBtn}>
                                <Icon
                                    name="arrow-up"
                                    size={20}
                                    color={Colors.white}
                                />
                            </TouchableOpacity>
                        </View>
                    </View>
                </View>
            </KeyboardAvoidingView>
        </Modal>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: Colors.chatBg,
    },
    inner: {
        flex: 1,
    },
    navBar: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: Spacing.lg,
        paddingVertical: 10,
        backgroundColor: Colors.white,
        borderBottomWidth: StyleSheet.hairlineWidth,
        borderBottomColor: Colors.hairlineDivider,
    },
    closeBtn: {
        width: 44,
        height: 44,
        justifyContent: 'center',
        alignItems: 'center',
    },
    closeBtnText: {
        fontSize: 18,
        color: Colors.textSubdued,
    },
    modelSelector: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
    },
    modelSelectorText: {
        ...Typography.buttonMd,
        color: Colors.primaryMid,
    },
    conversationArea: {
        flex: 1,
        justifyContent: 'flex-end',
        paddingBottom: 16,
    },
    suggestionsContainer: {
        paddingBottom: 8,
    },
    inputBar: {
        backgroundColor: Colors.white,
        paddingTop: 10,
        paddingHorizontal: 10,
        borderTopWidth: StyleSheet.hairlineWidth,
        borderTopColor: Colors.hairlineDivider,
    },
    inputRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
    },
    attachBtn: {
        width: 36,
        height: 36,
        borderRadius: 18,
        borderWidth: 1,
        borderColor: Colors.hairlineDivider,
        justifyContent: 'center',
        alignItems: 'center',
    },
    memoriesToggle: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 10,
        paddingVertical: 6,
        borderRadius: BorderRadius.pill,
        borderWidth: 1,
        borderColor: Colors.hairlineDivider,
        gap: 4,
    },
    memoriesToggleActive: {
        borderColor: Colors.primaryMid,
    },
    memoriesText: {
        ...Typography.bodySm,
        color: Colors.textSubdued,
        fontSize: 12,
    },
    memoriesTextActive: {
        color: Colors.textDark,
    },
    memoriesDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
    },
    textInputContainer: {
        flex: 1,
        height: 36,
        borderRadius: BorderRadius.pill,
        borderWidth: 1,
        borderColor: Colors.hairlineDivider,
        justifyContent: 'center',
        paddingHorizontal: 12,
    },
    textInput: {
        ...Typography.bodySm,
        color: Colors.textBody,
        padding: 0,
    },
    iconBtn: {
        width: 36,
        height: 36,
        justifyContent: 'center',
        alignItems: 'center',
    },
    sendBtn: {
        width: 32,
        height: 32,
        borderRadius: 16,
        backgroundColor: Colors.primaryMid,
        justifyContent: 'center',
        alignItems: 'center',
    },
});
