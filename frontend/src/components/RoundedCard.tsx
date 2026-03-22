import React from 'react';
import { TouchableOpacity, StyleSheet, ViewStyle } from 'react-native';
import { Colors, BorderRadius, Spacing } from '../theme';

interface RoundedCardProps {
    children: React.ReactNode;
    bgColor?: string;
    borderRadius?: number;
    onPress?: () => void;
    style?: ViewStyle;
    hasBorder?: boolean;
    hasShadow?: boolean;
}

export function RoundedCard({
    children,
    bgColor = Colors.white,
    borderRadius = BorderRadius.lg,
    onPress,
    style,
    hasBorder = false,
    hasShadow = false,
}: RoundedCardProps) {
    return (
        <TouchableOpacity
            onPress={onPress}
            disabled={!onPress}
            activeOpacity={onPress ? 0.7 : 1}
            style={[
                styles.card,
                { backgroundColor: bgColor, borderRadius },
                hasBorder && styles.border,
                hasShadow && styles.shadow,
                style,
            ]}>
            {children}
        </TouchableOpacity>
    );
}

const styles = StyleSheet.create({
    card: {
        padding: Spacing.lg,
        overflow: 'hidden',
    },
    border: {
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: Colors.hairlineDivider,
    },
    shadow: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.06,
        shadowRadius: 8,
        elevation: 2,
    },
});
