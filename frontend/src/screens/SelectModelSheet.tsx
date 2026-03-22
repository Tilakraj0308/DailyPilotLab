import React from 'react';
import {
    View,
    Text,
    ScrollView,
    StyleSheet,
    TouchableOpacity,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { SectionHeader } from '../components';
import { Colors, Typography, Spacing, BorderRadius } from '../theme';

interface Model {
    name: string;
    isPremium?: boolean;
    subtitle?: string;
    icon?: string;
}

interface ModelSection {
    header: string;
    models: Model[];
}

const MODEL_DATA: ModelSection[] = [
    {
        header: 'TWINMIND',
        models: [
            { name: 'TwinMind Auto', subtitle: 'Recommended', icon: '🧠' },
        ],
    },
    {
        header: 'GOOGLE',
        models: [
            { name: 'Gemini 3.1 Pro', isPremium: true },
            { name: 'Gemini 3 Pro', isPremium: true },
            { name: 'Gemini 3 Flash', isPremium: true },
            { name: 'Gemini 2.5 Pro' },
        ],
    },
    {
        header: 'OPENAI',
        models: [
            { name: 'ChatGPT-5.2', isPremium: true },
            { name: 'ChatGPT-5.1' },
            { name: 'ChatGPT o3' },
        ],
    },
    {
        header: 'ANTHROPIC',
        models: [
            { name: 'Claude Opus 4.6', isPremium: true },
            { name: 'Claude Sonnet 4.5', isPremium: true },
        ],
    },
];

interface SelectModelSheetProps {
    visible: boolean;
    onClose: () => void;
    onSelectModel?: (model: string) => void;
}

export function SelectModelSheet({
    visible,
    onClose,
    onSelectModel,
}: SelectModelSheetProps) {
    const insets = useSafeAreaInsets();

    if (!visible) {
        return null;
    }

    return (
        <View style={styles.overlay}>
            <TouchableOpacity
                style={styles.backdrop}
                onPress={onClose}
                activeOpacity={1}
            />
            <View style={[styles.sheet, { paddingBottom: insets.bottom + 20 }]}>
                {/* Handle */}
                <View style={styles.handleRow}>
                    <View style={styles.handle} />
                </View>

                {/* Header */}
                <View style={styles.header}>
                    <View style={{ width: 60 }} />
                    <Text style={styles.title}>Select Model</Text>
                    <TouchableOpacity onPress={onClose} style={styles.doneBtn}>
                        <Text style={styles.doneText}>Done</Text>
                    </TouchableOpacity>
                </View>

                <ScrollView
                    showsVerticalScrollIndicator={false}
                    contentContainerStyle={{ paddingBottom: 20 }}>
                    {MODEL_DATA.map((section, si) => (
                        <View key={si}>
                            <SectionHeader title={section.header} />
                            <View style={styles.groupCard}>
                                {section.models.map((model, mi) => (
                                    <View key={mi}>
                                        <TouchableOpacity
                                            style={styles.modelRow}
                                            onPress={() => onSelectModel?.(model.name)}
                                            activeOpacity={0.6}>
                                            {model.icon && (
                                                <Text style={styles.modelIcon}>{model.icon}</Text>
                                            )}
                                            <View style={styles.modelInfo}>
                                                <Text style={styles.modelName}>
                                                    {model.name}
                                                    {model.isPremium && (
                                                        <Text style={styles.sparkle}> ✦</Text>
                                                    )}
                                                </Text>
                                                {model.subtitle && (
                                                    <Text style={styles.modelSub}>{model.subtitle}</Text>
                                                )}
                                            </View>
                                        </TouchableOpacity>
                                        {mi < section.models.length - 1 && (
                                            <View style={styles.divider} />
                                        )}
                                    </View>
                                ))}
                            </View>
                        </View>
                    ))}
                </ScrollView>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    overlay: {
        ...StyleSheet.absoluteFillObject,
        justifyContent: 'flex-end',
        zIndex: 200,
    },
    backdrop: {
        ...StyleSheet.absoluteFillObject,
        backgroundColor: Colors.backdropDim,
    },
    sheet: {
        backgroundColor: Colors.offWhite,
        borderTopLeftRadius: 16,
        borderTopRightRadius: 16,
        maxHeight: '90%',
    },
    handleRow: {
        alignItems: 'center',
        paddingTop: 8,
        paddingBottom: 4,
    },
    handle: {
        width: 36,
        height: 4,
        borderRadius: 2,
        backgroundColor: Colors.hairlineDivider,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 12,
        paddingHorizontal: Spacing.lg,
    },
    title: {
        ...Typography.screenTitle,
        color: Colors.textDark,
    },
    doneBtn: {
        width: 60,
        alignItems: 'flex-end',
    },
    doneText: {
        ...Typography.body,
        color: Colors.primaryMid,
        fontWeight: '600',
    },
    groupCard: {
        backgroundColor: Colors.white,
        borderRadius: BorderRadius.lg,
        marginHorizontal: Spacing.lg,
        overflow: 'hidden',
    },
    modelRow: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 14,
        paddingHorizontal: Spacing.lg,
        minHeight: 48,
    },
    modelIcon: {
        fontSize: 20,
        marginRight: 10,
    },
    modelInfo: {
        flex: 1,
    },
    modelName: {
        ...Typography.bodyBold,
        color: Colors.textBody,
    },
    sparkle: {
        color: '#DAA520',
        fontSize: 14,
    },
    modelSub: {
        ...Typography.bodySm,
        color: Colors.textPlaceholder,
        marginTop: 1,
    },
    divider: {
        height: StyleSheet.hairlineWidth,
        backgroundColor: Colors.hairlineDivider,
        marginLeft: Spacing.lg,
    },
});
