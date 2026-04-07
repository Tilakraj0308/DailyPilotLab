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

const BAR_COUNT = 35;
const BAR_WIDTH = 4;
const BAR_GAP = 1.5;
const BASE_HEIGHT = 4;
const MAX_HEIGHT = 38;
const BAR_COLOR = '#4e45e4';
const BAR_RADIUS = 1.8;

// dB range for normalization
const DB_MAX = 10;

interface SoundBarsEqualizerProps {
    volumeLevel: SharedValue<number>;
    noiseFloorLevel: SharedValue<number>; // dynamic baseline from calibration
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
export default function SoundBarsEqualizer({ volumeLevel, noiseFloorLevel }: SoundBarsEqualizerProps) {
    // Each bar gets its own shared value for height
    const barHeights: SharedValue<number>[] = [];
    for (let i = 0; i < BAR_COUNT; i++) {
        // eslint-disable-next-line react-hooks/rules-of-hooks
        barHeights.push(useSharedValue(BASE_HEIGHT));
    }

    // Time-based animation — consistent on 60Hz and 120Hz displays
    const elapsedMs = useSharedValue(0);
    const smoothedHeight = useSharedValue(BASE_HEIGHT);
    const SHIFT_INTERVAL_MS = 80; // shift bars every 80ms (~12.5 shifts/sec)
    const LERP_SPEED = 20; // lerp speed per second — higher = snappier reactions

    useFrameCallback((frameInfo) => {
        'worklet';
        const dt = (frameInfo.timeSincePreviousFrame ?? 16) / 1000; // delta in seconds

        // Compute target height from current volume every frame
        const raw = volumeLevel.value;
        const floor = noiseFloorLevel.value;
        const linear = interpolate(
            raw,
            [floor, DB_MAX],
            [0, 0.7],
            Extrapolation.CLAMP,
        );
        // Softer curve — volume changes are more visible while still gradual
        const curved = linear * Math.sqrt(linear);
        const targetHeight = BASE_HEIGHT + (MAX_HEIGHT - BASE_HEIGHT) * curved;

        // Time-adjusted lerp for frame-rate independent smoothing
        const lerpFactor = 1 - Math.pow(Math.E, -LERP_SPEED * dt);
        smoothedHeight.value += (targetHeight - smoothedHeight.value) * lerpFactor;

        // Update the newest bar with smoothed value every frame (keeps it alive)
        barHeights[BAR_COUNT - 1].value = smoothedHeight.value;

        // Shift bars at controlled time intervals
        elapsedMs.value += frameInfo.timeSincePreviousFrame ?? 16;
        if (elapsedMs.value >= SHIFT_INTERVAL_MS) {
            elapsedMs.value -= SHIFT_INTERVAL_MS;

            // Shift all bars one position to the left (streaming right-to-left)
            for (let i = 0; i < BAR_COUNT - 1; i++) {
                barHeights[i].value = barHeights[i + 1].value;
            }
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
