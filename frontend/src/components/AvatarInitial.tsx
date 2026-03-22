import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, Typography } from '../theme';

interface AvatarInitialProps {
    initial: string;
    bgColor?: string;
    size?: number;
    textColor?: string;
}

export function AvatarInitial({
    initial,
    bgColor = Colors.accent,
    size = 56,
    textColor = Colors.white,
}: AvatarInitialProps) {
    return (
        <View
            style={[
                styles.container,
                {
                    width: size,
                    height: size,
                    borderRadius: size / 2,
                    backgroundColor: bgColor,
                },
            ]}>
            <Text
                style={[
                    styles.text,
                    {
                        color: textColor,
                        fontSize: size * 0.42,
                    },
                ]}>
                {initial}
            </Text>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        alignItems: 'center',
        justifyContent: 'center',
    },
    text: {
        fontWeight: '700',
    },
});
