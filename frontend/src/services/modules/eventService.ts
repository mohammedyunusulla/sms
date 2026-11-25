/**
 * Events (Annual Day, parent-teacher meetings, sports meets...). Shown through the Calendar feed;
 * managed by the Institution Admin / "Manage Events", and by class teachers for their own section.
 */
import { getApiClient, getInstitutionId } from '../api/client';
import { API_ENDPOINTS } from '../api/config';

export type EventType = 'GENERAL' | 'PTM' | 'SPORTS' | 'CULTURAL' | 'MEETING' | 'OTHER';
export type EventAudience = 'ALL' | 'STAFF' | 'STUDENTS' | 'SECTIONS';

export interface EventOptions {
    can_create: boolean;
    can_manage_all: boolean;
    types: { value: EventType; label: string }[];
    audiences: { value: EventAudience; label: string }[];
    /** sections this user may target, with their class (the form picks a class, then its sections) */
    sections: { id: number; label: string; section_name: string; class_id: number; class_name: string }[];
}

export interface EventInput {
    title: string;
    event_type: EventType;
    start_date: string;
    end_date: string;
    /** HH:MM, or empty for all day */
    start_time: string;
    end_time: string;
    location: string;
    description: string;
    audience: EventAudience;
    section_ids: number[];
    notify?: boolean;
    reinstate?: boolean;
}

interface Envelope<T> {
    data: T;
}

const E = API_ENDPOINTS.EVENTS;
const client = () => getApiClient();

export const eventService = {
    async options(): Promise<EventOptions> {
        const res = (await client().get(E.OPTIONS(getInstitutionId()))) as unknown as Envelope<EventOptions>;
        return res.data;
    },
    async create(input: EventInput): Promise<unknown> {
        return ((await client().post(E.CREATE(getInstitutionId()), input)) as unknown as Envelope<unknown>).data;
    },
    async update(id: number, input: Partial<EventInput>): Promise<unknown> {
        return ((await client().put(E.ITEM(getInstitutionId(), id), input)) as unknown as Envelope<unknown>).data;
    },
    async cancel(id: number, notify: boolean): Promise<unknown> {
        return ((await client().post(E.CANCEL(getInstitutionId(), id), { notify })) as unknown as Envelope<unknown>).data;
    },
    async remove(id: number): Promise<unknown> {
        return ((await client().delete(E.ITEM(getInstitutionId(), id))) as unknown as Envelope<unknown>).data;
    },
};
