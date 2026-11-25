/**
 * Leave requests (students, parents applying for a child, staff) and approvals.
 * Who may see / decide what is checked on the server.
 */
import { getApiClient, getInstitutionId } from '../api/client';
import { API_ENDPOINTS } from '../api/config';

export type LeaveStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED';
export type ApplicantType = 'STUDENT' | 'STAFF';

export interface LeaveRequest {
    id: number;
    applicant_type: ApplicantType;
    user_id: number;
    name: string;
    applied_by: number;
    applied_by_name: string;
    applied_by_self: boolean;
    section_id: number | null;
    class_section: string | null;
    from_date: string;
    to_date: string;
    days: number;
    leave_type: string;
    leave_type_label: string;
    reason: string;
    status: LeaveStatus;
    decided_by_name: string | null;
    decided_at: string | null;
    decision_note: string | null;
    created_at: string | null;
    can_decide: boolean;
    can_cancel: boolean;
    /** staff leave: days counted (Sundays not counted) */
    counted_days: number | null;
    /** staff leave, once approved: paid days (within the yearly balance) and unpaid days (beyond it) */
    paid_days: number | null;
    unpaid_days: number | null;
    /** set when a holiday / weekly-off change recounted this approved leave */
    recount_note: string | null;
    /** pending staff leave: balance of that type and how many days would be unpaid if approved now */
    balance: { paid_days: number | null; used: number; remaining: number | null; would_be_unpaid: number } | null;
}

export interface LeaveBalance {
    type: string;
    label: string;
    /** null = no limit */
    paid_days: number | null;
    used: number;
    remaining: number | null;
}

export interface LeavePolicy {
    academic_year_id: number | null;
    year_name: string | null;
    /** the policy shown comes from this earlier year (nothing saved for the current year yet) */
    inherited_from: string | null;
    types: { type: string; label: string; paid_days: number | null }[];
}

export interface LeaveTypeOption {
    value: string;
    label: string;
}

export interface MyLeaveData {
    applicant_type: ApplicantType;
    leave_types: LeaveTypeOption[];
    days_back: number;
    max_days: number;
    /** staff only */
    balances: LeaveBalance[] | null;
    requests: LeaveRequest[];
}

export interface ReviewData {
    can_review: boolean;
    full_access: boolean;
    pending: number;
    requests: LeaveRequest[];
}

export interface ApplyLeaveInput {
    student_id?: number;
    from_date: string;
    to_date: string;
    leave_type: string;
    reason: string;
}

export interface ReviewFilters {
    status?: string;
    applicant_type?: string;
    from_date?: string;
    to_date?: string;
    search?: string;
}

interface Envelope<T> {
    status?: string;
    message?: string;
    data: T;
}

const client = () => getApiClient();
const E = API_ENDPOINTS.LEAVE;

export const leaveService = {
    async getMine(studentId?: number): Promise<MyLeaveData> {
        const res = (await client().get(E.MY(getInstitutionId()), {
            params: studentId ? { student_id: studentId } : undefined,
        })) as unknown as Envelope<MyLeaveData>;
        return res.data;
    },

    async apply(input: ApplyLeaveInput): Promise<LeaveRequest> {
        const res = (await client().post(E.APPLY(getInstitutionId()), input)) as unknown as Envelope<LeaveRequest>;
        return res.data;
    },

    async cancel(id: number): Promise<LeaveRequest> {
        const res = (await client().post(E.CANCEL(getInstitutionId(), id))) as unknown as Envelope<LeaveRequest>;
        return res.data;
    },

    async getRequests(filters: ReviewFilters = {}): Promise<ReviewData> {
        const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
        const res = (await client().get(E.REQUESTS(getInstitutionId()), { params })) as unknown as Envelope<ReviewData>;
        return res.data;
    },

    async pendingCount(): Promise<number> {
        const res = (await client().get(E.PENDING_COUNT(getInstitutionId()))) as unknown as Envelope<number>;
        return Number(res.data) || 0;
    },

    async decide(id: number, decision: 'APPROVE' | 'REJECT', note?: string): Promise<LeaveRequest> {
        const res = (await client().post(E.DECIDE(getInstitutionId(), id), { decision, note })) as unknown as Envelope<LeaveRequest>;
        return res.data;
    },

    async getPolicy(): Promise<LeavePolicy> {
        const res = (await client().get(E.POLICY(getInstitutionId()))) as unknown as Envelope<LeavePolicy>;
        return res.data;
    },

    async savePolicy(types: { type: string; paid_days: number | null }[]): Promise<LeavePolicy> {
        const res = (await client().put(E.POLICY(getInstitutionId()), { types })) as unknown as Envelope<LeavePolicy>;
        return res.data;
    },

    /** Students of a section on approved leave that day: { studentId: leave type label } */
    async onLeave(sectionId: string | number, date: string): Promise<Record<string, string>> {
        const res = (await client().get(E.ON_LEAVE(getInstitutionId()), {
            params: { section_id: sectionId, date },
        })) as unknown as Envelope<Record<string, string>>;
        return res.data || {};
    },
};

/** The server's error message, for a toast */
export const leaveErrorMessage = (err: unknown, fallback: string): string => {
    // the api client rejects with { status, ...the server's JSON body }
    const e = err as { message?: string } | null;
    return e?.message || fallback;
};
