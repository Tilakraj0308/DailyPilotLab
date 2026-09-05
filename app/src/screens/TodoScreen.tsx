import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
    View,
    Text,
    TouchableOpacity,
    ScrollView,
    TextInput,
    ActivityIndicator,
    Alert,
    Animated,
    KeyboardAvoidingView,
    Platform,
    RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialIcons, Feather } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import {
    getTasks,
    createTask,
    updateTask,
    deleteTask,
    Task,
    TaskFilter,
    TaskPriority,
    TaskStatus,
} from '../lib/tasksApi';

// ── Types ────────────────────────────────────────────────────────────────────

interface FilterTab {
    key: TaskFilter;
    label: string;
}

const FILTERS: FilterTab[] = [
    { key: 'all', label: 'All' },
    { key: 'due_today', label: 'Today' },
    { key: 'in_progress', label: 'In Progress' },
    { key: 'high_priority', label: 'Priority' },
];

const PRIORITY_COLORS: Record<TaskPriority, string> = {
    low: '#94a3b8',
    medium: '#f59e0b',
    high: '#f97316',
    urgent: '#ef4444',
};

const PRIORITY_BG: Record<TaskPriority, string> = {
    low: '#f1f5f9',
    medium: '#fef3c7',
    high: '#ffedd5',
    urgent: '#fee2e2',
};

