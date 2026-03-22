import React from 'react';
import { TouchableOpacity, Text, View, StyleSheet } from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { Colors, Typography, Spacing } from '../theme';

interface SettingsRowProps {
    label: string;
    iconName?: string;
    onPress?: () => void;
    showDivider?: boolean;
    destructive?: boolean;
    subtitle?: string;
    rightElement?: React.ReactNode;
}

export function SettingsRow({
    label,
    iconName,
    onPress,
    showDivider = true,
    destructive = false,
    subtitle,
    rightElement,
}: SettingsRowProps) {
    const textColor = destructive ? Colors.destructive : Colors.textBody;
    const iconColor = destructive ? Colors.destructive : Colors.primaryMid;

    return (
        <>
            <TouchableOpacity
                style={styles.row}
                onPress={onPress}
                activeOpacity={0.6}>
                {iconName && (
                    <Icon name={iconName} size={22} color={iconColor} style={styles.icon} />
                )}
                <View style={styles.content}>
                    <Text style={[styles.label, { color: textColor }]}>{label}</Text>
                    {subtitle && (
                        <Text style={styles.subtitle}>{subtitle}</Text>
                    )}
                </View>
                {rightElement || (
                    <Icon name="chevron-forward" size={18} color={Colors.textPlaceholder} />
                )}
            </TouchableOpacity>
            {showDivider && <View style={styles.divider} />}
        </>
    );
}

const styles = StyleSheet.create({
    row: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 14,
        paddingHorizontal: Spacing.lg,
        minHeight: 48,
    },
    icon: {
        marginRight: 12,
        width: 24,
        textAlign: 'center',
    },
    content: {
        flex: 1,
    },
    label: {
        ...Typography.body,
    },
    subtitle: {
        ...Typography.bodySm,
        color: Colors.textPlaceholder,
        marginTop: 2,
    },
    divider: {
        height: StyleSheet.hairlineWidth,
        backgroundColor: Colors.hairlineDivider,
        marginLeft: Spacing.lg,
    },
});
