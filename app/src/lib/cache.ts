import AsyncStorage from '@react-native-async-storage/async-storage';

const memoryCache: Record<string, any> = {};

export async function getCache<T>(key: string): Promise<T | null> {
    if (!key) return null;
    if (memoryCache[key] !== undefined) {
        return memoryCache[key] as T;
    }
    try {
        const stored = await AsyncStorage.getItem(key);
        if (stored) {
            const parsed = JSON.parse(stored);
            memoryCache[key] = parsed;
            return parsed as T;
        }
    } catch (e) {
        console.warn(`Cache read error for key ${key}:`, e);
    }
    return null;
}

export async function setCache<T>(key: string, value: T): Promise<void> {
    if (!key) return;
    memoryCache[key] = value;
    try {
        await AsyncStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
        console.warn(`Cache write error for key ${key}:`, e);
    }
}

export async function removeCache(key: string): Promise<void> {
    if (!key) return;
    delete memoryCache[key];
    try {
        await AsyncStorage.removeItem(key);
    } catch (e) {
        console.warn(`Cache remove error for key ${key}:`, e);
    }
}

export async function clearUserCaches(userId: string): Promise<void> {
    if (!userId) return;
    const prefixes = [
        `@chat_history_${userId}`,
        `@connectors_${userId}`,
        `@gmail_priority_${userId}`,
        `@token_usage_${userId}`,
        `@ai_settings_${userId}`,
        `@memories_${userId}`,
    ];

    // Clear memory cache keys starting with or matching any prefix
    for (const key of Object.keys(memoryCache)) {
        if (key.includes(userId)) {
            delete memoryCache[key];
        }
    }

    try {
        const allKeys = await AsyncStorage.getAllKeys();
        const keysToRemove = allKeys.filter(key => key.includes(userId));
        if (keysToRemove.length > 0) {
            await AsyncStorage.multiRemove(keysToRemove);
        }
    } catch (e) {
        console.warn(`Error clearing user caches for ${userId}:`, e);
    }
}
