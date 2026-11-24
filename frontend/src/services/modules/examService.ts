
// Exam Service
// Handles API calls for exam management operations
// Uses centralized API client from services/api/client.ts


import { getApiClient, getInstitutionId } from '../api/client';
import { IExam, ExamType } from '../../types/index';

interface IExamListResponse {
    data: IExam[];
    meta: {
        total: number;
        page: number;
        limit: number;
        totalPages: number;
    };
}

interface ICreateExamRequest {
    name: string;
    type: ExamType;
    description?: string;
    startDate: string;
    endDate: string;
    classIds: string[];
    publishResults?: boolean;
}

interface IUpdateExamRequest {
    name?: string;
    type?: ExamType;
    description?: string;
    startDate?: string;
    endDate?: string;
    classIds?: string[];
    status?: 'SCHEDULED' | 'ONGOING' | 'COMPLETED';
    publishResults?: boolean;
}

interface IExamSchedule {
    examId: string;
    classId: string;
    subject: string;
    date: string;
    startTime: string;
    endTime: string;
    room?: string;
}

class ExamService {
    private baseUrl = '/exams';


    // Get list of exams with optional filtering 
    /** Exams whose results are published (visible to students/parents) for a year */
    async listPublishedResults(academicYearId: number | string): Promise<{ exam_type_id: number; published_at: string }[]> {
        const api = getApiClient();
        const institutionId = getInstitutionId();
        if (!institutionId) throw new Error('Institution ID not found. Please log in again.');
        const response = (await api.get(`${this.baseUrl}/results-published/${institutionId}`, {
            params: { academic_year_id: academicYearId },
        })) as unknown as { data?: { exam_type_id: number; published_at: string }[] };
        return response?.data || [];
    }

    /** Publish (or hide again) an exam's results for students and parents */
    async setResultsPublished(examTypeId: number, academicYearId: number | string, published: boolean): Promise<unknown> {
        const api = getApiClient();
        const institutionId = getInstitutionId();
        if (!institutionId) throw new Error('Institution ID not found. Please log in again.');
        return api.post(`${this.baseUrl}/results-publish/${institutionId}/${examTypeId}`, {
            academic_year_id: Number(academicYearId),
            published,
        });
    }

