import { getApiClient, getInstitutionId } from '../../../services/api/client';
import { API_ENDPOINTS } from '../../../services/api/config';
import { HomeworkAnalytics, Homework, HomeworkSession } from '../types';

interface ApiEnvelope<T> {
  code: number;
  status: string;
  message: string;
  data: T;
}

interface ResourceListEnvelope<T> {
  data: T[];
}

const AI_GRADING_TIMEOUT_MS = Number(import.meta.env.VITE_AI_GRADING_TIMEOUT_MS || 180000);

export const homeworkApi = {
  async createHomework(payload: {
    class_id: number;
    section_id: number;
    subject: string;
    title: string;
    description: string;
    expected_time_minutes: number;
    reference_answer_key?: string;
    /** YYYY-MM-DD, the day the homework is for (default today) */
    homework_date?: string;
  }, photos: File[] = []): Promise<Homework> {
    const client = getApiClient();
    if (photos.length === 0) {
      const response = await client.post<ApiEnvelope<Homework>>(API_ENDPOINTS.HOMEWORK.ITEMS, payload);
      return response.data;
    }
    // with photos of the homework (e.g. the board): multipart form
    const form = new FormData();
    Object.entries(payload).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') form.append(key, String(value));
    });
    photos.forEach((photo) => form.append('photos', photo));
    const response = await client.post<ApiEnvelope<Homework>>(API_ENDPOINTS.HOMEWORK.ITEMS, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  /** A submitted page as a Blob (the endpoint needs the login token, so <img src> can't load it directly). */
  async getSessionPage(sessionId: number, index: number): Promise<Blob> {
    const client = getApiClient();
    return (await client.get(API_ENDPOINTS.HOMEWORK.SESSION_PAGE(sessionId, index), { responseType: 'blob' })) as unknown as Blob;
  },

  async getHomeworkPhoto(homeworkId: number, index: number): Promise<Blob> {
    const client = getApiClient();
    return (await client.get(`/homework/items/${homeworkId}/photos/${index}`, { responseType: 'blob' })) as unknown as Blob;
  },

  /** AI drafts the instructions from photos of the homework; the teacher edits the text before saving. */
  async draftInstructionsFromPhotos(photos: File[], subject?: string): Promise<string> {
    const client = getApiClient();
    const form = new FormData();
    photos.forEach((photo) => form.append('photos', photo));
    if (subject) form.append('subject', subject);
    const response = await client.post<ApiEnvelope<{ instructions: string }>>('/homework/instructions-from-photo', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data?.instructions || '';
  },

  async listHomework(params?: {
    class_id?: number;
    section_id?: number;
    student_id?: number;
    /** YYYY-MM-DD: only that day's homework */
    date?: string;
  }): Promise<Homework[]> {
    const client = getApiClient();
    const response = await client.get<ApiEnvelope<Homework[]>>(API_ENDPOINTS.HOMEWORK.ITEMS, { params });
    return response.data || [];
  },

  /** Delete a homework nobody has started yet. */
  async deleteHomework(homeworkId: number): Promise<void> {
    await getApiClient().delete(API_ENDPOINTS.HOMEWORK.HOMEWORK_ITEM(homeworkId));
  },

  /** Start or resume a homework. The questions come back with the session (hidden until started). */
  async startSession(homeworkId: number): Promise<HomeworkSession> {
    const client = getApiClient();
    const response = await client.post<ApiEnvelope<HomeworkSession>>(API_ENDPOINTS.HOMEWORK.START_SESSION, { homework_id: homeworkId });
    return response.data;
  },

  async latestSession(homeworkId: number): Promise<HomeworkSession | null> {
    const client = getApiClient();
    const response = await client.get<ApiEnvelope<HomeworkSession | null>>('/homework/sessions/latest', {
      params: { homework_id: homeworkId },
    });
    return response.data ?? null;
  },

  async togglePause(sessionId: number): Promise<HomeworkSession> {
    const client = getApiClient();
    const response = await client.post<ApiEnvelope<HomeworkSession>>(API_ENDPOINTS.HOMEWORK.TOGGLE_PAUSE(sessionId));
    return response.data;
  },

  async askHint(sessionId: number, doubtText?: string, file?: File): Promise<{ hint: string; hints_used_count: number }> {
    const client = getApiClient();
    const form = new FormData();
    if (doubtText) form.append('doubt_text', doubtText);
    if (file) form.append('file', file);
    const response = await client.post<ApiEnvelope<{ hint: string; hints_used_count: number }>>(
      API_ENDPOINTS.HOMEWORK.ASK_HINT(sessionId),
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  },

  /** The finished pages (photos), for AI grading. */
  async submitSession(sessionId: number, files: File[]): Promise<{ session: HomeworkSession; grading: Record<string, unknown> }> {
    const client = getApiClient();
    const form = new FormData();
    files.forEach((file) => form.append('files', file));
    const response = await client.post<ApiEnvelope<{ session: HomeworkSession; grading: Record<string, unknown> }>>(
      API_ENDPOINTS.HOMEWORK.SUBMIT(sessionId),
      form,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: AI_GRADING_TIMEOUT_MS,
      }
    );
    return response.data;
  },

  async getHomeworkAnalytics(homeworkId: number): Promise<HomeworkAnalytics> {
    const client = getApiClient();
    const response = await client.get<ApiEnvelope<HomeworkAnalytics>>(API_ENDPOINTS.HOMEWORK.ANALYTICS(homeworkId));
    return response.data;
  },

  /** Subjects of a section for the Create Homework dropdown (teachers: only the ones they teach there). */
  async listSectionSubjects(sectionId: number): Promise<Array<{ id: number; subject_name: string; subject_code?: string | null }>> {
    const client = getApiClient();
    const response = await client.get<ApiEnvelope<Array<{ id: number; subject_name: string; subject_code?: string | null }>>>(
      `/homework/sections/${sectionId}/subjects`
    );
    return response.data || [];
  },

  /** Classes/sections this user may use on the teacher page (teachers: only sections they teach). */
  async getTeachingScope(): Promise<{
    all: boolean;
    sections: Array<{ class_id: number; class_name: string; section_id: number; section_name: string }>;
  }> {
    const client = getApiClient();
    const response = await client.get<ApiEnvelope<{
      all: boolean;
      sections: Array<{ class_id: number; class_name: string; section_id: number; section_name: string }>;
    }>>('/homework/scope');
    return response.data || { all: false, sections: [] };
  },

  async listClasses(): Promise<Array<{ id: number; class_name?: string; name?: string }>> {
    const client = getApiClient();
    const skid = getInstitutionId();
    const response = await client.get<ApiEnvelope<Array<{ id: number; class_name?: string; name?: string }>>>(
      API_ENDPOINTS.CLASSES.LIST_BY_INSTITUTION(skid)
    );
    return response.data || [];
  },

  async listSections(classId: number): Promise<Array<{ id: number; section_name?: string; name?: string }>> {
    const client = getApiClient();
    const skid = getInstitutionId();
    const response = await client.get<ApiEnvelope<Array<{ id: number; section_name?: string; name?: string }>>>(
      API_ENDPOINTS.CLASSES.SECTIONS(skid, classId)
    );
    return response.data || [];
  },

  async listStudentsRaw(): Promise<Array<Record<string, any>>> {
    const client = getApiClient();
    const response = await client.get<ResourceListEnvelope<Record<string, any>>>(API_ENDPOINTS.STUDENTS.LIST);
    return response.data || [];
  },
};
