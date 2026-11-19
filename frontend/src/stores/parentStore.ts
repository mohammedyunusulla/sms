/**
 * Parent Store (Zustand)
 * Holds the parent's linked children and the currently selected child.
 * Not persisted — children are re-fetched on each session (mirrors the mobile app).
 */

import { create } from 'zustand';

export interface ParentChild {
    student_id: number;
    school_user_id?: number;
    first_name: string;
    last_name?: string;
    full_name?: string;
    class_name?: string;
    section_name?: string;
    roll_no?: string;
    relation_type?: string;
    [key: string]: any;
}

interface ParentStore {
    children: ParentChild[];
    selectedChild: ParentChild | null;
    loading: boolean;
    loaded: boolean;

    setChildren: (children: ParentChild[]) => void;
    selectChild: (child: ParentChild) => void;
    setLoading: (loading: boolean) => void;
    reset: () => void;
}

export const useParentStore = create<ParentStore>((set) => ({
    children: [],
    selectedChild: null,
    loading: false,
    loaded: false,

    setChildren: (children) =>
        set({
            children,
            selectedChild: children.length > 0 ? children[0] : null,
            loaded: true,
        }),

    selectChild: (child) => set({ selectedChild: child }),

    setLoading: (loading) => set({ loading }),

    reset: () => set({ children: [], selectedChild: null, loading: false, loaded: false }),
}));
