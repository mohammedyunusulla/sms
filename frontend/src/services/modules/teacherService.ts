/**
 * Teacher Service
 * Handles API calls for teacher management operations
 */

import { getApiClient, getInstitutionId } from '../api/client';

interface ITeacherListParams {
    search?: string;
    gender?: string;
    status?: string;
    page?: number;
    limit?: number;
}

interface ITeacherListResponse {
    data: any[];
    meta: {
        total: number;
        page: number;
        limit: number;
        totalPages: number;
    };
}

class TeacherService {
    private baseUrl = '/teachers';

    /**
     * Get list of teachers with pagination
     */
    async list(params?: ITeacherListParams): Promise<ITeacherListResponse> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        try {
            const response = await api.get(`${this.baseUrl}/list/${institutionId}`, { params });

            // Handle both old and new response formats
            if (response.data && response.meta) {
                // New format: { data: [], meta: { total, page, limit, totalPages } }
                return response;
            } else {
                throw new Error('Invalid response format');
            }
        } catch (error: any) {
            throw new Error(error.message || 'Failed to fetch teachers');
        }
    }

    /**
     * Every active teacher, for dropdowns. list() with no params returned only the first 10 (the server's
     * default page size), so bigger institutions saw part of their staff in timetable / section / seating forms.
     */
    async listAll(): Promise<ITeacherListResponse['data']> {
        const all: ITeacherListResponse['data'] = [];
        for (let page = 1; page <= 50; page++) {
            const res = await this.list({ page, limit: 100, status: 'active' });
            all.push(...res.data);
            if (!res.meta || page >= (res.meta.totalPages || 1)) break;
        }
        return all;
    }

    /**
     * Get single teacher by ID
     */
    async getById(id: string): Promise<any> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.get(`${this.baseUrl}/profile/${institutionId}/${id}`);
        return response.teacher_data;
    }

    /**
     * Create new teacher
     */
    async create(data: any): Promise<any> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.post(`${this.baseUrl}/create/${institutionId}`, data);
        if (response.code === 200 && response.status === 'success') {
            return response?.data;
        }
        throw new Error(response?.message || response.data?.message || 'Failed to create teacher');
    }

    /**
     * Update teacher
     */
    async update(id: string, data: any): Promise<any> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.put(`${this.baseUrl}/update/${institutionId}/${id}`, data);
        if (response.code === 200 && response.status === 'success') {
            return response.data;
        }
        throw new Error(response?.message || response.data?.message || 'Failed to update teacher');
    }

    /**
     * Delete teacher
     */
    async delete(id: string): Promise<void> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.delete(`${this.baseUrl}/delete/${institutionId}/${id}`);
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response?.message || response.data?.message || 'Failed to delete teacher');
        }
    }

    // Reactivate a (soft-)deleted teacher: active again and login re-enabled.
    async reactivate(id: string): Promise<void> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = (await api.patch(`${this.baseUrl}/reactivate/${institutionId}/${id}`));
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response.message || 'Failed to reactivate teacher');
        }
    }
    /**
     * Get subject IDs assigned to a teacher
     */
    async getSubjectIds(teacherId: string): Promise<number[]> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.get(`${this.baseUrl}/${teacherId}/subjects/${institutionId}`);
        return response.subject_ids || [];
    }

    /**
     * Assign subjects to a teacher (replaces all existing assignments)
     */
    async assignSubjects(teacherId: string, subjectIds: number[]): Promise<void> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.put(`${this.baseUrl}/${teacherId}/assign-subjects/${institutionId}`, {
            subject_ids: subjectIds,
        });
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response.data?.message || 'Failed to assign subjects');
        }
    }
}

export const teacherService = new TeacherService();
