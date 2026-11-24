/**
 * Institution Service
 * Handles API calls for institution management operations
 * Uses centralized API client from services/api/client.ts
 */

import { getApiClient } from '../api/client';
import { IInstitution } from '../../types/index';

interface IInstitutionListParams {
    search?: string;
    status?: 'active' | 'inactive';
    page?: number;
    limit?: number;
}

interface IInstitutionListResponse {
    data: IInstitution[];
    meta: {
        total: number;
        page: number;
        limit: number;
        totalPages: number;
    };
}

class InstitutionService {
    private baseUrl = '/institution';

    /**
     * Get list of all institutions
     */
    async listInstitutions(): Promise<{ data: IInstitution[] }> {
        const api = getApiClient();
        const response = await api.get(`${this.baseUrl}/list`);
        if (response.code === 200 && response.status === 'success') {
            return { data: response?.data };
        }
        throw new Error(response.data?.message || 'Failed to fetch institutions');
    }

    /**
     * Get list of institutions with optional filtering
     */
    async list(params?: IInstitutionListParams): Promise<IInstitutionListResponse> {
        const api = getApiClient();
        const response = await api.get(`${this.baseUrl}/list`, { params });
        return response.data;
    }

    /**
     * Get single institution by ID
     */
    async getById(id: string): Promise<IInstitution> {
        const api = getApiClient();
        const response = await api.get(`${this.baseUrl}/${id}`);
        return response.institution;
    }

    /**
     * Create new institution
     */
    async create(data: Omit<IInstitution, 'id' | 'created_at' | 'updated_at'>): Promise<IInstitution> {
        const api = getApiClient();
        const response = await api.post(`${this.baseUrl}/create`, data);
        if (response.code === 200 && response.status === 'success') {
            // the client already unwraps the body: the institution is at the top level (response.data was undefined)
            return response.institution;
        }
        throw new Error(response.data?.message || 'Failed to create institution');
    }

    /**
     * Update existing institution
     */
    async update(id: string, data: Partial<IInstitution>): Promise<IInstitution> {
        const api = getApiClient();
        const response = await api.put(`${this.baseUrl}/update/${id}`, data);
        if (response.code === 200 && response.status === 'success') {
            return response.institution;
        }
        throw new Error(response.message || 'Failed to update institution');
    }

