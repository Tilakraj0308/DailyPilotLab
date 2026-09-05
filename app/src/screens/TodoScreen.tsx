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
    { key: 'overdue', label: 'Overdue' },
    { key: 'high_priority', label: 'Priority' },
    { key: 'completed', label: 'Completed' },
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
    todo: 'done',
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

    const hasTime = (d.getHours() !== 0 || d.getMinutes() !== 0);
    const timeStr = hasTime ? ` at ${d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}` : '';

    if (diff === 0) return `Due today${timeStr}`;
    if (diff === 1) return `Due tomorrow${timeStr}`;
    if (diff === -1) return `Yesterday${timeStr}`;
    if (diff < 0) return `${Math.abs(diff)}d overdue`;
    return `${d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}${timeStr}`;
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
        <View className={`bg-white rounded-2xl p-4 mb-3 shadow-sm border ${overdue ? 'border-red-200 bg-red-50/20' : 'border-transparent'}`}>
            <View className="flex-row items-start gap-3">
                {/* Status toggle (Open <-> Done) */}
                <TouchableOpacity
                    className={`w-6 h-6 rounded-full border-2 mt-0.5 items-center justify-center flex-shrink-0 ${isDone ? 'bg-[#35436b] border-[#35436b]' : 'border-gray-300 bg-white'}`}
                    onPress={() => onToggleStatus(task)}
                    hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                >
                    {isDone && <MaterialIcons name="check" size={14} color="#fff" />}
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

// ── Mini Calendar Date Picker Component ─────────────────────────────────────

