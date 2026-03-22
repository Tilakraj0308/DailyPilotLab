import React from 'react';
import {
    TouchableOpacity,
    Text,
    StyleSheet,
    ViewStyle,
    TextStyle,
    View,
} from 'react-native';
import { Colors, BorderRadius, Typography } from '../theme';

type PillButtonVariant = 'primary' | 'secondary' | 'text';
type PillButtonSize = 'sm' | 'md' | 'lg';

interface PillButtonProps {
    label: string;
    onPress?: () => void;
    variant?: PillButtonVariant;
    size?: PillButtonSize;
    icon?: React.ReactNode;
    iconRight?: React.ReactNode;
    fullWidth?: boolean;
    disabled?: boolean;
    style?: ViewStyle;
    textStyle?: TextStyle;
}

const sizeMap: Record<PillButtonSize, { height: number; px: number; typo: TextStyle }> = {
    sm: { height: 34, px: 14, typo: Typography.buttonSm },
    md: { height: 44, px: 20, typo: Typography.buttonMd },
    lg: { height: 56, px: 24, typo: Typography.buttonLg },
};

export function PillButton({
    label,
    onPress,
    variant = 'primary',
    size = 'md',
    icon,
    iconRight,
    fullWidth = false,
    disabled = false,
    style,
    textStyle,
}: PillButtonProps) {
    const s = sizeMap[size];

    const containerStyle: ViewStyle = {
        height: s.height,
        paddingHorizontal: s.px,
        borderRadius: BorderRadius.pill,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        alignSelf: fullWidth ? 'stretch' : 'flex-start',
        opacity: disabled ? 0.5 : 1,
        ...(variant === 'primary' && { backgroundColor: Colors.primaryDark }),
        ...(variant === 'secondary' && {
            backgroundColor: Colors.white,
            borderWidth: 1,
            borderColor: Colors.primaryMid,
        }),
        ...(variant === 'text' && { backgroundColor: 'transparent' }),
    };

    const labelStyle: TextStyle = {
        ...s.typo,
        ...(variant === 'primary' && { color: Colors.white }),
        ...(variant === 'secondary' && { color: Colors.primaryMid }),
        ...(variant === 'text' && { color: Colors.primaryMid }),
    };

    return (
        <TouchableOpacity
            onPress={onPress}
            disabled={disabled}
            activeOpacity={0.7}
            style={[containerStyle, style]}>
            {icon && <View style={styles.iconLeft}>{icon}</View>}
            <Text style={[labelStyle, textStyle]}>{label}</Text>
            {iconRight && <View style={styles.iconRight}>{iconRight}</View>}
        </TouchableOpacity>
    );
}

const styles = StyleSheet.create({
    iconLeft: {
        marginRight: 6,
    },
    iconRight: {
        marginLeft: 6,
    },
});
