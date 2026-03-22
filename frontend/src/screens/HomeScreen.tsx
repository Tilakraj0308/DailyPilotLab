import React from 'react';
import {
    View,
    Text,
    ScrollView,
    ImageBackground,
    StyleSheet,
    Dimensions,
    TouchableOpacity,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { PillButton, RoundedCard } from '../components';
import { Colors, Typography, Spacing, BorderRadius } from '../theme';

const { height: SCREEN_HEIGHT } = Dimensions.get('window');
const HERO_HEIGHT = SCREEN_HEIGHT * 0.55;

interface HomeScreenProps {
    onOpenDrawer?: () => void;
    onOpenChat?: () => void;
    onOpenSettings?: () => void;
}

export function HomeScreen({ onOpenDrawer, onOpenChat }: HomeScreenProps) {
    const insets = useSafeAreaInsets();

    return (
        <View style={styles.container}>
            <ScrollView
                style={styles.scrollView}
                contentContainerStyle={{ paddingBottom: 80 }}
                showsVerticalScrollIndicator={false}>
                {/* Hero Section */}
                <ImageBackground
                    source={require('../assets/hero_mountain.png')}
                    style={[styles.heroImage, { paddingTop: insets.top + 8 }]}
                    resizeMode="cover">
                    {/* Top Nav Bar */}
                    <View style={styles.topNav}>
                        <TouchableOpacity
                            onPress={onOpenDrawer}
                            style={styles.hamburgerBtn}
                            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
                            <Icon name="menu" size={28} color={Colors.textDark} />
                        </TouchableOpacity>

                        <PillButton
                            label="View Digest"
                            variant="secondary"
                            size="sm"
                            icon={<Icon name="flash" size={16} color={Colors.primaryMid} />}
                            style={styles.digestBtn}
                        />
                    </View>

                    {/* Greeting */}
                    <View style={styles.greeting}>
                        <Text style={styles.greetingName}>Hey Gsoc!</Text>
                        <Text style={styles.greetingBody}>
                            Do you want me to{'\n'}listen and take notes?
                        </Text>
                        <PillButton
                            label="Capture"
                            variant="primary"
                            size="sm"
                            style={styles.captureBtn}
                        />
                    </View>
                </ImageBackground>

                {/* Content Below Hero */}
                <View style={styles.content}>
                    {/* Chat Entry Row */}
                    <TouchableOpacity
                        style={styles.chatEntryRow}
                        onPress={onOpenChat}
                        activeOpacity={0.7}>
                        <Text style={styles.chatEntryText}>
                            <Text style={{ color: Colors.primaryMid }}>✦ </Text>
                            <Text style={{ color: Colors.textDark }}>Chat with </Text>
                            <Text style={{ color: Colors.orange }}>all your memories</Text>
                        </Text>
                    </TouchableOpacity>

                    {/* Quick Access Cards — 2-column */}
                    <View style={styles.cardRow}>
                        <RoundedCard
                            bgColor={Colors.cardBluGrey}
                            style={styles.quickCard}
                            onPress={() => { }}>
                            <View style={styles.quickCardContent}>
                                <Icon
                                    name="checkbox-outline"
                                    size={28}
                                    color={Colors.primaryDark}
                                    style={styles.quickCardIcon}
                                />
                                <Text style={styles.quickCardTitle}>To-Do</Text>
                                <Text style={styles.quickCardSub}>View Tasks ›</Text>
                            </View>
                        </RoundedCard>

                        <RoundedCard
                            bgColor={Colors.cardPeach}
                            style={styles.quickCard}
                            onPress={() => { }}>
                            <View style={styles.quickCardContent}>
                                <Icon
                                    name="folder-open"
                                    size={28}
                                    color={Colors.orange}
                                    style={styles.quickCardIcon}
                                />
                                <Text style={styles.quickCardTitle}>Notes & Chats</Text>
                                <Text style={styles.quickCardSub}>View Memories ›</Text>
                            </View>
                        </RoundedCard>
                    </View>

                    {/* Coming Up Section */}
                    <Text style={styles.sectionLabel}>Coming Up</Text>
                    <RoundedCard
                        hasBorder
                        hasShadow
                        style={styles.calendarCard}
                        onPress={() => { }}>
                        <View style={styles.calendarRow}>
                            <Icon
                                name="calendar-outline"
                                size={22}
                                color={Colors.primaryMid}
                                style={{ marginRight: 10 }}
                            />
                            <Text style={styles.calendarText}>
                                No upcoming events found{'\n'}
                                <Text style={{ color: Colors.primaryMid }}>
                                    manage your calendars
                                </Text>
                            </Text>
                            <Icon
                                name="chevron-forward"
                                size={18}
                                color={Colors.textPlaceholder}
                            />
                        </View>
                    </RoundedCard>
                </View>
            </ScrollView>

            {/* Sticky Bottom CTA */}
            <View
                style={[styles.bottomBar, { paddingBottom: Math.max(insets.bottom, 16) }]}>
                <PillButton
                    label=" Capture Notes"
                    variant="primary"
                    size="lg"
                    fullWidth
                    icon={<Icon name="mic" size={20} color={Colors.white} />}
                />
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: Colors.white,
    },
    scrollView: {
        flex: 1,
    },
    heroImage: {
        height: HERO_HEIGHT,
        width: '100%',
    },
    topNav: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: Spacing.lg,
        paddingVertical: 8,
    },
    hamburgerBtn: {
        width: 44,
        height: 44,
        justifyContent: 'center',
        alignItems: 'center',
    },
    digestBtn: {
        backgroundColor: 'rgba(255,255,255,0.85)',
        borderColor: Colors.primaryMid,
        borderWidth: 1,
    },
    greeting: {
        paddingHorizontal: Spacing.lg + 4,
        paddingTop: 40,
    },
    greetingName: {
        ...Typography.heroTitle,
        color: Colors.primaryDark,
    },
    greetingBody: {
        ...Typography.heroBody,
        color: Colors.primaryDark,
        marginTop: 4,
    },
    captureBtn: {
        marginTop: 16,
    },
    content: {
        paddingHorizontal: Spacing.lg,
        paddingTop: Spacing.lg,
    },
    chatEntryRow: {
        height: 52,
        borderRadius: BorderRadius.pill,
        backgroundColor: Colors.white,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: Colors.hairlineDivider,
        justifyContent: 'center',
        alignItems: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.05,
        shadowRadius: 6,
        elevation: 2,
    },
    chatEntryText: {
        ...Typography.body,
    },
    cardRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginTop: Spacing.lg,
        gap: 12,
    },
    quickCard: {
        flex: 1,
        minHeight: 100,
        padding: Spacing.lg,
    },
    quickCardContent: {
        flex: 1,
    },
    quickCardIcon: {
        alignSelf: 'flex-end',
    },
    quickCardTitle: {
        ...Typography.bodyBold,
        color: Colors.textDark,
        marginTop: 12,
    },
    quickCardSub: {
        ...Typography.bodySm,
        color: Colors.textSubdued,
        marginTop: 4,
    },
    sectionLabel: {
        ...Typography.caption,
        color: Colors.primaryMid,
        marginTop: 20,
        marginBottom: 8,
    },
    calendarCard: {
        paddingVertical: 14,
        paddingHorizontal: Spacing.lg,
    },
    calendarRow: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    calendarText: {
        ...Typography.bodySm,
        color: Colors.textSubdued,
        flex: 1,
    },
    bottomBar: {
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        paddingHorizontal: Spacing.lg,
        paddingTop: 12,
        backgroundColor: Colors.white,
    },
});
