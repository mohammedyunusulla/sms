/**
 * User Service
 * Handles API calls for user management operations
 * Uses centralized API client from services/api/client.ts
 */

import { getApiClient, getInstitutionId } from '../api/client';
import { IUser } from '../../types/index';

/**
 * Generic API response interface
 * The axios response interceptor returns response.data directly,
 * so we need type assertions when accessing these properties
 */
interface ApiResponse {
    code?: number;
    status?: string;
    message?: string;
    data?: IUser | IUser[];
    user?: IUser;
    meta?: {
        total: number;
        page: number;
        limit: number;
        totalPages: number;
    };
    total?: number;
    page?: number;
    limit?: number;
    totalPages?: number;
}

interface IUserListParams {
    search?: string;
    gender?: string;
    role?: string;
    status?: string;
    page?: number;
    limit?: number;
}

interface IUserListResponse {
    data: IUser[];
    meta: {
        total: number;
        page: number;
        limit: number;
        totalPages: number;
    };
}

class UserService {
    private baseUrl = '/users';

    /**
     * Get list of users with optional filtering
     */
    async list(params?: IUserListParams): Promise<IUserListResponse> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        try {
            const response = (await api.get(`${this.baseUrl}/list/${institutionId}`, { params })) as ApiResponse;

            // Handle response format
            if (response.data && response.meta) {
                // New format: { data: [], meta: { total, page, limit, totalPages } }
                return {
                    data: response.data as IUser[],
                    meta: response.meta
                };
            } else if (response.data && !response.meta) {
                // Fallback for old format: ensure meta exists
                const dataArray = response.data as IUser[];
                return {
                    data: dataArray,
                    meta: {
                        total: response.total || dataArray.length,
                        page: response.page || 1,
                        limit: response.limit || dataArray.length,
                        totalPages: response.totalPages || 1
                    }
                };
            } else {
                throw new Error('Invalid response format');
            }
        } catch (error: any) {
            throw new Error(error.message || 'Failed to fetch users');
        }
    }

    /**
     * Get single user by ID
     */
    async getById(id: string): Promise<IUser> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = (await api.get(`${this.baseUrl}/get/${institutionId}/${id}`)) as ApiResponse;
        return (response.user || response.data) as IUser;
    }

    /**
     * Create new user
     */
    async create(data: Omit<IUser, 'id' | 'created_at' | 'updated_at'>): Promise<IUser> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = (await api.post(`${this.baseUrl}/create`, data)) as ApiResponse;
        if (response.code === 200 && response.status === 'success') {
            return (response.user || response.data) as IUser;
        }
        throw new Error(response.message || 'Failed to create user');
    }

    /**
     * Update existing user
     */
    async update(id: string, data: Partial<IUser>): Promise<IUser> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = (await api.put(`${this.baseUrl}/update-institution/${institutionId}/${id}`, data)) as ApiResponse;
        if (response.code === 200 && response.status === 'success') {
            return (response.user || response.data) as IUser;
        }
        throw new Error(response.message || 'Failed to update user');
    }

    /**
     * Delete user
     */
    async delete(id: string): Promise<void> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        // Soft delete: inactive + login disabled; records kept, can be reactivated
        const response = (await api.delete(`${this.baseUrl}/delete/${institutionId}/${id}`)) as ApiResponse;
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response.message || 'Failed to delete user');
        }
    }

    /**
     * Reactivate a (soft-)deleted user: active again and login re-enabled
     */
    async reactivate(id: string): Promise<void> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = (await api.patch(`${this.baseUrl}/reactivate/${institutionId}/${id}`)) as ApiResponse;
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response.message || 'Failed to reactivate user');
        }
    }


    /**
     * Reset user password (admin only)
     */
    async resetPassword(id: string, newPassword: string): Promise<void> {
        const api = getApiClient();
        const institutionId = getInstitutionId();

        if (!institutionId) {
            throw new Error('Institution ID not found. Please log in again.');
        }

        const response = (await api.post(`${this.baseUrl}/${id}/reset-password/${institutionId}`, {
            new_password: newPassword,
        })) as ApiResponse;
        if (response.code !== 200 || response.status !== 'success') {
            throw new Error(response.message || 'Failed to reset password');
        }
    }

    /**
     * Activate user login (main DB)
     */
    async activateUser(mainUserId: string): Promise<any> {
        const api = getApiClient();
        const response = (await api.post(`${this.baseUrl}/${mainUserId}/activate`)) as ApiResponse;
        if (response.code === 200 && response.status === 'success') {
            return response;
        }
        throw new Error(response.message || 'Failed to activate user');
    }

    /**
     * Deactivate user login (main DB)
     */
    async deactivateUser(mainUserId: string): Promise<any> {
        const api = getApiClient();
        const response = (await api.post(`${this.baseUrl}/${mainUserId}/deactivate`)) as ApiResponse;
        if (response.code === 200 && response.status === 'success') {
            return response;
        }
        throw new Error(response.message || 'Failed to deactivate user');
    }

    /**
     * Provision login for a single institution user (STUDENT/PARENT)
     */
    async provisionLogin(data: {
        institution_user_id: number;
        skid: string;
        institution_id: number;
        password: string;
    }): Promise<any> {
        const api = getApiClient();
        const response = (await api.post(`${this.baseUrl}/provision-login`, data)) as any;
        if (response.code === 200 && response.status === 'success') {
            return response;
        }
        throw new Error(response.message || 'Failed to provision login');
    }

    /**
     * Bulk provision logins for STUDENT/PARENT users
     */
    async provisionBulkLogins(data: {
        skid: string;
        institution_id: number;
        default_password: string;
        role_filter?: string;
    }): Promise<any> {
        const api = getApiClient();
        const response = (await api.post(`${this.baseUrl}/provision-bulk-logins`, data)) as any;
        if (response.code === 200 && response.status === 'success') {
            return response.data;
        }
        throw new Error(response.message || 'Failed to provision bulk logins');
    }

    /**
     * Get provisioning report for export
     */
    async getProvisioningReport(skid: string, institutionId: number): Promise<any> {
        const api = getApiClient();
        const response = (await api.get(`${this.baseUrl}/provisioning-report/${skid}/${institutionId}`)) as any;
        if (response.code === 200 && response.status === 'success') {
            return response.data;
        }
        throw new Error(response.message || 'Failed to get provisioning report');
    }
}

// Export singleton instance
export const userService = new UserService();