function MiniCalendarPicker({
    selectedDate,
    onSelectDate,
}: {
    selectedDate: string;
    onSelectDate: (dateStr: string) => void;
}) {
    const today = new Date();
    const initialDate = selectedDate ? new Date(selectedDate + 'T00:00:00') : today;
    const [viewYear, setViewYear] = useState(initialDate.getFullYear());
    const [viewMonth, setViewMonth] = useState(initialDate.getMonth());

    const monthNames = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ];

    const prevMonth = () => {
        if (viewMonth === 0) {
            setViewMonth(11);
            setViewYear(v => v - 1);
        } else {
            setViewMonth(v => v - 1);
        }
    };

    const nextMonth = () => {
        if (viewMonth === 11) {
            setViewMonth(0);
            setViewYear(v => v + 1);
        } else {
            setViewMonth(v => v + 1);
        }
    };

    const firstDayIndex = new Date(viewYear, viewMonth, 1).getDay();
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
    const todayStr = today.toISOString().split('T')[0];

    const handleSelectDay = (day: number) => {
        const mm = String(viewMonth + 1).padStart(2, '0');
        const dd = String(day).padStart(2, '0');
        onSelectDate(`${viewYear}-${mm}-${dd}`);
    };

    return (
        <View style={{ backgroundColor: '#f8f9fa', borderRadius: 16, padding: 12, marginBottom: 14, borderWidth: 1, borderColor: '#e2e8f0' }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                <TouchableOpacity onPress={prevMonth} style={{ padding: 4 }}>
                    <MaterialIcons name="chevron-left" size={22} color="#35436b" />
                </TouchableOpacity>
                <Text style={{ fontSize: 13, fontFamily: 'Inter_600SemiBold', color: '#1a2228' }}>
                    {monthNames[viewMonth]} {viewYear}
                </Text>
                <TouchableOpacity onPress={nextMonth} style={{ padding: 4 }}>
                    <MaterialIcons name="chevron-right" size={22} color="#35436b" />
                </TouchableOpacity>
            </View>

            <View style={{ flexDirection: 'row', justifyContent: 'space-around', marginBottom: 6 }}>
                {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((d, i) => (
                    <Text key={i} style={{ width: 28, textAlign: 'center', fontSize: 11, color: '#94a3b8', fontFamily: 'Inter_600SemiBold' }}>
                        {d}
                    </Text>
                ))}
            </View>

            <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
                {Array.from({ length: firstDayIndex }).map((_, i) => (
                    <View key={`empty-${i}`} style={{ width: '14.28%', height: 32 }} />
                ))}
                {Array.from({ length: daysInMonth }).map((_, i) => {
                    const dayNum = i + 1;
                    const mm = String(viewMonth + 1).padStart(2, '0');
                    const dd = String(dayNum).padStart(2, '0');
                    const dateStr = `${viewYear}-${mm}-${dd}`;
                    const isSelected = selectedDate === dateStr;
                    const isToday = todayStr === dateStr;

                    return (
                        <TouchableOpacity
                            key={`day-${dayNum}`}
                            onPress={() => handleSelectDay(dayNum)}
                            style={{
                                width: '14.28%',
                                height: 32,
                                alignItems: 'center',
                                justifyContent: 'center',
                            }}
                        >
                            <View style={{
                                width: 26,
                                height: 26,
                                borderRadius: 99,
                                backgroundColor: isSelected ? '#35436b' : 'transparent',
                                borderWidth: isToday && !isSelected ? 1.5 : 0,
                                borderColor: '#35436b',
                                alignItems: 'center',
                                justifyContent: 'center',
                            }}>
                                <Text style={{
                                    fontSize: 12,
                                    fontFamily: isSelected || isToday ? 'Inter_600SemiBold' : 'Inter_400Regular',
                                    color: isSelected ? '#ffffff' : isToday ? '#35436b' : '#334155',
                                }}>
                                    {dayNum}
                                </Text>
                            </View>
                        </TouchableOpacity>
                    );
                })}
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

const TIME_PERIODS = [
    { label: 'Morning', time: '09:00', icon: 'wb-sunny' },
    { label: 'Afternoon', time: '13:00', icon: 'wb-twilight' },
    { label: 'Evening', time: '18:00', icon: 'nights-stay' },
    { label: 'Night', time: '21:00', icon: 'bedtime' },
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
    const [dueTime, setDueTime] = useState('');
    const [saving, setSaving] = useState(false);
    const [mounted, setMounted] = useState(visible);
    const slideAnim = useRef(new Animated.Value(visible ? 0 : 500)).current;
    const fadeAnim = useRef(new Animated.Value(visible ? 1 : 0)).current;

    // Sync form fields when task/visible changes
    useEffect(() => {
        if (task) {
            setTitle(task.title);
            setDescription(task.description || '');
            setPriority(task.priority);
            if (task.due_date) {
                const d = new Date(task.due_date);
                if (!isNaN(d.getTime())) {
                    const yyyy = d.getFullYear();
                    const mm = String(d.getMonth() + 1).padStart(2, '0');
                    const dd = String(d.getDate()).padStart(2, '0');
                    setDueDate(`${yyyy}-${mm}-${dd}`);

                    const hh = String(d.getHours()).padStart(2, '0');
                    const min = String(d.getMinutes()).padStart(2, '0');
                    if (d.getHours() !== 0 || d.getMinutes() !== 0) {
                        setDueTime(`${hh}:${min}`);
                    } else {
                        setDueTime('');
                    }
                } else {
                    setDueDate('');
                    setDueTime('');
                }
            } else {
                setDueDate('');
                setDueTime('');
            }
        } else {
            setTitle('');
            setDescription('');
            setPriority('medium');
            setDueDate('');
            setDueTime('');
        }
    }, [task, visible]);

    // Slide in/out animation
    useEffect(() => {
        if (visible) {
            setMounted(true);
            Animated.parallel([
                Animated.spring(slideAnim, { toValue: 0, useNativeDriver: true, damping: 24, stiffness: 240 }),
                Animated.timing(fadeAnim, { toValue: 1, duration: 180, useNativeDriver: true }),
            ]).start();
        } else {
            Animated.parallel([
                Animated.timing(slideAnim, { toValue: 500, duration: 180, useNativeDriver: true }),
                Animated.timing(fadeAnim, { toValue: 0, duration: 180, useNativeDriver: true }),
            ]).start(({ finished }) => {
                if (finished) setMounted(false);
            });
        }
    }, [visible]);

    const handleSave = () => {
        if (!title.trim() || saving) return;
        const timeToUse = dueTime || '00:00';
        const payload = {
            title: title.trim(),
            description: description.trim() || undefined,
            priority,
            due_date: dueDate ? new Date(`${dueDate}T${timeToUse}:00`).toISOString() : undefined,
        };
        onClose();
        onSave(payload);
    };

    const formattedDue = dueDate
        ? new Date(dueDate + 'T' + (dueTime || '00:00') + ':00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
        : null;

    const formattedTime = dueTime
        ? new Date(`2000-01-01T${dueTime}:00`).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
        : null;

    if (!visible && !mounted) return null;

    return (
        <View style={{ position: 'absolute', inset: 0, zIndex: 50 } as any} pointerEvents={visible ? 'auto' : 'none'}>
            {/* Backdrop */}
            <Animated.View
                style={{ position: 'absolute', inset: 0, backgroundColor: 'rgba(20,28,40,0.5)', opacity: fadeAnim } as any}
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
                    maxHeight: '90%',
                    shadowColor: '#000',
                    shadowOffset: { width: 0, height: -6 },
                    shadowOpacity: 0.1,
                    shadowRadius: 24,
                    elevation: 24,
                }}>
                    <ScrollView showsVerticalScrollIndicator={false} bounces={false}>
                        {/* Handle */}
                        <View style={{ width: 32, height: 4, backgroundColor: '#dde1e8', borderRadius: 99, alignSelf: 'center', marginBottom: 14 }} />

                        {/* Header */}
                        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
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

                        {/* Due Date Calendar Picker */}
                        <Text style={{ fontSize: 10, color: '#adb5bd', fontFamily: 'Inter_600SemiBold', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 8 }}>
                            Due Date
                        </Text>

                        <MiniCalendarPicker
                            selectedDate={dueDate}
                            onSelectDate={(d) => setDueDate(d)}
                        />

                        {/* Time Period Selector */}
                        <Text style={{ fontSize: 10, color: '#adb5bd', fontFamily: 'Inter_600SemiBold', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 8 }}>
                            Time Period
                        </Text>
                        <View style={{ flexDirection: 'row', gap: 7, marginBottom: 14, flexWrap: 'wrap' }}>
                            {TIME_PERIODS.map(tp => {
                                const isActive = dueTime === tp.time;
                                return (
                                    <TouchableOpacity
                                        key={tp.label}
                                        onPress={() => setDueTime(isActive ? '' : tp.time)}
                                        style={{
                                            flexDirection: 'row',
                                            alignItems: 'center',
                                            gap: 5,
                                            paddingHorizontal: 11,
                                            paddingVertical: 6,
                                            borderRadius: 99,
                                            backgroundColor: isActive ? '#35436b' : '#f0f2f5',
                                            borderWidth: 1,
                                            borderColor: isActive ? '#35436b' : '#e4e7ec',
                                        }}
                                    >
                                        <MaterialIcons name={tp.icon as any} size={13} color={isActive ? '#fff' : '#586064'} />
                                        <Text style={{ fontSize: 12, fontFamily: isActive ? 'Inter_600SemiBold' : 'Inter_400Regular', color: isActive ? '#fff' : '#586064' }}>
                                            {tp.label}
                                        </Text>
                                    </TouchableOpacity>
                                );
                            })}
                        </View>

                        {/* Selected date & time pill */}
                        {formattedDue && (
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 5, marginBottom: 16 }}>
                                <MaterialIcons name="event" size={13} color="#35436b" />
                                <Text style={{ fontSize: 12, color: '#35436b', fontFamily: 'Inter_500Medium' }}>
                                    {formattedDue}{formattedTime ? ` at ${formattedTime}` : ''}
                                </Text>
                                <TouchableOpacity onPress={() => { setDueDate(''); setDueTime(''); }} hitSlop={{ top: 6, bottom: 6, left: 6, right: 6 }}>
                                    <MaterialIcons name="cancel" size={14} color="#c0c8d0" />
                                </TouchableOpacity>
                            </View>
                        )}

                        {/* Save Button */}
                        <TouchableOpacity
                            onPress={handleSave}
                            disabled={!title.trim() || saving}
                            style={{
                                backgroundColor: title.trim() ? '#35436b' : '#e2e8f0',
                                borderRadius: 14,
                                paddingVertical: 14,
                                alignItems: 'center',
                                marginTop: 4,
                                marginBottom: 8,
                            }}
                        >
                            <Text style={{ fontSize: 15, fontFamily: 'Inter_600SemiBold', color: title.trim() ? '#ffffff' : '#94a3b8' }}>
                                {task ? 'Save Changes' : 'Create Task'}
                            </Text>
                        </TouchableOpacity>
                    </ScrollView>
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

    const fetchTasks = useCallback(async () => {
        try {
            // Fetch all tasks once (or during pull-to-refresh)
            const data = await getTasks('all');
            setTasks(data);
        } catch (e) {
            console.error('fetchTasks error', e);
        }
    }, []);

    useEffect(() => {
        setLoading(true);
        fetchTasks().finally(() => setLoading(false));
    }, [fetchTasks]);

    const handleRefresh = async () => {
        setRefreshing(true);
        await fetchTasks();
        setRefreshing(false);
    };

    const handleToggleStatus = async (task: Task) => {
        const nextStatus = STATUS_NEXT[task.status];
        const optimisticTask: Task = {
            ...task,
            status: nextStatus,
            completed_at: nextStatus === 'done' ? new Date().toISOString() : undefined,
            updated_at: new Date().toISOString(),
        };

        // Optimistic UI update: instantly update local state
        setTasks(prev => prev.map(t => (t.id === task.id ? optimisticTask : t)));

        try {
            const updated = await updateTask(task.id, { status: nextStatus });
            setTasks(prev => prev.map(t => (t.id === task.id ? updated : t)));
        } catch (e) {
            console.error('Failed to update task status', task.id, e);
            // Rollback on failure
            setTasks(prev => prev.map(t => (t.id === task.id ? task : t)));
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
        // Optimistic UI update: instantly remove from list
        setTasks(prev => prev.filter(t => t.id !== task.id));

        try {
            await deleteTask(task.id);
        } catch (e) {
            console.error('Failed to delete task', task.id, e);
            // Rollback on failure: restore task
            setTasks(prev => [task, ...prev]);
            Alert.alert('Error', 'Failed to delete task.');
        }
    };

    const handleSave = async (data: any) => {
        if (editingTask) {
            const optimisticTask: Task = {
                ...editingTask,
                ...data,
                updated_at: new Date().toISOString(),
            };
            // Optimistic update
            setTasks(prev => prev.map(t => (t.id === editingTask.id ? optimisticTask : t)));

            try {
                const updated = await updateTask(editingTask.id, data);
                setTasks(prev => prev.map(t => (t.id === editingTask.id ? updated : t)));
            } catch (e) {
                console.error('Failed to update task', editingTask.id, e);
                // Rollback
                setTasks(prev => prev.map(t => (t.id === editingTask.id ? editingTask : t)));
                Alert.alert('Error', 'Failed to update task.');
            }
        } else {
            const tempId = `temp_${Date.now()}`;
            const tempTask: Task = {
                id: tempId,
                user_id: '',
                title: data.title,
                description: data.description,
                status: 'todo',
                priority: data.priority || 'medium',
                due_date: data.due_date,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
            };
            // Optimistic insert
            setTasks(prev => [tempTask, ...prev]);

            try {
                const created = await createTask(data);
                setTasks(prev => prev.map(t => (t.id === tempId ? created : t)));
            } catch (e) {
                console.error('Failed to create task', e);
                // Rollback
                setTasks(prev => prev.filter(t => t.id !== tempId));
                Alert.alert('Error', 'Failed to create task.');
            }
        }
    };

    const filteredTasks = tasks.filter(t => {
        if (t.status === 'cancelled') return false;
        if (activeFilter === 'completed') {
            return t.status === 'done';
        }
        if (t.status === 'done') return false;

        if (activeFilter === 'due_today') {
            if (!t.due_date) return false;
            const d = new Date(t.due_date);
            const now = new Date();
            return (
                d.getFullYear() === now.getFullYear() &&
                d.getMonth() === now.getMonth() &&
                d.getDate() === now.getDate()
            );
        }
        if (activeFilter === 'overdue') {
            return isOverdue(t.due_date, t.status);
        }
        if (activeFilter === 'high_priority') {
            return t.priority === 'high' || t.priority === 'urgent';
        }
        return true;
    });

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
                    {filteredTasks.length === 0 ? (
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
                            <Text className="text-xs text-[#586064] uppercase tracking-widest mb-3" style={{ fontFamily: 'Inter_600SemiBold' }}>
                                {filteredTasks.length} {filteredTasks.length === 1 ? 'Task' : 'Tasks'}
                            </Text>
                            {filteredTasks.map((task: Task) => (
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
