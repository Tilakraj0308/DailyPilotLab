import React, { useState } from "react";
import { View, Text, TouchableOpacity, TextInput, Pressable, ActivityIndicator } from "react-native";
import { MaterialIcons } from "@expo/vector-icons";
import { GoogleTaskApiItem } from "./api";

interface TasksPreviewProps {
    tasks: GoogleTaskApiItem[];
    isBusy: string | null;
    onChangeList: () => void;
    onQuickAdd: (title: string) => void;
    onToggleDone: (task: GoogleTaskApiItem) => void;
    onDelete: (task: GoogleTaskApiItem) => void;
}

export default function TasksPreview({
    tasks,
    isBusy,
    onChangeList,
    onQuickAdd,
    onToggleDone,
    onDelete,
}: TasksPreviewProps) {
    const [quickTitle, setQuickTitle] = useState("");

    const handleAdd = () => {
        onQuickAdd(quickTitle);
        setQuickTitle("");
    };

    return (
        <View className="mb-4 gap-2">
            <TouchableOpacity
                onPress={onChangeList}
                disabled={isBusy !== null}
                className="py-2 flex-row items-center gap-2"
            >
                <MaterialIcons name="edit" size={18} color="#4e45e4" />
                <Text className="text-sm text-secondary" style={{ fontFamily: "Inter_500Medium" }}>
                    Change task list
                </Text>
            </TouchableOpacity>
            <View className="flex-row gap-2 items-center">
                <TextInput
                    className="flex-1 border border-outline-variant/30 rounded-xl px-3 py-2 text-on-surface text-sm"
                    placeholder="Quick add to this list…"
                    placeholderTextColor="#888"
                    value={quickTitle}
                    onChangeText={setQuickTitle}
                    editable={isBusy === null}
                />
                <TouchableOpacity
                    onPress={handleAdd}
                    disabled={isBusy !== null || !quickTitle.trim()}
                    className="px-4 py-2 rounded-xl bg-secondary"
                >
                    {isBusy === "tasks_quick_add" ? (
                        <ActivityIndicator color="#fff" size="small" />
                    ) : (
                        <Text className="text-white text-sm" style={{ fontFamily: "Inter_600SemiBold" }}>
                            Add
                        </Text>
                    )}
                </TouchableOpacity>
            </View>
            {tasks.length > 0 ? (
                <View className="mt-2">
                    <Text
                        className="text-[10px] uppercase text-on-surface-variant mb-2"
                        style={{ fontFamily: "Inter_600SemiBold" }}
                    >
                        In this list
                    </Text>
                    {tasks.map((task) => (
                        <View
                            key={task.id || task.title}
                            className="flex-row items-center justify-between py-2 border-b border-outline-variant/10"
                        >
                            <Pressable onPress={() => onToggleDone(task)} className="flex-row items-center flex-1 gap-2">
                                <MaterialIcons
                                    name={task.status === "completed" ? "check-box" : "check-box-outline-blank"}
                                    size={22}
                                    color="#4e45e4"
                                />
                                <Text
                                    className={`flex-1 text-sm ${task.status === "completed" ? "text-on-surface-variant line-through" : "text-on-surface"}`}
                                    style={{ fontFamily: "Inter_400Regular" }}
                                    numberOfLines={2}
                                >
                                    {task.title || "(untitled)"}
                                </Text>
                            </Pressable>
                            <TouchableOpacity onPress={() => onDelete(task)} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
                                <MaterialIcons name="delete-outline" size={20} color="#ef4444" />
                            </TouchableOpacity>
                        </View>
                    ))}
                </View>
            ) : null}
        </View>
    );
}
