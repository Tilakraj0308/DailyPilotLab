import React, { useState, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, ScrollView, ActivityIndicator, Keyboard } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialIcons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { supabase } from '../lib/supabase';
import { getApiUrl } from '../lib/api';

import { getCache, setCache } from '../lib/cache';

export default function MemoriesScreen() {
    const navigation = useNavigation<any>();
    const [searchQuery, setSearchQuery] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [traits, setTraits] = useState<any[]>([]);
    const [activeIdeas, setActiveIdeas] = useState<any[]>([]);
    const [searchResults, setSearchResults] = useState<any[]>([]);
    const [isSearching, setIsSearching] = useState(false);

    useEffect(() => {
        if (!searchQuery.trim()) {
            fetchMemories();
        }
    }, [searchQuery]);

    const fetchMemories = async () => {
        try {
            const { data } = await supabase.auth.getSession();
            const token = data?.session?.access_token;
            const userId = data?.session?.user?.id;
            const cacheKey = userId ? `@memories_${userId}` : null;

            if (!token) return;

            if (cacheKey && traits.length === 0 && activeIdeas.length === 0) {
                const cached = await getCache<{ traits: any[]; activeIdeas: any[] }>(cacheKey);
                if (cached) {
                    if (cached.traits) setTraits(cached.traits);
                    if (cached.activeIdeas) setActiveIdeas(cached.activeIdeas);
                } else {
                    setIsLoading(true);
                }
            } else if (traits.length === 0) {
                setIsLoading(true);
            }

            const apiUrl = getApiUrl();
            const [traitsRes, ideasRes] = await Promise.all([
                fetch(`${apiUrl}/users/traits`, { headers: { 'Authorization': `Bearer ${token}` } }),
                fetch(`${apiUrl}/ideas/raw`, { headers: { 'Authorization': `Bearer ${token}` } })
            ]);

            let fetchedTraits = traits;
            let fetchedIdeas = activeIdeas;

            if (traitsRes.ok) {
                const json = await traitsRes.json();
                fetchedTraits = json.traits || [];
                setTraits(fetchedTraits);
            }
            if (ideasRes.ok) {
                const json = await ideasRes.json();
                fetchedIdeas = json.ideas || [];
                setActiveIdeas(fetchedIdeas);
            }

            if (cacheKey) {
                await setCache(cacheKey, { traits: fetchedTraits, activeIdeas: fetchedIdeas });
            }
        } catch (e) {
            console.error("Failed to fetch memories", e);
        }
        setIsLoading(false);
        setIsSearching(false);
    };

    const handleSearch = async () => {
        if (!searchQuery.trim()) {
            return;
        }
        Keyboard.dismiss();
        setIsLoading(true);
        setIsSearching(true);
        try {
            const { data } = await supabase.auth.getSession();
            const token = data?.session?.access_token;
            if (!token) return;

            const apiUrl = getApiUrl();
            const res = await fetch(`${apiUrl}/ideas/search?query=${encodeURIComponent(searchQuery)}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (res.ok) {
                const json = await res.json();
                setSearchResults(json.ideas || []);
            }
        } catch (e) {
            console.error("Failed to search memories", e);
        }
        setIsLoading(false);
    };

    return (
        <SafeAreaView className="flex-1 bg-background" edges={['top']}>
            <View className="flex-row items-center px-5 py-3 border-b border-outline-variant/10 bg-background">
                <TouchableOpacity onPress={() => navigation.goBack()} className="p-1 mr-3">
                    <MaterialIcons name="arrow-back" size={24} color="#2b3437" />
                </TouchableOpacity>
                <Text className="text-lg font-bold text-on-surface" style={{ fontFamily: "Manrope_700Bold" }}>
                    My Memories
                </Text>
            </View>

            <View className="px-4 py-4 border-b border-outline-variant/10 bg-surface">
                <View className="flex-row items-center bg-surface-container rounded-full px-4 h-12 border border-outline-variant/20">
                    <MaterialIcons name="search" size={20} color="#586064" />
                    <TextInput
                        className="flex-1 ml-2 text-sm text-on-surface"
                        placeholder="Search your memories..."
                        placeholderTextColor="#586064"
                        value={searchQuery}
                        onChangeText={setSearchQuery}
                        onSubmitEditing={handleSearch}
                        returnKeyType="search"
                        style={{ fontFamily: "Inter_400Regular" }}
                    />
                    {searchQuery.length > 0 && (
                        <TouchableOpacity onPress={() => setSearchQuery('')}>
                            <MaterialIcons name="close" size={20} color="#586064" />
                        </TouchableOpacity>
                    )}
                </View>
            </View>

            {isLoading ? (
                <View className="flex-1 justify-center items-center">
                    <ActivityIndicator size="large" color="#4e45e4" />
                </View>
            ) : isSearching ? (
                <ScrollView className="flex-1 px-4 py-2" contentContainerStyle={{ paddingBottom: 40 }}>
                    <Text className="text-lg font-bold text-on-surface my-4" style={{ fontFamily: "Manrope_700Bold" }}>Search Results</Text>
                    {searchResults.length === 0 ? (
                        <Text className="text-sm text-on-surface-variant my-4" style={{ fontFamily: "Inter_400Regular" }}>No memories found matching "{searchQuery}".</Text>
                    ) : (
                        searchResults.map((item, idx) => (
                            <View key={idx} className="bg-surface-container/50 p-4 rounded-xl border border-outline-variant/10 mb-3">
                                <Text className="text-sm text-on-surface leading-relaxed" style={{ fontFamily: "Inter_500Medium" }}>{item.content}</Text>
                                {item.status && <Text className="text-xs text-secondary mt-2 capitalize font-bold" style={{ fontFamily: "Inter_600SemiBold" }}>{item.status}</Text>}
                            </View>
                        ))
                    )}
                </ScrollView>
            ) : (
                <ScrollView className="flex-1 px-4 pt-2" contentContainerStyle={{ paddingBottom: 40 }}>

                    <Text className="text-lg font-bold text-on-surface mt-4 mb-3" style={{ fontFamily: "Manrope_700Bold" }}>Long-Term Traits</Text>
                    {traits.length === 0 ? (
                        <Text className="text-sm text-on-surface-variant mb-4" style={{ fontFamily: "Inter_400Regular" }}>No traits learned yet.</Text>
                    ) : (
                        <View className="flex-row flex-wrap gap-2 mb-6">
                            {traits.map((t, idx) => (
                                <View key={idx} className="bg-secondary/10 border border-secondary/20 px-3 py-2 rounded-xl">
                                    <View className="flex-row items-center gap-1 mb-1">
                                        <MaterialIcons name="memory" size={12} color="#4e45e4" />
                                        <Text className="text-xs font-bold text-secondary uppercase" style={{ fontFamily: "Inter_600SemiBold" }}>{t.trait_type}</Text>
                                    </View>
                                    <Text className="text-sm text-on-surface" style={{ fontFamily: "Inter_500Medium" }}>{t.trait_text}</Text>
                                </View>
                            ))}
                        </View>
                    )}

                    <Text className="text-lg font-bold text-on-surface mt-2 mb-3" style={{ fontFamily: "Manrope_700Bold" }}>Active Current Ideas</Text>
                    {activeIdeas.length === 0 ? (
                        <Text className="text-sm text-on-surface-variant mb-4" style={{ fontFamily: "Inter_400Regular" }}>No active ideas in short-term memory.</Text>
                    ) : (
                        activeIdeas.map((idea, idx) => (
                            <View key={idx} className="bg-surface-container border border-outline-variant/10 p-4 rounded-xl mb-3 flex-row items-start gap-3">
                                <View className="mt-1">
                                    <MaterialIcons name="lightbulb-outline" size={18} color="#586064" />
                                </View>
                                <View className="flex-1">
                                    <Text className="text-sm text-on-surface leading-relaxed" style={{ fontFamily: "Inter_500Medium" }}>{idea.content}</Text>
                                    <Text className="text-xs text-on-surface-variant mt-2" style={{ fontFamily: "Inter_400Regular" }}>Extracting to long-term memory soon...</Text>
                                </View>
                            </View>
                        ))
                    )}

                </ScrollView>
            )}
        </SafeAreaView>
    );
}
