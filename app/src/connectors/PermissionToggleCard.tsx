import React from "react";
import { View, Text, Switch, StyleSheet, TouchableOpacity } from "react-native";
import { Eye, Plus, Pencil, Trash2 } from "lucide-react-native";

interface PermissionToggleCardProps {
    crudType: "read" | "create" | "update" | "delete";
    enabled: boolean;
    onToggle: (enabled: boolean) => void;
    disabled?: boolean;
}

const CRUD_INFO = {
    read: {
        title: "Read Data",
        description: "View and list information from this connected service",
        Icon: Eye,
        color: "#6366f1", // Indigo
    },
    create: {
        title: "Create Items",
        description: "Add new data (like creating tasks or events)",
        Icon: Plus,
        color: "#10b981", // Emerald
    },
    update: {
        title: "Update Items",
        description: "Modify existing data (like marking completed)",
        Icon: Pencil,
        color: "#f59e0b", // Amber
    },
    delete: {
        title: "Delete Items",
        description: "Remove data permanently. Use with caution.",
        Icon: Trash2,
        color: "#ef4444", // Red
    },
};

export default function PermissionToggleCard({
    crudType,
    enabled,
    onToggle,
    disabled = false,
}: PermissionToggleCardProps) {
    const info = CRUD_INFO[crudType];
    const Icon = info.Icon;

    const isDelete = crudType === "delete";

    // We use NativeWind classes to match the main app theme.
    const baseClass = "flex-row items-center bg-surface-container-lowest rounded-2xl p-4 mb-3 border shadow-sm";
    const dangerClass = isDelete && enabled
        ? "border-red-200 bg-red-50"
        : "border-outline-variant/15";

    return (
        <View className={`${baseClass} ${dangerClass}`}>
            <View className="w-10 h-10 rounded-xl bg-secondary-container items-center justify-center mr-4">
                <Icon size={20} color={info.color} />
            </View>
            <View className="flex-1 mr-3">
                <Text
                    className="text-base text-on-surface mb-1"
                    style={{ fontFamily: 'Inter_600SemiBold' }}
                >
                    {info.title}
                </Text>
                <Text
                    className="text-sm text-on-surface-variant leading-5"
                    style={{ fontFamily: 'Inter_400Regular' }}
                >
                    {info.description}
                </Text>
            </View>
            <Switch
                value={enabled}
                onValueChange={onToggle}
                disabled={disabled}
                trackColor={{ false: "#e2e8f0", true: isDelete ? "#ef4444" : "#10b981" }}
                thumbColor={"#ffffff"}
            />
        </View>
    );
}
