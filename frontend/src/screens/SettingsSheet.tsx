import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import {
    AvatarInitial,
    ProBadge,
    SectionHeader,
    SettingsRow,
    ToggleRow,
} from '../components';
import { Colors, Typography, Spacing, BorderRadius } from '../theme';

interface SettingsSheetProps {
    visible: boolean;
    onClose: () => void;
    onOpenPersonalize?: () => void;
}

export function SettingsSheet({
    visible,
    onClose,
    onOpenPersonalize,
}: SettingsSheetProps) {
    const insets = useSafeAreaInsets();
    const [calendarReminders, setCalendarReminders] = useState(true);

    if (!visible) {
        return null;
    }

    return (
        <View style={styles.overlay}>
            <TouchableOpacity style={styles.backdrop} onPress={onClose} activeOpacity={1} />
            <View style={[styles.sheet, { paddingBottom: insets.bottom + 20 }]}>
                {/* Handle */}
                <View style={styles.handleRow}>
                    <View style={styles.handle} />
                </View>

                {/* Header */}
                <View style={styles.header}>
                    <Text style={styles.title}>Settings</Text>
                    <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
                        <Text style={styles.closeBtnText}>✕</Text>
                    </TouchableOpacity>
                </View>

                <ScrollView showsVerticalScrollIndicator={false}>
                    {/* User Profile */}
                    <View style={styles.profileSection}>
                        <AvatarInitial initial="G" size={80} />
                        <View style={styles.nameRow}>
                            <Text style={styles.username}>Gsoc</Text>
                            <ProBadge />
                        </View>
                    </View>

                    {/* ACCOUNT Section */}
                    <SectionHeader title="ACCOUNT" />
                    <View style={styles.groupCard}>
                        <SettingsRow
                            label="user@twinmind.com"
                            iconName="mail-outline"
                            showDivider={false}
                            rightElement={null}
                        />
                    </View>

                    {/* SETTINGS Section */}
                    <SectionHeader title="SETTINGS" />
                    <View style={styles.groupCard}>
                        <SettingsRow
                            label="Personalization & Language"
                            iconName="language-outline"
                            onPress={onOpenPersonalize}
                        />
                        <ToggleRow
                            label="Calendar Reminders"
                            subtitle="Get reminded before your upcoming meetings"
                            value={calendarReminders}
                            onValueChange={setCalendarReminders}
                            showDivider={false}
                        />
                    </View>
                    <TouchableOpacity style={styles.linkRow}>
                        <Text style={styles.linkText}>
                            Add Outlook and other calendars
                        </Text>
                    </TouchableOpacity>

                    {/* CONTACT US Section */}
                    <SectionHeader title="CONTACT US" />
                    <View style={styles.groupCard}>
                        <SettingsRow
                            label="Get in Touch with Support"
                            iconName="chatbubble-ellipses-outline"
                        />
                        <SettingsRow label="Discord" iconName="logo-discord" />
                        <SettingsRow label="LinkedIn" iconName="logo-linkedin" />
                        <SettingsRow label="Instagram" iconName="logo-instagram" />
                        <SettingsRow
                            label="X"
                            iconName="logo-twitter"
                            showDivider={false}
                        />
                    </View>

                    {/* Destructive Actions */}
                    <View style={[styles.groupCard, { marginTop: 16 }]}>
                        <SettingsRow
                            label="Delete Account"
                            iconName="warning-outline"
                            destructive
                        />
                        <SettingsRow
                            label="Sign Out"
                            iconName="log-out-outline"
                            destructive
                            showDivider={false}
                        />
                    </View>

                    {/* Footer */}
                    <Text style={styles.footer}>
                        TwinMind · 1.0.86 · Unleashing deeper insights through sound since
                        2024.
                    </Text>
                </ScrollView>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    overlay: {
        ...StyleSheet.absoluteFillObject,
        justifyContent: 'flex-end',
        zIndex: 100,
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
        justifyContent: 'center',
        alignItems: 'center',
        paddingVertical: 12,
        paddingHorizontal: Spacing.lg,
        position: 'relative',
    },
    title: {
        ...Typography.screenTitle,
        color: Colors.textDark,
    },
    closeBtn: {
        position: 'absolute',
        right: Spacing.lg,
        width: 44,
        height: 44,
        justifyContent: 'center',
        alignItems: 'center',
    },
    closeBtnText: {
        fontSize: 18,
        color: Colors.textSubdued,
    },
    profileSection: {
        alignItems: 'center',
        paddingVertical: 16,
    },
    nameRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 12,
        gap: 8,
    },
    username: {
        ...Typography.bodyBold,
        color: Colors.textDark,
        fontSize: 18,
    },
    groupCard: {
        backgroundColor: Colors.white,
        borderRadius: BorderRadius.lg,
        marginHorizontal: Spacing.lg,
        overflow: 'hidden',
    },
    linkRow: {
        paddingHorizontal: Spacing.lg,
        paddingVertical: 10,
    },
    linkText: {
        ...Typography.bodySm,
        color: Colors.primaryMid,
    },
    footer: {
        ...Typography.bodySm,
        color: Colors.textPlaceholder,
        textAlign: 'center',
        paddingVertical: 24,
        paddingHorizontal: Spacing.lg,
        lineHeight: 18,
    },
});
