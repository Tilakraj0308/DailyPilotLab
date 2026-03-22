import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, BorderRadius, Typography } from '../theme';

export function ProBadge() {
    return (
        <View style={styles.badge}>
            <Text style={styles.text}>PRO</Text>
        </View>
    );
}

const styles = StyleSheet.create({
    badge: {
        backgroundColor: Colors.primaryDark,
        paddingHorizontal: 8,
        paddingVertical: 2,
        borderRadius: 9,
        alignSelf: 'flex-start',
    },
    text: {
        ...Typography.badge,
        color: Colors.white,
    },
});
