/**
 * Section Service
 * Handles API calls for section management operations
 */

import { getApiClient, getInstitutionId } from '../api/client';
import { ISection } from '../../types/index';

class SectionService {
    private baseUrl = '/classes';

    /**
     * Get sections for a specific class
     */
    async getByClass(classId: string): Promise<ISection[]> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.get(`${this.baseUrl}/sections/${institutionId}/${classId}`);
        return response?.data || [];
    }

    /**
     * Get single section by ID
     */
    async getById(sectionId: string): Promise<ISection> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.get(`${this.baseUrl}/section/${sectionId}/${institutionId}`);
        return response.data?.data || response.data;
    }

    /**
     * Create new section for a class
     */
    async create(classId: string, sectionName: string, teacherId: string): Promise<ISection> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.post(`${this.baseUrl}/create/section/${institutionId}`, {
            class_id: classId,
            section_name: sectionName,
            teacher_id: teacherId,
        });

        if (response.code === 200 && response.status === 'success') {
            return response.data;
        }

        throw new Error(response.data || 'Failed to create section');
    }

    /**
     * Update existing section
     */
    async update(sectionId: string, classId: string, sectionName: string, teacherId: string): Promise<ISection> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.put(`${this.baseUrl}/update/section/${institutionId}/${sectionId}`, {
            class_id: classId,
            section_name: sectionName,
            teacher_id: teacherId,
        });

        if (response.code === 200 && response.status === 'success') {
            return response?.data;
        }

        throw new Error(response.data?.message || 'Failed to update section');
    }

    /**
     * Delete section
     */
    async delete(sectionId: string): Promise<void> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = await api.delete(`${this.baseUrl}/delete/section/${institutionId}/${sectionId}`);
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response.data?.message || 'Failed to delete section');
        }
    }
}

// Export singleton instance
export const sectionService = new SectionService();
