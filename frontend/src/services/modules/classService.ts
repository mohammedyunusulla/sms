import { getApiClient, getSchoolId } from '../api/client';
import { IClass } from '../../types/index';


interface IClassListParams {
    search?: string;
    section?: string;
    teacher?: string;
    status?: 'ACTIVE' | 'INACTIVE';
    page?: number;
    limit?: number;
}


class ClassService {
    private baseUrl = '/classes';

    // Get list of classes with optional filtering
    async list(): Promise<any> {
        const api = getApiClient();
        const schoolId = getSchoolId();

        if (!schoolId) {
            throw new Error('School ID not found. Please log in again.');
        }

        const response = await api.get(`${this.baseUrl}/list/${schoolId}`);
        return response.data;
    }


    // Get single class by ID
    async getById(id: string): Promise<IClass> {
        const api = getApiClient();
        const schoolId = getSchoolId();

        if (!schoolId) {
            throw new Error('School ID not found. Please log in again.');
        }

        const response = await api.get(`${this.baseUrl}/${id}/${schoolId}`);
        return response.data;
    }


    // Create new class
    async create(data: Omit<IClass, 'id' | 'createdAt'>): Promise<IClass> {
        const api = getApiClient();
        const schoolId = getSchoolId();

        if (!schoolId) {
            throw new Error('School ID not found. Please log in again.');
        }

        const response = await api.post(`${this.baseUrl}/create/class/${schoolId}`, data);
        if (response.code === 200 && response.status === 'success') {
            return response.class;
        }
        throw new Error(response?.message || 'Failed to create class');
    }


    // Update existing class
    async update(id: string, data: Partial<IClass>): Promise<IClass> {
        const api = getApiClient();
        const schoolId = getSchoolId();

        if (!schoolId) {
            throw new Error('School ID not found. Please log in again.');
        }

        const response = await api.put(`${this.baseUrl}/update/class/${schoolId}/${id}`, data);
        if (response.code === 200 && response.status === 'success') {
            return response?.data;
        }
        throw new Error(response.data?.message || 'Failed to update class');
    }

    // Delete class
    async delete(id: string): Promise<void> {
        const api = getApiClient();
        const schoolId = getSchoolId();

        if (!schoolId) {
            throw new Error('School ID not found. Please log in again.');
        }

        const response = await api.delete(`${this.baseUrl}/class/delete/${schoolId}/${id}`);
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response.message || response.data?.message || 'Failed to delete class');
        }
    }


    // Assign students to a class
    async assignStudents(classId: string, studentIds: string[]): Promise<void> {
        const api = getApiClient();
        const schoolId = getSchoolId();

        if (!schoolId) {
            throw new Error('School ID not found. Please log in again.');
        }

        const response = await api.post(`${this.baseUrl}/${classId}/assign-students/${schoolId}`, { studentIds });
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response.data?.message || 'Failed to assign students');
        }
    }


    // Get students in a class
    async getStudents(classId: string): Promise<any[]> {
        const api = getApiClient();
        const schoolId = getSchoolId();

        if (!schoolId) {
            throw new Error('School ID not found. Please log in again.');
        }

        const response = await api.get(`${this.baseUrl}/${classId}/students/${schoolId}`);
        return response.data?.data || [];
    }


    // Remove student from section
    async removeStudent(sectionId: string, studentId: string): Promise<void> {
        const api = getApiClient();
        const schoolId = getSchoolId();

        if (!schoolId) {
            throw new Error('School ID not found. Please log in again.');
        }

        const response = await api.delete(`${this.baseUrl}/remove-from-section/${schoolId}/${sectionId}/${studentId}`);
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response.data?.message || 'Failed to remove student from section');
        }
    }


    // Move student to another section
    async moveStudent(targetSectionId: string, studentId: string): Promise<void> {
        const api = getApiClient();
        const schoolId = getSchoolId();

        if (!schoolId) {
            throw new Error('School ID not found. Please log in again.');
        }

        const response = await api.put(`${this.baseUrl}/move-to-section/${schoolId}/${targetSectionId}/${studentId}`, {});
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response.data?.message || 'Failed to move student to section');
        }
    }


    // Update class status (ACTIVE/INACTIVE)
    async updateStatus(id: string, status: 'ACTIVE' | 'INACTIVE'): Promise<IClass> {
        const api = getApiClient();
        const schoolId = getSchoolId();

        if (!schoolId) {
            throw new Error('School ID not found. Please log in again.');
        }

        const response = await api.patch(`${this.baseUrl}/${id}/status/${schoolId}`, { status });
        if (response.code === 200 && response.status === 'success') {
            return response?.data;
        }
        throw new Error(response.data?.message || 'Failed to update class status');
    }


    // Get sections for a specific class
    async getSections(classId: string): Promise<any[]> {
        const api = getApiClient();
        const schoolId = getSchoolId();

        if (!schoolId) {
            throw new Error('School ID not found. Please log in again.');
        }

        const response = await api.get(`${this.baseUrl}/sections/${schoolId}/${classId}`);
        return response.data || [];
    }

    // Create Section For the Selected Class
    // teacherId is optional: a section can be created without a class teacher and assigned later
    async createSection(classId: string, sectionName: string, teacherId?: string | number | null): Promise<any> {
        const api = getApiClient();
        const schoolId = getSchoolId();

        if (!schoolId) {
            throw new Error('School ID not found. Please log in again.');
        }

        const response = await api.post(`${this.baseUrl}/create/section/${schoolId}`, {
            class_id: classId,
            section_name: sectionName,
            teacher_id: teacherId || null,
        });

        if (response.code === 200 && response.status === 'success') {
            return response?.data;
        }

        throw new Error(response.data?.message || 'Failed to create section');
    }

    // teacherId empty/null removes the class teacher
    async updateSection(classId: string, sectionId: string, sectionName: string, teacherId?: string | number | null): Promise<any> {
        const api = getApiClient();
        const schoolId = getSchoolId();

        if (!schoolId) {
            throw new Error('School ID not found. Please log in again.');
        }

        const response = await api.put(`${this.baseUrl}/update/section/${schoolId}/${sectionId}`, {
            class_id: classId,
            section_name: sectionName,
            teacher_id: teacherId || null,
        });

        if (response.code === 200 && response.status === 'success') {
            return response?.data;
        }

        throw new Error(response.data?.message || 'Failed to update section');
    }

    // Delete a section (refused by the backend if anything still uses it)
    async deleteSection(sectionId: string | number): Promise<void> {
        const api = getApiClient();
        const schoolId = getSchoolId();

        if (!schoolId) {
            throw new Error('School ID not found. Please log in again.');
        }

        const response = await api.delete(`${this.baseUrl}/section/delete/${schoolId}/${sectionId}`);
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response.message || 'Failed to delete section');
        }
    }


    // Export classes to CSV
    async exportToCSV(params?: IClassListParams): Promise<Blob> {
        const api = getApiClient();
        const response = await api.get(`${this.baseUrl}/export/csv`, {
            params,
            responseType: 'blob',
        });
        return response.data;
    }
}

// Export singleton instance
export const classService = new ClassService();
