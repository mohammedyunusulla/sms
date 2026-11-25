/**
 * Staff attendance: mark a day, the monthly register, a staff member's own month, loss of pay on a salary.
 */
import { getApiClient, getInstitutionId } from '../api/client';
import { API_ENDPOINTS } from '../api/config';

export type StaffStatus = 'PRESENT' | 'ABSENT' | 'LATE' | 'HALF_DAY' | 'LEAVE';
export const STAFF_STATUSES: StaffStatus[] = ['PRESENT', 'ABSENT', 'LATE', 'HALF_DAY', 'LEAVE'];
export const STAFF_STATUS_LABEL: Record<StaffStatus, string> = {
    PRESENT: 'Present', ABSENT: 'Absent', LATE: 'Late', HALF_DAY: 'Half day', LEAVE: 'Leave',
};

export interface StaffDayRow {
    user_id: number;
    name: string;
    email: string;
    role_name: string;
    status: StaffStatus | null;
    remarks: string | null;
    on_leave: string | null;
}

export interface StaffDay {
    date: string;
    is_marked: boolean;
    last_saved_by: string | null;
    last_saved_at: string | null;
    staff: StaffDayRow[];
}

export type StaffTotals = Record<StaffStatus | 'NOT_MARKED', number> & { days: number };

export interface StaffRegister {
    year: number;
    month: number;
    days: number;
    staff: { user_id: number; name: string; role_name: string; days: Record<string, StaffStatus>; totals: StaffTotals }[];
}

export interface MyStaffMonth {
    year: number;
    month: number;
    days: number;
    records: { date: string; status: StaffStatus; remarks: string | null }[];
    approved_leave_days: string[];
    totals: StaffTotals;
}

interface Envelope<T> {
    data: T;
}

const E = API_ENDPOINTS.STAFF_ATTENDANCE;
const client = () => getApiClient();

export const staffAttendanceService = {
    async getDay(date: string): Promise<StaffDay> {
        const res = (await client().get(E.DAY(getInstitutionId()), { params: { date } })) as unknown as Envelope<StaffDay>;
        return res.data;
    },
    async saveDay(date: string, records: { user_id: number; status: StaffStatus; remarks?: string | null }[]): Promise<{ saved: number }> {
        const res = (await client().post(E.DAY(getInstitutionId()), { date, records })) as unknown as Envelope<{ saved: number }>;
        return res.data;
    },
    async getRegister(year: number, month: number): Promise<StaffRegister> {
        const res = (await client().get(E.REGISTER(getInstitutionId()), { params: { year, month } })) as unknown as Envelope<StaffRegister>;
        return res.data;
    },
    async getMine(year: number, month: number): Promise<MyStaffMonth> {
        const res = (await client().get(E.MY(getInstitutionId()), { params: { year, month } })) as unknown as Envelope<MyStaffMonth>;
        return res.data;
    },
    async lossOfPay(paymentId: number, apply: boolean): Promise<{ net_amount_paid: number }> {
        const res = (await client().post(E.LOSS_OF_PAY(getInstitutionId(), paymentId), { apply })) as unknown as Envelope<{ net_amount_paid: number }>;
        return res.data;
    },
};

export const errorMessage = (err: unknown, fallback: string): string =>
    (err as { message?: string } | null)?.message || fallback;
