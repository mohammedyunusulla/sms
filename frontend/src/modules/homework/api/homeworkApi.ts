import { getApiClient, getSchoolId } from '../../../services/api/client';
import { API_ENDPOINTS } from '../../../services/api/config';
import { HomeworkAnalytics, HomeworkAssignment, HomeworkSession } from '../types';

interface ApiEnvelope<T> {
  code: number;
  status: string;
  message: string;
  data: T;
}

interface ResourceListEnvelope<T> {
  data: T[];
}

export const homeworkApi = {
  async createAssignment(payload: {
    class_id: number;
    section_id: number;
    subject: string;
    title: string;
    description: string;
    expected_time_minutes: number;
    reference_answer_key?: string;
    due_date?: string;
  }, photos: File[] = []): Promise<HomeworkAssignment> {
    const client = getApiClient();
    if (photos.length === 0) {
      const response = await client.post<ApiEnvelope<HomeworkAssignment>>(API_ENDPOINTS.HOMEWORK.CREATE_ASSIGNMENT, payload);
      return response.data;
    }
    // with photos of the homework (e.g. the board): multipart form
    const form = new FormData();
    Object.entries(payload).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') form.append(key, String(value));
    });
    photos.forEach((photo) => form.append('photos', photo));
    const response = await client.post<ApiEnvelope<HomeworkAssignment>>(API_ENDPOINTS.HOMEWORK.CREATE_ASSIGNMENT, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  /** One homework photo as a Blob (the endpoint needs the login token, so <img src> can't load it directly). */
  /** A session's photo: the blank start page (kind 'start', index 0) or a finished page (kind 'page'). */
  async getSessionPhoto(sessionId: number, kind: 'start' | 'page', index: number): Promise<Blob> {
    const client = getApiClient();
    return (await client.get(API_ENDPOINTS.HOMEWORK.SESSION_PHOTO(sessionId, kind, index), { responseType: 'blob' })) as unknown as Blob;
  },

  async getHomeworkPhoto(assignmentId: number, index: number): Promise<Blob> {
    const client = getApiClient();
    return (await client.get(`/homework/assignments/${assignmentId}/photos/${index}`, { responseType: 'blob' })) as unknown as Blob;
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

  async listAssignments(params?: {
    class_id?: number;
    section_id?: number;
    student_id?: number;
  }): Promise<HomeworkAssignment[]> {
    const client = getApiClient();
    const response = await client.get<ApiEnvelope<HomeworkAssignment[]>>(API_ENDPOINTS.HOMEWORK.LIST_ASSIGNMENTS, { params });
    return response.data || [];
  },

  /** Start (photo of the blank page with its QR sticker) or resume (no photo) a homework. */
  async startSession(assignmentId: number, startPhoto?: File): Promise<HomeworkSession> {
    const client = getApiClient();
    if (!startPhoto) {
      const resumed = await client.post<ApiEnvelope<HomeworkSession>>(API_ENDPOINTS.HOMEWORK.START_SESSION, { assignment_id: assignmentId });
      return resumed.data;
    }
    const form = new FormData();
    form.append('assignment_id', String(assignmentId));
    form.append('start_photo', startPhoto);
    const response = await client.post<ApiEnvelope<HomeworkSession>>(API_ENDPOINTS.HOMEWORK.START_SESSION, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
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

  /** The finished pages; the page the homework was started on (same QR sticker) must be one of them. */
  async submitSession(sessionId: number, files: File[]): Promise<{ session: HomeworkSession; grading: Record<string, unknown> }> {
    const client = getApiClient();
    const form = new FormData();
    files.forEach((file) => form.append('files', file));
    const response = await client.post<ApiEnvelope<{ session: HomeworkSession; grading: Record<string, unknown> }>>(
      API_ENDPOINTS.HOMEWORK.SUBMIT(sessionId),
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  },

  async getAssignmentAnalytics(assignmentId: number): Promise<HomeworkAnalytics> {
    const client = getApiClient();
    const response = await client.get<ApiEnvelope<HomeworkAnalytics>>(API_ENDPOINTS.HOMEWORK.ANALYTICS(assignmentId));
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
    const skid = getSchoolId();
    const response = await client.get<ApiEnvelope<Array<{ id: number; class_name?: string; name?: string }>>>(
      API_ENDPOINTS.CLASSES.LIST_BY_SCHOOL(skid)
    );
    return response.data || [];
  },

  async listSections(classId: number): Promise<Array<{ id: number; section_name?: string; name?: string }>> {
    const client = getApiClient();
    const skid = getSchoolId();
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
