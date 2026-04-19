import React from "react";
import { View, Text, TouchableOpacity, Modal, Pressable, FlatList, ActivityIndicator } from "react-native";
import { GoogleTaskListItem } from "./api";

interface TaskListPickerProps {
    visible: boolean;
    loading: boolean;
    taskLists: GoogleTaskListItem[];
    isBusy: boolean;
    onPick: (item: GoogleTaskListItem) => void;
    onClose: () => void;
}

export default function TaskListPicker({ visible, loading, taskLists, isBusy, onPick, onClose }: TaskListPickerProps) {
    return (
        <Modal visible={visible} animationType="slide" transparent>
            <Pressable
                className="flex-1 bg-black/50 justify-end"
                onPress={() => !loading && onClose()}
            >
                <Pressable
                    className="bg-surface-container-lowest rounded-t-3xl max-h-[70%] p-4 border-t border-outline-variant/20"
                    onPress={(e) => e.stopPropagation()}
                >
                    <Text className="text-lg text-on-surface mb-3" style={{ fontFamily: "Inter_600SemiBold" }}>
                        Select a task list
                    </Text>
                    {loading ? (
                        <View className="py-12 items-center">
                            <ActivityIndicator color="#4e45e4" />
                        </View>
                    ) : (
                        <FlatList
                            data={taskLists}
                            keyExtractor={(item) => item.id}
                            renderItem={({ item }) => (
                                <TouchableOpacity
                                    onPress={() => onPick(item)}
                                    disabled={isBusy}
                                    className="py-3 border-b border-outline-variant/10"
                                >
                                    <Text className="text-base text-on-surface" style={{ fontFamily: "Inter_500Medium" }}>
                                        {item.title || "(Untitled list)"}
                                    </Text>
                                </TouchableOpacity>
                            )}
                            ListEmptyComponent={
                                <Text className="text-on-surface-variant py-6 text-center">No task lists found.</Text>
                            }
                        />
                    )}
                    <TouchableOpacity
                        onPress={onClose}
                        className="mt-2 py-3 items-center"
                    >
                        <Text className="text-secondary" style={{ fontFamily: "Inter_600SemiBold" }}>
                            Cancel
                        </Text>
                    </TouchableOpacity>
                </Pressable>
            </Pressable>
        </Modal>
    );
}
