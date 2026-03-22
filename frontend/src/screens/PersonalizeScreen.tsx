import React, { useState } from 'react';
import {
    View,
    Text,
    ScrollView,
    TextInput,
    Image,
    StyleSheet,
    TouchableOpacity,
    Modal,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { ToggleRow, PillButton } from '../components';
import { Colors, Typography, Spacing, BorderRadius } from '../theme';

interface PersonalizeScreenProps {
    visible: boolean;
    onClose: () => void;
}

export function PersonalizeScreen({ visible, onClose }: PersonalizeScreenProps) {
    const insets = useSafeAreaInsets();
    const [name, setName] = useState('Gsoc');
    const [role, setRole] = useState('');
    const [language, setLanguage] = useState('English');
    const [translateTranscripts, setTranslateTranscripts] = useState(false);
    const [extraContext, setExtraContext] = useState('');
    const [confirmVisible, setConfirmVisible] = useState(false);

    const handleSave = () => {
        setConfirmVisible(true);
    };

    const handleConfirmSave = () => {
        setConfirmVisible(false);
        onClose();
    };

    const handleConfirmCancel = () => {
        setConfirmVisible(false);
    };

    return (
        <Modal visible={visible} animationType="slide" presentationStyle="pageSheet">
            <View style={[styles.container, { paddingTop: insets.top }]}>
                {/* Navigation Bar */}
                <View style={styles.navBar}>
                    <TouchableOpacity onPress={onClose}>
                        <Text style={styles.cancelText}>Cancel</Text>
                    </TouchableOpacity>
                    <Text style={styles.navTitle}>Personalize</Text>
                    <TouchableOpacity onPress={handleSave}>
                        <Text style={styles.saveText}>Save</Text>
                    </TouchableOpacity>
                </View>

                <ScrollView
                    style={styles.scrollView}
                    contentContainerStyle={{ paddingBottom: insets.bottom + 40 }}
                    showsVerticalScrollIndicator={false}>
                    {/* Hero Illustration Card */}
                    <View style={styles.heroCard}>
                        <Image
                            source={require('../assets/personalize_illustration.png')}
                            style={styles.heroImage}
                            resizeMode="cover"
                        />
                        <View style={styles.heroBadges}>
                            <View style={styles.heroBadge}>
                                <Text style={styles.heroBadgeText}>I can be more:</Text>
                            </View>
                            <View style={styles.heroBadge}>
                                <Text style={styles.heroBadgeText}>Relevant</Text>
                            </View>
                            <View style={styles.heroBadge}>
                                <Text style={styles.heroBadgeText}>Personal</Text>
                            </View>
                            <View style={styles.heroBadge}>
                                <Text style={styles.heroBadgeText}>Useful</Text>
                            </View>
                        </View>
                    </View>

                    {/* Description Text */}
                    <Text style={styles.description}>
                        Help TwinMind understand your context better so it can provide more
                        relevant and personalized responses.
                    </Text>

                    {/* Form Fields */}
                    <View style={styles.formSection}>
                        <Text style={styles.fieldLabel}>
                            What should TwinMind call you?
                        </Text>
                        <TextInput
                            style={styles.textInput}
                            value={name}
                            onChangeText={setName}
                            placeholder="Your name"
                            placeholderTextColor={Colors.textPlaceholder}
                        />

                        <Text style={styles.fieldLabel}>What do you do?</Text>
                        <TextInput
                            style={styles.textInput}
                            value={role}
                            onChangeText={setRole}
                            placeholder="Student, engineer, etc"
                            placeholderTextColor={Colors.textPlaceholder}
                        />

                        <Text style={styles.fieldLabel}>
                            Preferred language for summaries and responses
                        </Text>
                        <TextInput
                            style={styles.textInput}
                            value={language}
                            onChangeText={setLanguage}
                            placeholder="English"
                            placeholderTextColor={Colors.textPlaceholder}
                        />
                    </View>

                    {/* Toggle */}
                    <ToggleRow
                        label="Translate Transcripts"
                        value={translateTranscripts}
                        onValueChange={setTranslateTranscripts}
                        trackColor={Colors.primaryDark}
                        showDivider={false}
                    />

                    {/* Extra Context Textarea */}
                    <View style={styles.formSection}>
                        <Text style={styles.fieldLabel}>
                            Anything else TwinMind should know about you?
                        </Text>
                        <TextInput
                            style={[styles.textInput, styles.textArea]}
                            value={extraContext}
                            onChangeText={setExtraContext}
                            placeholder="e.g. I am a product designer at TwinMind, I focus on mobile UX and accessibility…"
                            placeholderTextColor={Colors.textPlaceholder}
                            multiline
                            numberOfLines={4}
                            textAlignVertical="top"
                        />
                    </View>
                </ScrollView>

                {/* Confirmation Modal */}
                <ConfirmationModal
                    visible={confirmVisible}
                    onSave={handleConfirmSave}
                    onCancel={handleConfirmCancel}
                />
            </View>
        </Modal>
    );
}

interface ConfirmationModalProps {
    visible: boolean;
    onSave: () => void;
    onCancel: () => void;
}

function ConfirmationModal({ visible, onSave, onCancel }: ConfirmationModalProps) {
    return (
        <Modal visible={visible} transparent animationType="fade">
            <View style={modalStyles.backdrop}>
                <View style={modalStyles.card}>
                    <Text style={modalStyles.title}>Keep Your Personalization?</Text>
                    <Text style={modalStyles.body}>
                        Your personalization settings will be saved{'\n'}and used across all
                        your conversations.
                    </Text>
                    <PillButton
                        label="Yes, save"
                        variant="primary"
                        size="lg"
                        fullWidth
                        onPress={onSave}
                        style={{ marginTop: 20 }}
                    />
                    <TouchableOpacity onPress={onCancel} style={modalStyles.cancelBtn}>
                        <Text style={modalStyles.cancelText}>No, cancel</Text>
                    </TouchableOpacity>
                </View>
            </View>
        </Modal>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: Colors.white,
    },
    navBar: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: Spacing.lg,
        paddingVertical: 12,
        borderBottomWidth: StyleSheet.hairlineWidth,
        borderBottomColor: Colors.hairlineDivider,
    },
    cancelText: {
        ...Typography.body,
        color: Colors.textSubdued,
    },
    navTitle: {
        ...Typography.screenTitle,
        color: Colors.textDark,
    },
    saveText: {
        ...Typography.body,
        color: Colors.primaryMid,
        fontWeight: '600',
    },
    scrollView: {
        flex: 1,
    },
    heroCard: {
        margin: Spacing.lg,
        borderRadius: BorderRadius.lg,
        overflow: 'hidden',
        height: 250,
        position: 'relative',
    },
    heroImage: {
        width: '100%',
        height: '100%',
    },
    heroBadges: {
        position: 'absolute',
        bottom: 20,
        left: 16,
        gap: 6,
    },
    heroBadge: {
        backgroundColor: 'rgba(255,255,255,0.9)',
        paddingHorizontal: 12,
        paddingVertical: 4,
        borderRadius: BorderRadius.pill,
        alignSelf: 'flex-start',
    },
    heroBadgeText: {
        ...Typography.bodySm,
        color: Colors.primaryDark,
        fontWeight: '500',
    },
    description: {
        ...Typography.body,
        color: Colors.textSubdued,
        paddingHorizontal: Spacing.lg,
        marginBottom: 20,
        lineHeight: 22,
    },
    formSection: {
        paddingHorizontal: Spacing.lg,
    },
    fieldLabel: {
        ...Typography.bodySm,
        color: Colors.textSubdued,
        marginBottom: 6,
        marginTop: 16,
    },
    textInput: {
        ...Typography.body,
        color: Colors.textBody,
        borderBottomWidth: StyleSheet.hairlineWidth,
        borderBottomColor: Colors.hairlineDivider,
        paddingVertical: 10,
    },
    textArea: {
        minHeight: 100,
        borderBottomWidth: 0,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: Colors.hairlineDivider,
        borderRadius: BorderRadius.sm,
        padding: 12,
        marginTop: 4,
    },
});

const modalStyles = StyleSheet.create({
    backdrop: {
        flex: 1,
        backgroundColor: Colors.backdropDim,
        justifyContent: 'center',
        alignItems: 'center',
        paddingHorizontal: 28,
    },
    card: {
        backgroundColor: Colors.white,
        borderRadius: BorderRadius.xl,
        padding: 28,
        width: '100%',
        alignItems: 'center',
    },
    title: {
        ...Typography.heroTitle,
        color: Colors.primaryDark,
        textAlign: 'center',
        marginBottom: 12,
    },
    body: {
        ...Typography.body,
        color: Colors.textSubdued,
        textAlign: 'center',
        lineHeight: 22,
    },
    cancelBtn: {
        marginTop: 16,
        paddingVertical: 8,
    },
    cancelText: {
        ...Typography.body,
        color: Colors.primaryMid,
    },
});
