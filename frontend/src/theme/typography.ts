import { TextStyle } from 'react-native';

export const Typography: Record<string, TextStyle> = {
    // Headings
    heroTitle: {
        fontSize: 28,
        fontWeight: '700',
        letterSpacing: -0.5,
    },
    heroBody: {
        fontSize: 20,
        fontWeight: '600',
        letterSpacing: -0.3,
    },
    screenTitle: {
        fontSize: 18,
        fontWeight: '600',
    },

    // Body
    body: {
        fontSize: 16,
        fontWeight: '400',
    },
    bodyBold: {
        fontSize: 16,
        fontWeight: '600',
    },
    bodySm: {
        fontSize: 14,
        fontWeight: '400',
    },

    // Captions & Labels
    caption: {
        fontSize: 13,
        fontWeight: '500',
    },
    sectionHeader: {
        fontSize: 11,
        fontWeight: '600',
        letterSpacing: 1,
        textTransform: 'uppercase',
    },
    badge: {
        fontSize: 11,
        fontWeight: '700',
        textTransform: 'uppercase',
    },

    // Buttons
    buttonLg: {
        fontSize: 17,
        fontWeight: '600',
    },
    buttonMd: {
        fontSize: 15,
        fontWeight: '600',
    },
    buttonSm: {
        fontSize: 13,
        fontWeight: '600',
    },
} as const;
