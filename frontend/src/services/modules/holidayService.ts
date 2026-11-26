/**
 * Holiday calendar: holidays (everyone / students / staff, possibly tentative) and weekly offs.
 */
import { featureOn } from '../../config/features';
import { getApiClient, getInstitutionId } from '../api/client';
import { API_ENDPOINTS } from '../api/config';

export type Audience = 'ALL' | 'STUDENTS' | 'STAFF';
export type AltSaturdays = 'NONE' | '2_4' | '1_3';

export interface Holiday {
    id: number;
    name: string;
    start_date: string;
    end_date: string;
    days: number;
    applies_to: Audience;
    is_tentative: boolean;
    note: string | null;
    academic_year_id: number | null;
}

export interface CalendarSettings {
    /** 0 = Monday ... 6 = Sunday */
    weekly_off_days: number[];
    alternate_saturdays: AltSaturdays;
    inherited_from: string | null;
}

export interface HolidayYear {
    academic_year_id: number | null;
    year_name: string | null;
    year_start: string | null;
    year_end: string | null;
    settings: CalendarSettings;
    holidays: Holiday[];
}

export interface OffDay {
    date: string;
    label: string;
    kind: 'HOLIDAY' | 'WEEKLY_OFF';
    tentative: boolean;
    holiday_id: number | null;
}

export interface HolidayInput {
    name: string;
    start_date: string;
    end_date: string;
    applies_to: Audience;
    is_tentative: boolean;
    note?: string | null;
    notify?: boolean;
}

export type CalendarEventType = 'HOLIDAY' | 'WEEKLY_OFF' | 'EXAM' | 'LEAVE' | 'EVENT';

/** One item on the Calendar page (a single day or a range) */
export interface CalendarEvent {
    type: CalendarEventType;
    date_from: string;
    date_to: string;
    title: string;
    /** holidays */
    id?: number;
    is_tentative?: boolean;
    applies_to?: Audience;
    note?: string | null;
    start_date?: string;
    end_date?: string;
    /** exams: paper time; staff: classes */
    time?: string;
    detail?: string;
    /** leave: PENDING / APPROVED; events: ACTIVE / CANCELLED */
    status?: 'PENDING' | 'APPROVED' | 'ACTIVE' | 'CANCELLED';
    mine?: boolean;
    /** events */
    event_type?: 'GENERAL' | 'PTM' | 'SPORTS' | 'CULTURAL' | 'MEETING' | 'OTHER';
    event_type_label?: string;
    start_time?: string | null;
    end_time?: string | null;
    location?: string | null;
    description?: string | null;
    audience?: 'ALL' | 'STAFF' | 'STUDENTS' | 'SECTIONS';
    audience_label?: string;
    section_ids?: number[];
    can_edit?: boolean;
}

interface Envelope<T> {
    data: T;
}

const E = API_ENDPOINTS.HOLIDAYS;
const client = () => getApiClient();

export const holidayService = {
    async listYear(academicYearId?: number): Promise<HolidayYear> {
        const res = (await client().get(E.LIST(getInstitutionId()), {
            params: academicYearId ? { academic_year_id: academicYearId } : undefined,
        })) as unknown as Envelope<HolidayYear>;
        return res.data;
    },
    /** Weekly offs and holidays between two days (YYYY-MM-DD) */
    async offDays(from: string, to: string, audience: 'STAFF' | 'STUDENTS'): Promise<OffDay[]> {
        if (!featureOn('calendar')) return []; // no holiday calendar: attendance / leave pages show no off days
        const res = (await client().get(E.OFF_DAYS(getInstitutionId()), { params: { from, to, audience } })) as unknown as Envelope<OffDay[]>;
        return res.data || [];
    },
    async create(input: HolidayInput): Promise<{ holiday: Holiday; recounted_leave: number }> {
        const res = (await client().post(E.CREATE(getInstitutionId()), input)) as unknown as Envelope<{ holiday: Holiday; recounted_leave: number }>;
        return res.data;
    },
    async update(id: number, input: Partial<HolidayInput>): Promise<{ holiday: Holiday; recounted_leave: number }> {
        const res = (await client().put(E.ITEM(getInstitutionId(), id), input)) as unknown as Envelope<{ holiday: Holiday; recounted_leave: number }>;
        return res.data;
    },
    async remove(id: number): Promise<{ recounted_leave: number }> {
        const res = (await client().delete(E.ITEM(getInstitutionId(), id))) as unknown as Envelope<{ recounted_leave: number }>;
        return res.data;
    },
    async saveSettings(weekly_off_days: number[], alternate_saturdays: AltSaturdays): Promise<{ settings: CalendarSettings; recounted_leave: number }> {
        const res = (await client().put(E.SETTINGS(getInstitutionId()), { weekly_off_days, alternate_saturdays })) as unknown as Envelope<{ settings: CalendarSettings; recounted_leave: number }>;
        return res.data;
    },
    /** Holidays, weekly offs, exams and leave between two days (at most two months) */
    async events(from: string, to: string): Promise<CalendarEvent[]> {
        const res = (await client().get(API_ENDPOINTS.CALENDAR.EVENTS(getInstitutionId()), { params: { from, to } })) as unknown as Envelope<{ events: CalendarEvent[] }>;
        return res.data?.events || [];
    },
    async tentativeSoon(): Promise<Holiday[]> {
        if (!featureOn('calendar')) return [];
        const res = (await client().get(E.TENTATIVE_SOON(getInstitutionId()))) as unknown as Envelope<Holiday[]>;
        return res.data || [];
    },
};

export const holidayError = (err: unknown, fallback: string): string =>
    (err as { message?: string } | null)?.message || fallback;

/** { 'YYYY-MM-DD': OffDay } */
export const offDayMap = (list: OffDay[]): Record<string, OffDay> => Object.fromEntries(list.map((d) => [d.date, d]));
