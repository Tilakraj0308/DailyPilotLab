import React, { useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import Animated, {
    SharedValue,
    useSharedValue,
    useAnimatedStyle,
    useFrameCallback,
    interpolate,
    Extrapolation,
} from 'react-native-reanimated';

const BAR_COUNT = 50;
const BAR_WIDTH = 2.5;
const BAR_GAP = 1.5;
const BASE_HEIGHT = 4;
const MAX_HEIGHT = 36;
const BAR_COLOR = '#4e45e4';
const BAR_RADIUS = 1.5;

// dB range for normalization
const DB_MIN = -60;
const DB_MAX = 0;

interface SoundBarsEqualizerProps {
    volumeLevel: SharedValue<number>;
}

/**
 * A single animated bar whose height is driven by a shared value.
 */
function AnimatedBar({ height }: { height: SharedValue<number> }) {
    const animatedStyle = useAnimatedStyle(() => {
        return {
            height: height.value,
        };
    });

    return (
        <Animated.View
            style={[
                styles.bar,
                animatedStyle,
            ]}
        />
    );
}

/**
 * Sound-reactive equalizer with 35 vertical bars that stream left-to-right.
 * All animation runs on the UI thread via worklets for 60fps performance.
 */
export default function SoundBarsEqualizer({ volumeLevel }: SoundBarsEqualizerProps) {
    // Each bar gets its own shared value for height
    const barHeights: SharedValue<number>[] = [];
    for (let i = 0; i < BAR_COUNT; i++) {
        // eslint-disable-next-line react-hooks/rules-of-hooks
        barHeights.push(useSharedValue(BASE_HEIGHT));
    }

    // Frame counter to control shift speed (shift every N frames for visible streaming)
    const frameCounter = useSharedValue(0);
    const SHIFT_EVERY_N_FRAMES = 5; // shift every 5 frames (~12 shifts/sec at 60fps)

    useFrameCallback(() => {
        'worklet';
        frameCounter.value += 1;

        if (frameCounter.value >= SHIFT_EVERY_N_FRAMES) {
            frameCounter.value = 0;

            // Shift all bars one position to the left (streaming right-to-left)
            for (let i = 0; i < BAR_COUNT - 1; i++) {
                barHeights[i].value = barHeights[i + 1].value;
            }

            // Compute the newest bar height from current volume
            const raw = volumeLevel.value;
            const linear = interpolate(
                raw,
                [DB_MIN, DB_MAX],
                [0, 1],
                Extrapolation.CLAMP,
            );
            // Exponential curve — bars need significantly louder audio to grow tall
            const curved = linear * linear * Math.sqrt(linear); // ~power of 2.5
            barHeights[BAR_COUNT - 1].value = BASE_HEIGHT + (MAX_HEIGHT - BASE_HEIGHT) * curved;
        }
    });

    return (
        <View style={styles.container}>
            {barHeights.map((h, i) => (
                <AnimatedBar key={i} height={h} />
            ))}
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: BAR_GAP,
        flex: 1,
        paddingHorizontal: 4,
        height: '100%',
    },
    bar: {
        width: BAR_WIDTH,
        backgroundColor: BAR_COLOR,
        borderRadius: BAR_RADIUS,
    },
});
