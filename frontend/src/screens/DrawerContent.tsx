import React from 'react';
import {
    View,
    Text,
    ScrollView,
    StyleSheet,
    TouchableOpacity,
    Image,
    TextInput,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { AvatarInitial, ProBadge, DrawerMenuItem } from '../components';
import { Colors, Typography, Spacing, BorderRadius } from '../theme';

interface DrawerContentProps {
    onClose?: () => void;
    onOpenPersonalize?: () => void;
    onOpenSettings?: () => void;
}

export function DrawerContent({
    onClose,
    onOpenPersonalize,
    onOpenSettings,
}: DrawerContentProps) {
    const insets = useSafeAreaInsets();

    return (
        <ScrollView
            style={[styles.container, { paddingTop: insets.top + 16 }]}
            contentContainerStyle={{ paddingBottom: insets.bottom + 20 }}
            showsVerticalScrollIndicator={false}>
            {/* User Profile Header */}
            <View style={styles.profileSection}>
                <AvatarInitial initial="G" size={56} />
                <View style={styles.profileInfo}>
                    <View style={styles.nameRow}>
                        <Text style={styles.username}>Gsoc</Text>
                        <ProBadge />
                    </View>
                    <Text style={styles.email}>user@twinmind.com</Text>
                </View>
            </View>

            {/* Search Bar */}
            <View style={styles.searchContainer}>
                <TextInput
                    style={styles.searchInput}
                    placeholder="View Notes & Chats"
                    placeholderTextColor={Colors.textPlaceholder}
                    editable={false}
                />
                <Icon
                    name="search"
                    size={18}
                    color={Colors.textPlaceholder}
                    style={styles.searchIcon}
                />
            </View>

            {/* Menu Items */}
            <View style={styles.menuSection}>
                <DrawerMenuItem
                    label="Personalization & Language"
                    iconName="language-outline"
                    onPress={onOpenPersonalize}
                />
                <DrawerMenuItem
                    label="Contact us on Discord"
                    iconName="logo-discord"
                    onPress={() => { }}
                />
                <DrawerMenuItem
                    label="Get TwinMind "
                    iconName="desktop-outline"
                    accentText="for Desktop"
                    accentColor={Colors.orange}
                    onPress={() => { }}
                />
            </View>

            {/* Referral Banner Card */}
            <View style={styles.referralCard}>
                <View style={styles.referralContent}>
                    <Text style={styles.referralTitle}>
                        Gift TwinMind Pro to a friend to extend your Pro plan
                    </Text>
                    <TouchableOpacity style={styles.referralBtn} activeOpacity={0.7}>
                        <Text style={styles.referralBtnText}>🎁 Give & Get Pro →</Text>
                    </TouchableOpacity>
                </View>
            </View>

            {/* Additional Menu Items */}
            <View style={styles.menuSection}>
                <DrawerMenuItem
                    label="Upload Audio Files"
                    iconName="cloud-upload-outline"
                    onPress={() => { }}
                />
                <DrawerMenuItem
                    label="Settings"
                    iconName="settings-outline"
                    onPress={onOpenSettings}
                    showDivider={false}
                />
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: Colors.offWhite,
    },
    profileSection: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: Spacing.lg,
        marginBottom: 16,
    },
    profileInfo: {
        marginLeft: 12,
        flex: 1,
    },
    nameRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    username: {
        ...Typography.bodyBold,
        color: Colors.textDark,
        fontSize: 18,
    },
    email: {
        ...Typography.bodySm,
        color: Colors.textSubdued,
        marginTop: 2,
    },
    searchContainer: {
        marginHorizontal: Spacing.lg,
        marginBottom: 16,
        position: 'relative',
    },
    searchInput: {
        height: 40,
        backgroundColor: '#EAEAEC',
        borderRadius: BorderRadius.pill,
        paddingHorizontal: 16,
        paddingRight: 40,
        ...Typography.body,
        color: Colors.textBody,
    },
    searchIcon: {
        position: 'absolute',
        right: 14,
        top: 11,
    },
    menuSection: {
        backgroundColor: Colors.white,
        borderRadius: BorderRadius.lg,
        marginHorizontal: Spacing.lg,
        marginBottom: 16,
        overflow: 'hidden',
    },
    referralCard: {
        marginHorizontal: Spacing.lg,
        marginBottom: 16,
        borderRadius: BorderRadius.lg,
        backgroundColor: '#1A1040',
        overflow: 'hidden',
        minHeight: 180,
        justifyContent: 'flex-end',
    },
    referralContent: {
        padding: Spacing.lg,
    },
    referralTitle: {
        ...Typography.bodyBold,
        color: Colors.white,
        fontSize: 17,
        marginBottom: 14,
    },
    referralBtn: {
        backgroundColor: Colors.white,
        borderRadius: BorderRadius.pill,
        paddingVertical: 12,
        alignItems: 'center',
    },
    referralBtnText: {
        ...Typography.buttonMd,
        color: Colors.primaryDark,
    },
});
