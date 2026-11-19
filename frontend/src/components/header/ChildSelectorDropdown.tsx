import { FC, useState, useRef, useEffect } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { useParentStore, ParentChild } from '../../stores/parentStore';
import { parentService } from '../../services/modules/parentService';

let lastFetchedForUserId: number | null = null;

const UserIcon = () => (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
);

const ChevronDownIcon = () => (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
);

const childLabel = (child: ParentChild) =>
    child.full_name || `${child.first_name ?? ''} ${child.last_name ?? ''}`.trim() || 'Child';

const ChildSelectorDropdown: FC = () => {
    const user = useAuthStore((s) => s.user);
    const { children, selectedChild, loaded, loading, setChildren, selectChild, setLoading, reset } =
        useParentStore();

    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Fetch children once per session. Refetch if the logged-in user changes.
    useEffect(() => {
        const uid = user?.school_user_id;
        if (!uid) return;

        // New user logged in — clear stale state from the previous user
        if (lastFetchedForUserId !== null && lastFetchedForUserId !== uid) {
            reset();
            lastFetchedForUserId = null;
        }

        if (loaded || loading) return;

        lastFetchedForUserId = uid;
        setLoading(true);
        parentService
            .getMyChildren(uid)
            .then((list) => setChildren(Array.isArray(list) ? list : []))
            .catch(() => setChildren([]))
            .finally(() => setLoading(false));
    }, [user?.school_user_id, loaded, loading, setChildren, setLoading, reset]);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    if (loading && children.length === 0) {
        return (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-indigo-50 dark:bg-indigo-900/20">
                <UserIcon />
                <span className="text-sm font-medium text-indigo-700 dark:text-indigo-300">Loading…</span>
            </div>
        );
    }

    if (!loading && children.length === 0) return null;

    const handlePick = (child: ParentChild) => {
        if (child.student_id !== selectedChild?.student_id) {
            selectChild(child);
        }
        setIsOpen(false);
    };

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 hover:bg-indigo-100 dark:hover:bg-indigo-900/30 transition-colors"
            >
                <UserIcon />
                <span className="text-sm font-medium text-indigo-700 dark:text-indigo-300 max-w-[140px] truncate">
                    {selectedChild ? childLabel(selectedChild) : 'Select Child'}
                </span>
                <ChevronDownIcon />
            </button>

            {isOpen && (
                <div className="absolute left-0 lg:left-auto lg:right-0 top-full mt-2 w-64 bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 py-2 z-50">
                    <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700">
                        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                            My Children
                        </p>
                    </div>

                    <div className="max-h-72 overflow-y-auto">
                        {children.map((child) => {
                            const isSelected = child.student_id === selectedChild?.student_id;
                            const classLine = [child.class_name, child.section_name]
                                .filter(Boolean)
                                .join(' · ');
                            return (
                                <button
                                    key={child.student_id}
                                    onClick={() => handlePick(child)}
                                    className={`w-full flex items-center justify-between px-3 py-2.5 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${
                                        isSelected ? 'bg-indigo-50 dark:bg-indigo-900/20' : ''
                                    }`}
                                >
                                    <div className="min-w-0">
                                        <p
                                            className={`text-sm truncate ${
                                                isSelected
                                                    ? 'font-semibold text-indigo-700 dark:text-indigo-300'
                                                    : 'text-gray-700 dark:text-gray-300'
                                            }`}
                                        >
                                            {childLabel(child)}
                                        </p>
                                        {(classLine || child.roll_no) && (
                                            <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                                {classLine}
                                                {child.roll_no ? ` · Roll #${child.roll_no}` : ''}
                                            </p>
                                        )}
                                    </div>
                                    {isSelected && (
                                        <svg
                                            className="w-4 h-4 text-indigo-600 dark:text-indigo-400 flex-shrink-0 ml-2"
                                            fill="currentColor"
                                            viewBox="0 0 24 24"
                                        >
                                            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                                        </svg>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
};

export default ChildSelectorDropdown;
