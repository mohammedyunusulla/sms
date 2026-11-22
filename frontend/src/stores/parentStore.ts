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

// The chosen child survives a reload (it reset to the first child - QA D26). Stored with the parent's id, so
// another parent signing in on the same device starts from their own first child; cleared at sign-out.
export const SELECTED_CHILD_KEY = 'parentSelectedChild';
const currentParentId = (): number | null => {
    try {
        return JSON.parse(localStorage.getItem('loggedUser') || 'null')?.school_user_id ?? null;
    } catch {
        return null;
    }
};
const rememberedChild = (children: ParentChild[]): ParentChild | null => {
    try {
        const saved = JSON.parse(localStorage.getItem(SELECTED_CHILD_KEY) || 'null');
        if (!saved || saved.parent !== currentParentId()) return null;
        return children.find((c) => c.student_id === saved.child) || null;
    } catch {
        return null;
    }
};

export const useParentStore = create<ParentStore>((set) => ({
    children: [],
    selectedChild: null,
    loading: false,
    loaded: false,

    setChildren: (children) =>
        set({
            children,
            selectedChild: rememberedChild(children) || (children.length > 0 ? children[0] : null),
            loaded: true,
        }),

    selectChild: (child) => {
        localStorage.setItem(SELECTED_CHILD_KEY, JSON.stringify({ parent: currentParentId(), child: child?.student_id ?? null }));
        set({ selectedChild: child });
    },

    setLoading: (loading) => set({ loading }),

    reset: () => set({ children: [], selectedChild: null, loading: false, loaded: false }),
}));
