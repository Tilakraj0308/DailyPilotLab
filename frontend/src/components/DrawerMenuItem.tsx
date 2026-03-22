import React from 'react';
import { TouchableOpacity, Text, View, StyleSheet } from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { Colors, Typography, Spacing } from '../theme';

interface DrawerMenuItemProps {
    label: string;
    iconName: string;
    onPress?: () => void;
    showDivider?: boolean;
    showChevron?: boolean;
    labelColor?: string;
    accentText?: string;
    accentColor?: string;
}

export function DrawerMenuItem({
    label,
    iconName,
    onPress,
    showDivider = true,
    showChevron = false,
    labelColor = Colors.textDark,
    accentText,
    accentColor = Colors.orange,
}: DrawerMenuItemProps) {
    return (
        <>
            <TouchableOpacity
                style={styles.row}
                onPress={onPress}
                activeOpacity={0.6}>
                <Icon name={iconName} size={22} color={Colors.primaryMid} style={styles.icon} />
                <Text style={[styles.label, { color: labelColor }]}>
                    {label}
                    {accentText && (
                        <Text style={{ color: accentColor }}>{accentText}</Text>
                    )}
                </Text>
                {showChevron && (
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
    },
    icon: {
        marginRight: 12,
        width: 24,
        textAlign: 'center',
    },
    label: {
        ...Typography.body,
        flex: 1,
    },
    divider: {
        height: StyleSheet.hairlineWidth,
        backgroundColor: Colors.hairlineDivider,
        marginLeft: 52,
    },
});
