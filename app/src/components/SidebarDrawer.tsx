import React, { useEffect } from 'react';
import { View, TouchableOpacity, Platform, Dimensions } from 'react-native';
import Animated, { useSharedValue, withTiming } from 'react-native-reanimated';

interface SidebarDrawerProps {
    isOpen: boolean;
    onClose: () => void;
    children: React.ReactNode;
    width?: number;
}

export default function SidebarDrawer({ isOpen, onClose, children, width = 300 }: SidebarDrawerProps) {
    const sidebarX = useSharedValue(-width);

    // Native animation using Reanimated
    useEffect(() => {
        if (Platform.OS !== 'web') {
            sidebarX.value = withTiming(isOpen ? 0 : -width, { duration: 250 });
        }
    }, [isOpen, width]);

    return (
        <>
            {/* Backdrop */}
            {isOpen && (
                <View style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 40, backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <TouchableOpacity
                        style={{ flex: 1 }}
                        activeOpacity={1}
                        onPress={onClose}
                    />
                </View>
            )}

            {/* Drawer */}
            {Platform.OS === 'web' ? (
                <View
                    style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        bottom: 0,
                        width: width,
                        zIndex: 50,
                        backgroundColor: '#ffffff',
                        boxShadow: '4px 0 20px rgba(0,0,0,0.12)' as any,
                        transform: `translateX(${isOpen ? '0px' : `-${width}px`})`,
                        transition: 'transform 250ms cubic-bezier(0.4, 0, 0.2, 1)',
                    } as any}
                >
                    {children}
                </View>
            ) : (
                <Animated.View
                    style={{
                        transform: [{ translateX: sidebarX }],
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        bottom: 0,
                        width: width,
                        zIndex: 50,
                        backgroundColor: '#ffffff',
                        shadowColor: '#000',
                        shadowOffset: { width: 4, height: 0 },
                        shadowOpacity: 0.1,
                        shadowRadius: 10,
                        elevation: 10,
                    }}
                >
                    {children}
                </Animated.View>
            )}
        </>
    );
}
