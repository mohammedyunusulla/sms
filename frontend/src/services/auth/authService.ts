/**
 * Authentication Service
 * Handles all authentication-related API calls
 */

import { getApiClient, setAuthToken, clearAuthToken } from '../api/client';
import { API_ENDPOINTS, API_CONFIG } from '../api/config';
import {
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RefreshTokenResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
} from '../../types/auth';

const client = getApiClient();

export const authService = {
    /**
     * Login user
     * @param credentials - Login credentials (identifier: email/username, password)
     */
    async login(credentials: LoginRequest): Promise<LoginResponse> {
        try {
            // Note: Response interceptor returns response.data directly, so we need type assertion
            const response = (await client.post<LoginResponse>(
                API_ENDPOINTS.AUTH.LOGIN,
                {
                    identifier: credentials.identifier,
                    password: credentials.password,
                }
            )) as unknown as LoginResponse;

            // Store tokens from response
            if (response.access_token) {
                setAuthToken(response.access_token);
            }
            if (response.refresh_token) {
                localStorage.setItem('refreshToken', response.refresh_token);
            }

            return response;
        } catch (error) {
            throw error;
        }
    },

    /**
     * Logout user
     */
    async logout(): Promise<LogoutResponse> {
        try {
            // Note: Response interceptor returns response.data directly, so we need type assertion
            const response = (await client.post<LogoutResponse>(
                API_ENDPOINTS.AUTH.LOGOUT
            )) as unknown as LogoutResponse;

            // Clear tokens
            clearAuthToken();

            return response;
        } catch (error) {
            // Clear tokens even if API call fails
            clearAuthToken();
            throw error;
        }
    },

    /**
     * Refresh access token.
     * Sends the refresh token via Authorization header (required by Flask-JWT-Extended).
     * The backend rotates both access and refresh tokens for security.
     */
    async refreshToken(): Promise<RefreshTokenResponse> {
        try {
            const refreshToken = localStorage.getItem('refreshToken');
            if (!refreshToken) {
                throw new Error('No refresh token available');
            }

            // Use raw axios to send refresh token in Authorization header
            // (not the intercepted client, to avoid infinite 401 loops)
            const { default: axios } = await import('axios');
            const response = await axios.post<RefreshTokenResponse>(
                `${API_CONFIG.BASE_URL}${API_ENDPOINTS.AUTH.REFRESH_TOKEN}`,
                {},
                {
                    headers: {
                        Authorization: `Bearer ${refreshToken}`,
                        'Content-Type': 'application/json',
                    },
                }
            );

            const data = response.data;

            // Update tokens from response
            if (data.access_token) {
                setAuthToken(data.access_token);
            }
            if (data.refresh_token) {
                localStorage.setItem('refreshToken', data.refresh_token);
            }

            return data;
        } catch (error) {
            clearAuthToken();
            throw error;
        }
    },

    /**
     * Forgot password
     */
    async forgotPassword(
        request: ForgotPasswordRequest
    ): Promise<ForgotPasswordResponse> {
        try {
            // Note: Response interceptor returns response.data directly, so we need type assertion
            const response = (await client.post<ForgotPasswordResponse>(
                API_ENDPOINTS.AUTH.FORGOT_PASSWORD,
                request
            )) as unknown as ForgotPasswordResponse;
            return response;
        } catch (error) {
            throw error;
        }
    },

    /**
     * Reset password
     */
    async resetPassword(
        request: ResetPasswordRequest
    ): Promise<ResetPasswordResponse> {
        try {
            // Note: Response interceptor returns response.data directly, so we need type assertion
            const response = (await client.post<ResetPasswordResponse>(
                API_ENDPOINTS.AUTH.RESET_PASSWORD,
                request
            )) as unknown as ResetPasswordResponse;
            return response;
        } catch (error) {
            throw error;
        }
    },

    /**
     * The logged-in user's own account (GET /auth/me)
     */
    async getMe(): Promise<Record<string, unknown>> {
        const response = (await getApiClient().get('/auth/me')) as unknown as { user?: Record<string, unknown> };
        return response.user || {};
    },

    /**
     * The logged-in user's current role and its permissions (GET /auth/me), to keep the menu in step
     * when an admin changes the role's tick boxes.
     */
    async getMyRole(): Promise<Record<string, unknown> | null> {
        const response = (await getApiClient().get('/auth/me')) as unknown as { role_obj?: Record<string, unknown> | null };
        return response.role_obj ?? null;
    },

    /**
     * The role (as getMyRole) plus the institution's feature and sign-in switches, in one call.
     */
    async getMyAccess(): Promise<{ role: Record<string, unknown> | null; features?: string[]; login_roles?: string[] }> {
        const response = (await getApiClient().get('/auth/me')) as unknown as {
            role_obj?: Record<string, unknown> | null;
            user?: { features?: string[]; login_roles?: string[] };
        };
        return { role: response.role_obj ?? null, features: response.user?.features, login_roles: response.user?.login_roles };
    },

    /**
     * Update the logged-in user's own first name, last name and phone (PUT /auth/me)
     */
    async updateMe(data: { first_name: string; last_name: string; phone: string | null }): Promise<Record<string, unknown>> {
        const response = (await getApiClient().put('/auth/me', data)) as unknown as { user?: Record<string, unknown> };
        return response.user || {};
    },

    /**
     * Change the logged-in user's password (POST /auth/change-password)
     */
    async changePassword(oldPassword: string, newPassword: string): Promise<string> {
        const response = (await getApiClient().post('/auth/change-password', {
            old_password: oldPassword,
            new_password: newPassword,
        })) as unknown as { message?: string };
        return response.message || 'Password changed successfully';
    },

    /**
     * Get stored user from localStorage
     */
    getStoredUser() {
        const userStr = localStorage.getItem('loggedUser');
        if (!userStr) return null;
        try {
            const user = JSON.parse(userStr);
            // A sign-in saved before the "school" -> "institution" rename has old field names and an old
            // role code: treat it as signed out so the person signs in again (the old name is spelled in
            // two parts so a future text rename can't change this check).
            if (user && typeof user === 'object' && ('sch' + 'ool_id') in user) {
                ['authToken', 'refreshToken', 'loggedUser', 'parentSelectedChild'].forEach((k) => localStorage.removeItem(k));
                return null;
            }
            return user;
        } catch {
            return null;
        }
    },

    /**
     * Store user in localStorage
     */
    storeUser(user: any) {
        localStorage.setItem('loggedUser', JSON.stringify(user));
    },

    /**
     * Clear stored user
     */
    clearStoredUser() {
        localStorage.removeItem('loggedUser');
        localStorage.removeItem('parentSelectedChild');
    },

    /**
     * Check if user is authenticated
     */
    isAuthenticated(): boolean {
        const token = localStorage.getItem('authToken');
        return !!token;
    },

    /**
     * Get auth token
     */
    getAuthToken(): string | null {
        return localStorage.getItem('authToken');
    },
};
