import React from 'react';
import { Text, StyleSheet } from 'react-native';
import { Colors, Typography, Spacing } from '../theme';

interface SectionHeaderProps {
    title: string;
}

export function SectionHeader({ title }: SectionHeaderProps) {
    return <Text style={styles.header}>{title}</Text>;
}

const styles = StyleSheet.create({
    header: {
        ...Typography.sectionHeader,
        color: Colors.sectionHeader,
        paddingHorizontal: Spacing.lg,
        paddingTop: 20,
        paddingBottom: 8,
    },
});
