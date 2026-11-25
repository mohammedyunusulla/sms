/**
 * Substitute teacher planner: periods needing cover on a date, suggestions, assign / remove.
 */
import { getApiClient, getInstitutionId } from '../api/client';
import { API_ENDPOINTS } from '../api/config';

export interface Suggestion {
    teacher_id: number;
    name: string;
    /** e.g. "Same subject", "Teaches this class", "1 cover today" */
    tags: string[];
}

export interface CoverPeriod {
    entry_id: number;
    period_number: number;
    start_time: string;
    end_time: string;
    class_section: string;
    subject_name: string;
    teacher_id: number;
    teacher_name: string;
    reason: 'LEAVE' | 'ABSENT' | 'HALF_DAY' | 'MANUAL' | null;
    reason_label: string;
    /** half day: listed as "may need cover" */
    optional: boolean;
    /** the teacher is back (leave cancelled / marked present) */
    teacher_back: boolean;
    substitute_id: number | null;
    substitute_name: string | null;
    note: string | null;
    suggestions: Suggestion[];
}

export interface CoverDay {
    date: string;
    off_day: { label: string; kind: string } | null;
    periods: CoverPeriod[];
    needed: number;
    covered: number;
    teachers: { id: number; name: string }[];
}

export interface TeacherPeriod {
    entry_id: number;
    period_number: number;
    start_time: string;
    end_time: string;
    class_section: string;
    subject_name: string;
}

interface Envelope<T> {
    data: T;
}

const E = API_ENDPOINTS.SUBSTITUTIONS;
const client = () => getApiClient();
const skid = () => getInstitutionId();

export const substitutionService = {
    async day(date: string): Promise<CoverDay> {
        return ((await client().get(E.DAY(skid()), { params: { date } })) as unknown as Envelope<CoverDay>).data;
    },
    async teacherPeriods(date: string, teacherId: number): Promise<TeacherPeriod[]> {
        return ((await client().get(E.TEACHER_PERIODS(skid()), { params: { date, teacher_id: teacherId } })) as unknown as Envelope<TeacherPeriod[]>).data || [];
    },
    async assign(date: string, entryId: number, substituteId: number): Promise<void> {
        await client().post(E.ASSIGN(skid()), { date, entry_id: entryId, substitute_id: substituteId });
    },
    async assignAll(date: string): Promise<{ assigned: number }> {
        return ((await client().post(E.ASSIGN_ALL(skid()), { date })) as unknown as Envelope<{ assigned: number }>).data;
    },
    async remove(date: string, entryId: number): Promise<void> {
        await client().post(E.REMOVE(skid()), { date, entry_id: entryId });
    },
    async mark(date: string, entryIds: number[], note: string): Promise<{ added: number }> {
        return ((await client().post(E.MARK(skid()), { date, entry_ids: entryIds, note })) as unknown as Envelope<{ added: number }>).data;
    },
    async unmark(date: string, entryId: number): Promise<void> {
        await client().post(E.UNMARK(skid()), { date, entry_id: entryId });
    },
    async today(): Promise<{ needed: number; covered: number; uncovered: number }> {
        return ((await client().get(E.TODAY(skid()))) as unknown as Envelope<{ needed: number; covered: number; uncovered: number }>).data;
    },
};

export const subError = (err: unknown, fallback: string): string => (err as { message?: string } | null)?.message || fallback;
