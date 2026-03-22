import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Switch } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Colors, Typography, Spacing, BorderRadius } from '../theme';

interface WebSearchSheetProps {
    visible: boolean;
    onClose: () => void;
}

export function WebSearchSheet({ visible, onClose }: WebSearchSheetProps) {
    const insets = useSafeAreaInsets();
    const [webSearchEnabled, setWebSearchEnabled] = useState(true);

    if (!visible) {
        return null;
    }

    return (
        <View style={styles.overlay}>
            <TouchableOpacity
                style={styles.backdrop}
                onPress={onClose}
                activeOpacity={1}
            />
            <View style={[styles.sheet, { paddingBottom: insets.bottom + 20 }]}>
                {/* Handle */}
                <View style={styles.handleRow}>
                    <View style={styles.handle} />
                </View>

                {/* Content */}
                <View style={styles.content}>
                    <View style={styles.row}>
                        <View style={styles.textContainer}>
                            <Text style={styles.title}>Web Search</Text>
                            <Text style={styles.subtitle}>
                                Enable Twinmind to access the web
                            </Text>
                        </View>
                        <Switch
                            value={webSearchEnabled}
                            onValueChange={setWebSearchEnabled}
                            trackColor={{ false: '#D1D1D6', true: Colors.primaryDark }}
                            thumbColor={Colors.white}
                            ios_backgroundColor="#D1D1D6"
                        />
                    </View>
                </View>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    overlay: {
        ...StyleSheet.absoluteFillObject,
        justifyContent: 'flex-end',
        zIndex: 150,
    },
    backdrop: {
        ...StyleSheet.absoluteFillObject,
        backgroundColor: Colors.backdropDim,
    },
    sheet: {
        backgroundColor: Colors.white,
        borderTopLeftRadius: 16,
        borderTopRightRadius: 16,
    },
    handleRow: {
        alignItems: 'center',
        paddingTop: 8,
        paddingBottom: 4,
    },
    handle: {
        width: 36,
        height: 4,
        borderRadius: 2,
        backgroundColor: Colors.hairlineDivider,
    },
    content: {
        padding: Spacing.lg,
        paddingTop: Spacing.md,
    },
    row: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingVertical: 16,
    },
    textContainer: {
        flex: 1,
        marginRight: 16,
    },
    title: {
        ...Typography.bodyBold,
        color: Colors.primaryMid,
        fontSize: 18,
    },
    subtitle: {
        ...Typography.bodySm,
        color: Colors.textSubdued,
        marginTop: 4,
    },
});