const STATUS_NEXT: Record<TaskStatus, TaskStatus> = {
    todo: 'in_progress',
    in_progress: 'done',
    done: 'todo',
    cancelled: 'todo',
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatDueDate(due?: string): string | null {
    if (!due) return null;
    const d = new Date(due);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const dDay = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    const diff = Math.round((dDay.getTime() - today.getTime()) / 86400000);
    if (diff === 0) return 'Due today';
    if (diff === 1) return 'Due tomorrow';
    if (diff === -1) return 'Yesterday';
    if (diff < 0) return `${Math.abs(diff)}d overdue`;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function isOverdue(due?: string, status?: TaskStatus): boolean {
    if (!due || status === 'done' || status === 'cancelled') return false;
    return new Date(due) < new Date();
}

// ── Sub-components ───────────────────────────────────────────────────────────

function TaskCard({
    task,
    onToggleStatus,
    onEdit,
    onDelete,
}: {
    task: Task;
    onToggleStatus: (t: Task) => void;
    onEdit: (t: Task) => void;
    onDelete: (t: Task) => void;
}) {
    const overdue = isOverdue(task.due_date, task.status);
    const dueDateLabel = formatDueDate(task.due_date);
    const isDone = task.status === 'done';

    return (
        <View className={`bg-white rounded-2xl p-4 mb-3 shadow-sm border ${overdue ? 'border-red-200' : 'border-transparent'}`}>
            <View className="flex-row items-start gap-3">
                {/* Status toggle */}
                <TouchableOpacity
                    className={`w-6 h-6 rounded-full border-2 mt-0.5 items-center justify-center flex-shrink-0 ${isDone ? 'bg-[#35436b] border-[#35436b]' : task.status === 'in_progress' ? 'border-amber-500 bg-amber-50' : 'border-gray-300'}`}
                    onPress={() => onToggleStatus(task)}
                    hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                >
                    {isDone && <MaterialIcons name="check" size={14} color="#fff" />}
                    {task.status === 'in_progress' && <View className="w-2.5 h-2.5 rounded-full bg-amber-500" />}
                </TouchableOpacity>

                {/* Content */}
                <View className="flex-1">
                    <Text
                        className={`text-[15px] leading-snug ${isDone ? 'text-gray-400 line-through' : 'text-[#2b3437]'}`}
                        style={{ fontFamily: isDone ? 'Inter_400Regular' : 'Inter_500Medium' }}
                        numberOfLines={2}
                    >
                        {task.title}
                    </Text>
                    {task.description ? (
                        <Text
                            className="text-xs text-[#586064] mt-1 leading-relaxed"
                            style={{ fontFamily: 'Inter_400Regular' }}
                            numberOfLines={2}
                        >
                            {task.description}
                        </Text>
                    ) : null}
                    <View className="flex-row items-center gap-2 mt-2 flex-wrap">
                        {/* Priority badge */}
                        <View
                            className="px-2 py-0.5 rounded-full"
                            style={{ backgroundColor: PRIORITY_BG[task.priority] }}
                        >
                            <Text
                                className="text-[10px] font-semibold capitalize"
                                style={{ color: PRIORITY_COLORS[task.priority], fontFamily: 'Inter_600SemiBold' }}
                            >
                                {task.priority}
                            </Text>
                        </View>
                        {/* Due date */}
                        {dueDateLabel && (
                            <View className="flex-row items-center gap-0.5">
                                <MaterialIcons
                                    name="schedule"
                                    size={11}
                                    color={overdue ? '#ef4444' : '#94a3b8'}
                                />
                                <Text
                                    className="text-[11px]"
                                    style={{ color: overdue ? '#ef4444' : '#94a3b8', fontFamily: 'Inter_400Regular' }}
                                >
                                    {dueDateLabel}
                                </Text>
                            </View>
                        )}
                    </View>
                </View>

                {/* Action buttons */}
                <View style={{ flexDirection: 'row', gap: 6, alignItems: 'center' }}>
                    <TouchableOpacity
                        style={{
                            width: 34,
                            height: 34,
                            borderRadius: 10,
                            backgroundColor: '#f1f5f9',
                            alignItems: 'center',
                            justifyContent: 'center',
                        }}
                        onPress={() => onEdit(task)}
                    >
                        <Feather name="edit-2" size={16} color="#35436b" />
                    </TouchableOpacity>
                    <TouchableOpacity
                        style={{
                            width: 34,
                            height: 34,
                            borderRadius: 10,
                            backgroundColor: '#fff0f0',
                            alignItems: 'center',
                            justifyContent: 'center',
                        }}
                        onPress={() => onDelete(task)}
                    >
                        <Feather name="trash-2" size={16} color="#ef4444" />
                    </TouchableOpacity>
                </View>
            </View>
        </View>
    );
}

// ── Task Form Sheet (inline, no Modal — works correctly on web+native) ────────

const PRIORITY_OPTIONS: { key: TaskPriority; label: string; color: string; bg: string }[] = [
    { key: 'low', label: 'Low', color: '#64748b', bg: '#eef0f3' },
    { key: 'medium', label: 'Medium', color: '#d97706', bg: '#fef3c7' },
    { key: 'high', label: 'High', color: '#ea580c', bg: '#ffedd5' },
    { key: 'urgent', label: 'Urgent', color: '#dc2626', bg: '#fee2e2' },
];

const QUICK_DATES = [
    { label: 'Today', offset: 0 },
    { label: 'Tomorrow', offset: 1 },
    { label: 'In 3 days', offset: 3 },
    { label: 'Next week', offset: 7 },
];

function TaskFormSheet({
    visible,
    task,
    onClose,
    onSave,
}: {
    visible: boolean;
    task: Task | null;
    onClose: () => void;
    onSave: (data: any) => Promise<void>;
}) {
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [priority, setPriority] = useState<TaskPriority>('medium');
    const [dueDate, setDueDate] = useState('');
    const [saving, setSaving] = useState(false);
    const slideAnim = useRef(new Animated.Value(500)).current;
    const fadeAnim = useRef(new Animated.Value(0)).current;
    const isHidden = useRef(true);

    // Sync form fields when task/visible changes
    useEffect(() => {
        if (task) {
            setTitle(task.title);
            setDescription(task.description || '');
            setPriority(task.priority);
            setDueDate(task.due_date ? task.due_date.split('T')[0] : '');
        } else {
            setTitle('');
            setDescription('');
            setPriority('medium');
            setDueDate('');
        }
    }, [task, visible]);

    // Slide in/out animation
    useEffect(() => {
        if (visible) {
            isHidden.current = false;
            Animated.parallel([
                Animated.spring(slideAnim, { toValue: 0, useNativeDriver: true, damping: 22, stiffness: 220 }),
                Animated.timing(fadeAnim, { toValue: 1, duration: 180, useNativeDriver: true }),
            ]).start();
        } else {
            Animated.parallel([
                Animated.timing(slideAnim, { toValue: 500, duration: 200, useNativeDriver: true }),
                Animated.timing(fadeAnim, { toValue: 0, duration: 180, useNativeDriver: true }),
            ]).start(() => { isHidden.current = true; });
        }
    }, [visible]);

    const handleSave = async () => {
        if (!title.trim()) return;
        setSaving(true);
        try {
            await onSave({
                title: title.trim(),
                description: description.trim() || undefined,
                priority,
                due_date: dueDate ? new Date(dueDate + 'T00:00:00').toISOString() : undefined,
            });
            onClose();
        } catch {
            Alert.alert('Error', 'Failed to save task. Please try again.');
        }
        setSaving(false);
    };

    const getChipDate = (offset: number) => {
        const d = new Date();
        d.setDate(d.getDate() + offset);
        return d.toISOString().split('T')[0];
    };

    const formattedDue = dueDate
        ? new Date(dueDate + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
        : null;

    if (!visible && isHidden.current) return null;

    return (
        <View style={{ position: 'absolute', inset: 0, zIndex: 50 } as any} pointerEvents={visible ? 'auto' : 'none'}>
            {/* Backdrop */}
            <Animated.View
                style={{ position: 'absolute', inset: 0, backgroundColor: 'rgba(20,28,40,0.5)' } as any}
                pointerEvents={visible ? 'auto' : 'none'}
            >
                <TouchableOpacity style={{ flex: 1 }} activeOpacity={1} onPress={onClose} />
            </Animated.View>

            {/* Sheet */}
            <KeyboardAvoidingView
                behavior={Platform.OS === 'ios' ? 'padding' : undefined}
                style={{ position: 'absolute', bottom: 0, left: 0, right: 0 } as any}
                pointerEvents="box-none"
            >
                <Animated.View style={{
                    transform: [{ translateY: slideAnim }],
                    backgroundColor: '#ffffff',
                    borderTopLeftRadius: 24,
                    borderTopRightRadius: 24,
                    paddingHorizontal: 20,
                    paddingTop: 10,
                    paddingBottom: Platform.OS === 'ios' ? 40 : 28,
                    shadowColor: '#000',
                    shadowOffset: { width: 0, height: -6 },
                    shadowOpacity: 0.1,
                    shadowRadius: 24,
                    elevation: 24,
                }}>
                    {/* Handle */}
                    <View style={{ width: 32, height: 4, backgroundColor: '#dde1e8', borderRadius: 99, alignSelf: 'center', marginBottom: 16 }} />

                    {/* Header */}
                    <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                        <Text style={{ fontSize: 17, fontFamily: 'Manrope_700Bold', color: '#1a2228' }}>
                            {task ? 'Edit Task' : 'New Task'}
                        </Text>
                        <TouchableOpacity
                            onPress={onClose}
                            style={{ width: 30, height: 30, borderRadius: 99, backgroundColor: '#f0f2f5', alignItems: 'center', justifyContent: 'center' }}
                        >
                            <MaterialIcons name="close" size={17} color="#586064" />
                        </TouchableOpacity>
                    </View>

                    {/* Title + Notes — grouped in one card */}
                    <View style={{
                        backgroundColor: '#f6f7f9',
                        borderRadius: 16,
                        marginBottom: 14,
                        overflow: 'hidden',
                        borderWidth: 1,
                        borderColor: '#eceef2',
                    }}>
                        <TextInput
                            style={{
                                paddingHorizontal: 15,
                                paddingTop: 13,
                                paddingBottom: 8,
                                fontSize: 15,
                                color: '#1a2228',
                                fontFamily: 'Inter_500Medium',
                                // Remove browser outline
                                ...(Platform.OS === 'web' ? { outlineStyle: 'none' } as any : {}),
                            }}
                            placeholder="What needs to be done?"
                            placeholderTextColor="#adb5bd"
                            value={title}
                            onChangeText={setTitle}
                            autoFocus
                            returnKeyType="next"
                            blurOnSubmit={false}
                        />
                        <View style={{ height: 1, backgroundColor: '#eceef2', marginHorizontal: 15 }} />
                        <TextInput
                            style={{
                                paddingHorizontal: 15,
                                paddingTop: 8,
                                paddingBottom: 12,
                                fontSize: 13,
                                color: '#586064',
                                fontFamily: 'Inter_400Regular',
                                minHeight: 56,
                                textAlignVertical: 'top',
                                ...(Platform.OS === 'web' ? { outlineStyle: 'none' } as any : {}),
                            }}
                            placeholder="Add notes (optional)..."
                            placeholderTextColor="#c0c8d0"
                            value={description}
                            onChangeText={setDescription}
                            multiline
                        />
                    </View>

                    {/* Priority */}
                    <Text style={{ fontSize: 10, color: '#adb5bd', fontFamily: 'Inter_600SemiBold', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 8 }}>
                        Priority
                    </Text>
                    <View style={{ flexDirection: 'row', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
                        {PRIORITY_OPTIONS.map(p => {
                            const selected = priority === p.key;
                            return (
                                <TouchableOpacity
                                    key={p.key}
                                    onPress={() => setPriority(p.key)}
                                    style={{
                                        flexDirection: 'row',
                                        alignItems: 'center',
                                        gap: 5,
                                        paddingHorizontal: 12,
                                        paddingVertical: 7,
                                        borderRadius: 99,
                                        backgroundColor: selected ? p.bg : '#f6f7f9',
                                        borderWidth: 1.5,
                                        borderColor: selected ? p.color : '#eceef2',
                                    }}
                                >
                                    <View style={{ width: 7, height: 7, borderRadius: 99, backgroundColor: p.color }} />
                                    <Text style={{ fontSize: 12, fontFamily: selected ? 'Inter_600SemiBold' : 'Inter_400Regular', color: selected ? p.color : '#586064' }}>
                                        {p.label}
                                    </Text>
                                </TouchableOpacity>
                            );
                        })}
                    </View>

                    {/* Due Date */}
                    <Text style={{ fontSize: 10, color: '#adb5bd', fontFamily: 'Inter_600SemiBold', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 8 }}>
                        Due Date
                    </Text>
                    <View style={{ flexDirection: 'row', gap: 7, marginBottom: formattedDue ? 8 : 18, flexWrap: 'wrap' }}>
                        {QUICK_DATES.map(qd => {
                            const chipDate = getChipDate(qd.offset);
                            const isActive = dueDate === chipDate;
                            return (
                                <TouchableOpacity
                                    key={qd.label}
                                    onPress={() => setDueDate(isActive ? '' : chipDate)}
                                    style={{
                                        paddingHorizontal: 11,
                                        paddingVertical: 6,
                                        borderRadius: 99,
                                        backgroundColor: isActive ? '#35436b' : '#f0f2f5',
                                        borderWidth: 1,
                                        borderColor: isActive ? '#35436b' : '#e4e7ec',
                                    }}
                                >
                                    <Text style={{ fontSize: 12, fontFamily: isActive ? 'Inter_600SemiBold' : 'Inter_400Regular', color: isActive ? '#fff' : '#586064' }}>
                                        {qd.label}
                                    </Text>
                                </TouchableOpacity>
                            );
                        })}
                    </View>

                    {/* Selected date pill */}
                    {formattedDue && (
                        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 5, marginBottom: 16 }}>
                            <MaterialIcons name="event" size={13} color="#35436b" />
                            <Text style={{ fontSize: 12, color: '#35436b', fontFamily: 'Inter_500Medium' }}>{formattedDue}</Text>
                            <TouchableOpacity onPress={() => setDueDate('')} hitSlop={{ top: 6, bottom: 6, left: 6, right: 6 }}>
                                <MaterialIcons name="cancel" size={14} color="#c0c8d0" />
                            </TouchableOpacity>
                        </View>
                    )}

                    {/* Save */}
                    <TouchableOpacity
                        onPress={handleSave}
                        disabled={!title.trim() || saving}
                        style={{
                            backgroundColor: title.trim() ? '#35436b' : '#eceef2',
                            borderRadius: 14,
                            paddingVertical: 14,
                            alignItems: 'center',
                        }}
                    >
                        {saving ? (
                            <ActivityIndicator color="#fff" />
                        ) : (
                            <Text style={{ color: title.trim() ? '#fff' : '#adb5bd', fontSize: 14, fontFamily: 'Inter_600SemiBold' }}>
                                {task ? 'Save Changes' : 'Add Task'}
                            </Text>
                        )}
                    </TouchableOpacity>
                </Animated.View>
            </KeyboardAvoidingView>
        </View>
    );
}

// ── Main Screen ──────────────────────────────────────────────────────────────

export default function TodoScreen() {
    const navigation = useNavigation<any>();
    const [activeFilter, setActiveFilter] = useState<TaskFilter>('all');
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [editingTask, setEditingTask] = useState<Task | null>(null);

    const fetchTasks = useCallback(async (filter: TaskFilter = activeFilter) => {
        try {
            const data = await getTasks(filter);
            setTasks(data);
        } catch (e) {
            console.error('fetchTasks error', e);
        }
    }, [activeFilter]);

    useEffect(() => {
        setLoading(true);
        fetchTasks(activeFilter).finally(() => setLoading(false));
    }, [activeFilter]);

    const handleRefresh = async () => {
        setRefreshing(true);
        await fetchTasks(activeFilter);
        setRefreshing(false);
    };

    const handleToggleStatus = async (task: Task) => {
        const nextStatus = STATUS_NEXT[task.status];
        try {
            const updated = await updateTask(task.id, { status: nextStatus });
            setTasks(prev => prev.map(t => (t.id === task.id ? updated : t)));
        } catch {
            Alert.alert('Error', 'Failed to update task status.');
        }
    };

    const handleOpenCreate = () => {
        setEditingTask(null);
        setModalVisible(true);
    };

    const handleEdit = (task: Task) => {
        setEditingTask(task);
        setModalVisible(true);
    };

    const handleDelete = async (task: Task) => {
        try {
            await deleteTask(task.id);
            setTasks(prev => prev.filter(t => t.id !== task.id));
        } catch {
            console.error('Failed to delete task', task.id);
        }
    };

    const handleSave = async (data: any) => {
        if (editingTask) {
            const updated = await updateTask(editingTask.id, data);
            setTasks(prev => prev.map(t => (t.id === editingTask.id ? updated : t)));
        } else {
            const created = await createTask(data);
            setTasks(prev => [created, ...prev]);
        }
    };

    const activeTasks = tasks.filter(t => t.status !== 'done' && t.status !== 'cancelled');
    const completedTasks = tasks.filter(t => t.status === 'done');

    return (
        <SafeAreaView className="flex-1 bg-[#f8f9fa]" edges={['top']}>
            {/* Header */}
            <View className="flex-row items-center justify-between px-5 py-4">
                <TouchableOpacity onPress={() => navigation.goBack()}>
                    <MaterialIcons name="arrow-back" size={26} color="#2b3437" />
                </TouchableOpacity>
                <Text className="text-xl text-[#2b3437]" style={{ fontFamily: 'Inter_600SemiBold' }}>
                    My Tasks
                </Text>
                <TouchableOpacity
                    className="w-9 h-9 bg-[#35436b] rounded-full items-center justify-center"
                    onPress={handleOpenCreate}
                >
                    <MaterialIcons name="add" size={22} color="#fff" />
                </TouchableOpacity>
            </View>

            {/* Filter Tabs */}
            <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                className="flex-grow-0 px-5"
                contentContainerStyle={{ gap: 8, paddingRight: 20, paddingBottom: 12 }}
            >
                {FILTERS.map(f => (
                    <TouchableOpacity
                        key={f.key}
                        className={`px-4 py-2 rounded-full ${activeFilter === f.key ? 'bg-[#35436b]' : 'bg-white border border-gray-200'}`}
                        onPress={() => setActiveFilter(f.key)}
                    >
                        <Text
                            className={`text-sm ${activeFilter === f.key ? 'text-white' : 'text-[#586064]'}`}
                            style={{ fontFamily: activeFilter === f.key ? 'Inter_600SemiBold' : 'Inter_400Regular' }}
                        >
                            {f.label}
                        </Text>
                    </TouchableOpacity>
                ))}
            </ScrollView>

            {/* Task List */}
            {loading ? (
                <View className="flex-1 items-center justify-center">
                    <ActivityIndicator size="large" color="#35436b" />
                </View>
            ) : (
                <ScrollView
                    className="flex-1 px-5"
                    contentContainerStyle={{ paddingTop: 4, paddingBottom: 40 }}
                    refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor="#35436b" />}
                    showsVerticalScrollIndicator={false}
                >
                    {tasks.length === 0 ? (
                        <View className="items-center mt-20">
                            <View className="w-16 h-16 rounded-full bg-[#35436b]/10 items-center justify-center mb-4">
                                <MaterialIcons name="check-circle-outline" size={32} color="#35436b" />
                            </View>
                            <Text className="text-base text-[#2b3437] mb-1" style={{ fontFamily: 'Inter_600SemiBold' }}>
                                No tasks here
                            </Text>
                            <Text className="text-sm text-[#586064] text-center" style={{ fontFamily: 'Inter_400Regular' }}>
                                Tap + to add your first task
                            </Text>
                        </View>
                    ) : (
                        <>
                            {/* Active tasks */}
                            {activeTasks.length > 0 && (
                                <>
                                    <Text className="text-xs text-[#586064] uppercase tracking-widest mb-3" style={{ fontFamily: 'Inter_600SemiBold' }}>
                                        {activeTasks.length} {activeTasks.length === 1 ? 'Task' : 'Tasks'}
                                    </Text>
                                    {activeTasks.map(task => (
                                        <TaskCard
                                            key={task.id}
                                            task={task}
                                            onToggleStatus={handleToggleStatus}
                                            onEdit={handleEdit}
                                            onDelete={handleDelete}
                                        />
                                    ))}
                                </>
                            )}

                            {/* Completed section */}
                            {completedTasks.length > 0 && (
                                <>
                                    <Text className="text-xs text-[#586064] uppercase tracking-widest mb-3 mt-4" style={{ fontFamily: 'Inter_600SemiBold' }}>
                                        Completed · {completedTasks.length}
                                    </Text>
                                    {completedTasks.map(task => (
                                        <TaskCard
                                            key={task.id}
                                            task={task}
                                            onToggleStatus={handleToggleStatus}
                                            onEdit={handleEdit}
                                            onDelete={handleDelete}
                                        />
                                    ))}
                                </>
                            )}
                        </>
                    )}
                </ScrollView>
            )}

            {/* Create/Edit Modal */}
            <TaskFormSheet
                visible={modalVisible}
                task={editingTask}
                onClose={() => setModalVisible(false)}
                onSave={handleSave}
            />
        </SafeAreaView>
    );
}