    async list(): Promise<IExamListResponse> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.get(`${this.baseUrl}/fetch/exam-types/${institutionId}`);
        return response.data;
    }


    // Get single exam by ID 
    async getById(id: string): Promise<IExam> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.get(`${this.baseUrl}/${id}/${institutionId}`);
        return response.data;
    }


    // Create new exam 
    async create(data: ICreateExamRequest): Promise<IExam> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.post(`${this.baseUrl}/create/exam-type/${institutionId}`, data);
        if (response.code === 200 && response.status === 'success') {
            return response.data;
        }
        throw new Error(response?.message || 'Failed to create exam');
    }


    // Update exam 
    async update(id: string, data: IUpdateExamRequest): Promise<IExam> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.put(`${this.baseUrl}/update/exam-type/${institutionId}/${id}`, data);
        if (response.code === 200 && response.status === 'success') {
            return response.data;
        }
        throw new Error(response?.message || 'Failed to update exam');
    }


    // Delete exam 
    async delete(id: string): Promise<void> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.delete(`${this.baseUrl}/delete/${id}/${institutionId}`);
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response?.message || 'Failed to delete exam');
        }
    }


    // Update exam status 
    async updateStatus(id: string, status: 'SCHEDULED' | 'ONGOING' | 'COMPLETED'): Promise<void> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.patch(`${this.baseUrl}/${id}/status/${institutionId}`, { status });
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response?.message || 'Failed to update exam status');
        }
    }


    // Get exam schedule 
    async getSchedule(examId: string): Promise<IExamSchedule[]> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.get(`${this.baseUrl}/${examId}/schedule/${institutionId}`);
        return response?.data || [];
    }


    // Create exam schedule 
    async createSchedule(
        examId: string,
        schedule: Omit<IExamSchedule, 'examId'>
    ): Promise<IExamSchedule> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.post(`${this.baseUrl}/${examId}/schedule/${institutionId}`, schedule);
        if (response.code === 200 && response.status === 'success') {
            return response?.data;
        }
        throw new Error(response?.message || 'Failed to create exam schedule');
    }


    // Update exam schedule 
    async updateSchedule(
        examId: string,
        scheduleId: string,
        schedule: Partial<Omit<IExamSchedule, 'examId'>>
    ): Promise<IExamSchedule> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.put(`${this.baseUrl}/${examId}/schedule/${scheduleId}/${institutionId}`, schedule);
        if (response.code === 200 && response.status === 'success') {
            return response?.data;
        }
        throw new Error(response?.message || 'Failed to update exam schedule');
    }


    // Delete exam schedule 
    async deleteSchedule(examId: string, scheduleId: string): Promise<void> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.delete(`${this.baseUrl}/${examId}/schedule/${scheduleId}/${institutionId}`);
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response?.message || 'Failed to delete exam schedule');
        }
    }


    // Publish exam results 
    async publishResults(examId: string): Promise<void> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.post(`${this.baseUrl}/${examId}/publish-results/${institutionId}`);
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response?.message || 'Failed to publish exam results');
        }
    }


    // Get exam statistics 
    async getStatistics(examId: string): Promise<any> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.get(`${this.baseUrl}/${examId}/statistics/${institutionId}`);
        return response?.data || response.data;
    }


    // Bulk delete exams
    async bulkDelete(ids: string[]): Promise<void> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.post(`${this.baseUrl}/bulk-delete/${institutionId}`, { ids });
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response?.message || 'Failed to delete exams');
        }
    }

    /**
     * Get exam subject configurations with filters
     */
    async getExamConfigs(filters?: any): Promise<any> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.get(`${this.baseUrl}/fetch/exam-configs/${institutionId}`, {
            params: filters,
        });
        return response.data;
    }

    /**
     * Get single exam configuration by ID
     */
    async getExamConfigById(configId: string): Promise<any> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.get(`${this.baseUrl}/exam-config/${configId}/${institutionId}`);
        return response?.data || response.data;
    }

    /**
     * Create exam subject configuration
     */
    async createExamConfig(data: any): Promise<any> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.post(`${this.baseUrl}/create/exam-config/${institutionId}`, data);
        if (response.code === 200 && response.status === 'success') {
            return response?.data;
        }
        throw new Error(response?.message || 'Failed to create configuration');
    }

    /**
     * Update exam subject configuration
     */
    async updateExamConfig(configId: string, data: any): Promise<any> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.put(
            `${this.baseUrl}/update/exam-config/${institutionId}/${configId}`,
            data
        );
        if (response.code === 200 && response.status === 'success') {
            return response?.data;
        }
        throw new Error(response?.message || 'Failed to update configuration');
    }

    /**
     * Delete exam subject configuration
     */
    async deleteExamConfig(configId: string): Promise<void> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.delete(
            `${this.baseUrl}/delete/exam-config/${institutionId}/${configId}`
        );
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response?.message || 'Failed to delete configuration');
        }
    }

    // ──────────────────────────────────────────────
    // Exam Timetable
    // ──────────────────────────────────────────────

    async getExamTimetables(filters?: {
        academic_year_id?: number;
        exam_type_id?: number;
        class_id?: number;
        section_id?: number;
    }): Promise<any> {
        const api = getApiClient();
        const institutionId = getInstitutionId();
        if (!institutionId) throw new Error('Institution ID not found. Please log in again.');

        const response = await api.get(`${this.baseUrl}/fetch/exam-timetables/${institutionId}`, {
            params: filters,
        });
        return response.data;
    }

    async getExamTimetableById(entryId: string): Promise<any> {
        const api = getApiClient();
        const institutionId = getInstitutionId();
        if (!institutionId) throw new Error('Institution ID not found. Please log in again.');

        const response = await api.get(`${this.baseUrl}/exam-timetable/${entryId}/${institutionId}`);
        return response?.data || response.data;
    }

    async createExamTimetable(data: any): Promise<any> {
        const api = getApiClient();
        const institutionId = getInstitutionId();
        if (!institutionId) throw new Error('Institution ID not found. Please log in again.');

        const response = await api.post(`${this.baseUrl}/create/exam-timetable/${institutionId}`, data);
        if (response.code === 200 && response.status === 'success') {
            return response?.data;
        }
        throw new Error(response?.message || 'Failed to create exam timetable entry');
    }

    async updateExamTimetable(entryId: string, data: any): Promise<any> {
        const api = getApiClient();
        const institutionId = getInstitutionId();
        if (!institutionId) throw new Error('Institution ID not found. Please log in again.');

        const response = await api.put(`${this.baseUrl}/update/exam-timetable/${institutionId}/${entryId}`, data);
        if (response.code === 200 && response.status === 'success') {
            return response?.data;
        }
        throw new Error(response?.message || 'Failed to update exam timetable entry');
    }

    async deleteExamTimetable(entryId: string): Promise<void> {
        const api = getApiClient();
        const institutionId = getInstitutionId();
        if (!institutionId) throw new Error('Institution ID not found. Please log in again.');

        const response = await api.delete(`${this.baseUrl}/delete/exam-timetable/${institutionId}/${entryId}`);
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response?.message || 'Failed to delete exam timetable entry');
        }
    }

    async getStudentExamTimetable(studentId: number, examTypeId: number, academicYearId?: number): Promise<any[]> {
        const api = getApiClient();
        const institutionId = getInstitutionId();
        if (!institutionId) throw new Error('Institution ID not found. Please log in again.');

        const params: any = { exam_type_id: examTypeId };
        if (academicYearId) params.academic_year_id = academicYearId;

        const response = await api.get(`${this.baseUrl}/student-exam-timetable/${institutionId}/${studentId}`, { params });
        return Array.isArray(response.data) ? response.data : (response.data?.data || []);
    }

    async getInvigilatorSchedule(teacherId: number, examTypeId: number, academicYearId?: number): Promise<any[]> {
        const api = getApiClient();
        const institutionId = getInstitutionId();
        if (!institutionId) throw new Error('Institution ID not found. Please log in again.');

        const params: any = { exam_type_id: examTypeId };
        if (academicYearId) params.academic_year_id = academicYearId;

        const response = await api.get(`${this.baseUrl}/invigilator-schedule/${institutionId}/${teacherId}`, { params });
        return Array.isArray(response.data) ? response.data : (response.data?.data || []);
    }

    async bulkDeleteExamTimetables(ids: number[]): Promise<any> {
        const api = getApiClient();
        const institutionId = getInstitutionId();
        if (!institutionId) throw new Error('Institution ID not found. Please log in again.');

        const response = await api.post(`${this.baseUrl}/bulk-delete/exam-timetables/${institutionId}`, { ids });
        if (response.code === 200 && response.status === 'success') {
            return response?.data;
        }
        throw new Error(response?.message || 'Failed to bulk delete exam timetable entries');
    }

    /**
     * Bulk copy exam configurations
     */
    async bulkCopyConfigs(data: any): Promise<any> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.post(
            `${this.baseUrl}/bulk-copy/exam-configs/${institutionId}`,
            data
        );
        if (response.code === 200 && response.status === 'success') {
            return response?.data;
        }
        throw new Error(response?.message || 'Failed to copy configurations');
    }
}

// Export singleton instance
export const examService = new ExamService();