    /**
     * Delete institution
     */
    async deleteInstitution(id: string, confirmCode: string): Promise<void> {
        const api = getApiClient();
        // the server deletes only with the institution's code typed back (QA S14)
        const response = await api.delete(`${this.baseUrl}/delete/${id}`, { data: { confirm_code: confirmCode } });
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response.data?.message || 'Failed to delete institution');
        }
    }

    /**
     * Activate institution
     */
    async activateInstitution(id: string): Promise<void> {
        const api = getApiClient();
        const response = await api.patch(`${this.baseUrl}/activate/${id}`);
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response.data?.message || 'Failed to activate institution');
        }
    }

    /**
     * Deactivate institution
     */
    async deactivateInstitution(id: string): Promise<void> {
        const api = getApiClient();
        const response = await api.patch(`${this.baseUrl}/deactivate/${id}`);
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response.data?.message || 'Failed to deactivate institution');
        }
    }

    /**
     * Update institution status (activate/deactivate)
     */
    async updateStatus(id: string, status: 'active' | 'inactive'): Promise<IInstitution> {
        if (status === 'active') {
            await this.activateInstitution(id);
        } else {
            await this.deactivateInstitution(id);
        }
        return await this.getById(id);
    }

    /**
     * Bulk delete institutions
     */
    async bulkDelete(ids: string[]): Promise<void> {
        const api = getApiClient();
        await api.post(`${this.baseUrl}/bulk-delete`, { ids });
    }

    /**
     * Export institutions to CSV
     */
    async exportToCSV(params?: IInstitutionListParams): Promise<Blob> {
        const api = getApiClient();
        const response = await api.get(`${this.baseUrl}/export/csv`, {
            params,
            responseType: 'blob',
        });
        return response.data;
    }

    /**
     * Get list of institution admins
     */
    async listInstitutionAdmins(): Promise<{ data: any[] }> {
        const api = getApiClient();
        const response = await api.get(`${this.baseUrl}/list/institution-admins`);
        if (response.code === 200 && response.status === 'success') {
            return { data: response?.data };
        }
        throw new Error(response.data?.message || 'Failed to fetch institution admins');
    }

    /**
     * Soft delete an institution admin (inactive + login disabled; can be reactivated).
     * Uses the admin's own institution id: a super admin doesn't belong to an institution.
     */
    async deactivateInstitutionAdmin(skid: string, institutionUserId: number | string): Promise<string> {
        const api = getApiClient();
        const response = await api.delete(`/users/delete/${skid}/${institutionUserId}`);
        if (response.code === 200 && response.status === 'success') {
            return response.message || 'Institution admin deleted';
        }
        throw new Error(response.message || 'Failed to delete institution admin');
    }

    /** Reactivate a (soft-)deleted institution admin. */
    async reactivateInstitutionAdmin(skid: string, institutionUserId: number | string): Promise<string> {
        const api = getApiClient();
        const response = await api.patch(`/users/reactivate/${skid}/${institutionUserId}`);
        if (response.code === 200 && response.status === 'success') {
            return response.message || 'Institution admin reactivated';
        }
        throw new Error(response.message || 'Failed to reactivate institution admin');
    }

    /**
     * Change institution admin password
     */
    async changeAdminPassword(adminId: string, newPassword: string): Promise<void> {
        const api = getApiClient();
        const response = await api.patch(`${this.baseUrl}/institution-admin/change-password/${adminId}`, {
            new_password: newPassword,
        });
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response.data?.message || 'Failed to change password');
        }
    }

    /**
     * Get institution admin by skid and admin ID
     * Uses the /users/institutionAdmin/{skid}/{admin_id} endpoint
     */
    async getInstitutionAdmin(skid: string, adminId: string): Promise<any> {
        const api = getApiClient();
        const response = await api.get(`/users/institutionAdmin/${skid}/${adminId}`) as any;
        if (response.code === 200 && response.status === 'success') {
            return response.user;
        }
        throw new Error(response.message || 'Failed to fetch institution admin');
    }

    /**
     * Create an institution admin (super admin context - no institutionId in URL)
     * Uses the /users/create endpoint directly
     */
    async createInstitutionAdmin(data: Record<string, any>): Promise<any> {
        const api = getApiClient();
        const response = await api.post('/users/create', data) as any;
        if (response.code === 200 && response.status === 'success') {
            return response.user;
        }
        throw new Error(response.message || 'Failed to create institution admin');
    }

    /**
     * Update an institution admin (super admin context - no institutionId in URL)
     * Uses the /users/update/{admin_id} endpoint directly
     */
    async updateInstitutionAdmin(adminId: string, data: Record<string, any>): Promise<any> {
        const api = getApiClient();
        const response = await api.put(`/users/update/${adminId}`, data) as any;
        if (response.user) {
            return response.user;
        }
        throw new Error(response.message || 'Failed to update institution admin');
    }

    /**
     * Get list of all system admins (super admins)
     */
    async listSuperAdmins(): Promise<{ data: any[] }> {
        const api = getApiClient();
        const response = await api.get('/users/super-admins') as any;
        if (response.code === 200 && response.status === 'success') {
            return { data: response.data };
        }
        throw new Error(response.message || 'Failed to fetch system admins');
    }

    /**
     * Create a new system admin (super admin)
     */
    async createSuperAdmin(data: { username?: string; email?: string; password: string }): Promise<any> {
        const api = getApiClient();
        const response = await api.post('/users/create-super-admin', data) as any;
        if (response.code === 200 && response.status === 'success') {
            return response.user;
        }
        throw new Error(response.message || 'Failed to create system admin');
    }
}

// Export singleton instance
export const institutionService = new InstitutionService();
