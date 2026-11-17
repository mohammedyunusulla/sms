import { getApiClient, getSchoolId } from '../../../services/api/client';
import { API_ENDPOINTS } from '../../../services/api/config';
import { HomeworkAnalytics, HomeworkAssignment, HomeworkSession, StudentStickerRow } from '../types';

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
  }): Promise<HomeworkAssignment> {
    const client = getApiClient();
    const response = await client.post<ApiEnvelope<HomeworkAssignment>>(API_ENDPOINTS.HOMEWORK.CREATE_ASSIGNMENT, payload);
    return response.data;
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

  async assignSticker(studentId: number, qrCodeValue?: string): Promise<{ qr_code_value: string }> {
    const client = getApiClient();
    const response = await client.post<ApiEnvelope<{ qr_code_value: string }>>(API_ENDPOINTS.HOMEWORK.ASSIGN_STICKER, {
      student_id: studentId,
      qr_code_value: qrCodeValue,
    });
    return response.data;
  },

  async listStickers(classId?: number, sectionId?: number): Promise<StudentStickerRow[]> {
    const client = getApiClient();
    const response = await client.get<ApiEnvelope<StudentStickerRow[]>>(API_ENDPOINTS.HOMEWORK.LIST_STICKERS, {
      params: { class_id: classId, section_id: sectionId },
    });
    return response.data || [];
  },

  async startSession(qrCodeValue: string, assignmentId: number): Promise<HomeworkSession> {
    const client = getApiClient();
    const response = await client.post<ApiEnvelope<HomeworkSession>>(API_ENDPOINTS.HOMEWORK.START_SESSION, {
      qr_code_value: qrCodeValue,
      assignment_id: assignmentId,
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

  async submitSession(sessionId: number, qrCodeValue: string, files: File[]): Promise<{ session: HomeworkSession; grading: Record<string, unknown> }> {
    const client = getApiClient();
    const form = new FormData();
    form.append('qr_code_value', qrCodeValue);
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
