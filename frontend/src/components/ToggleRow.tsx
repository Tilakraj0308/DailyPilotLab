import React from 'react';
import { View, Text, Switch, StyleSheet } from 'react-native';
import { Colors, Typography, Spacing } from '../theme';

interface ToggleRowProps {
    label: string;
    subtitle?: string;
    value: boolean;
    onValueChange: (val: boolean) => void;
    trackColor?: string;
    showDivider?: boolean;
}

export function ToggleRow({
    label,
    subtitle,
    value,
    onValueChange,
    trackColor = Colors.toggleGreen,
    showDivider = true,
}: ToggleRowProps) {
    return (
        <>
            <View style={styles.row}>
                <View style={styles.textContainer}>
                    <Text style={styles.label}>{label}</Text>
                    {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
                </View>
                <Switch
                    value={value}
                    onValueChange={onValueChange}
                    trackColor={{ false: '#D1D1D6', true: trackColor }}
                    thumbColor={Colors.white}
                    ios_backgroundColor="#D1D1D6"
                />
            </View>
            {showDivider && <View style={styles.divider} />}
        </>
    );
}

const styles = StyleSheet.create({
    row: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingVertical: 14,
        paddingHorizontal: Spacing.lg,
        minHeight: 48,
    },
    textContainer: {
        flex: 1,
        marginRight: 12,
    },
    label: {
        ...Typography.body,
        color: Colors.textBody,
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
