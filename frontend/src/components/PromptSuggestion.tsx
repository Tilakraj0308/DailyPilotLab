import React from 'react';
import { TouchableOpacity, Text, StyleSheet } from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { Colors, Typography, Spacing } from '../theme';

interface PromptSuggestionProps {
    text: string;
    onPress?: () => void;
}

export function PromptSuggestion({ text, onPress }: PromptSuggestionProps) {
    return (
        <TouchableOpacity style={styles.row} onPress={onPress} activeOpacity={0.6}>
            <Icon name="return-down-forward" size={18} color={Colors.primaryMid} style={styles.icon} />
            <Text style={styles.text}>{text}</Text>
        </TouchableOpacity>
    );
}

const styles = StyleSheet.create({
    row: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        paddingVertical: 10,
        paddingHorizontal: Spacing.lg,
    },
    icon: {
        marginRight: 10,
        marginTop: 2,
    },
    text: {
        ...Typography.body,
        color: Colors.textSubdued,
        flex: 1,
    },
});
