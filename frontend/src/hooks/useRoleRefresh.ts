/**
 * Keeps the signed-in user's role permissions (and so the menu) in step with the server:
 * re-reads the role every minute and when the tab gets focus, and updates the stored user if an admin
 * changed the role's tick boxes. The server applies the same ticks within a minute (A15).
 */
import { useEffect } from 'react';
import { useAuthStore } from '../stores/authStore';
import { authService } from '../services/auth/authService';
import type { AuthUser, RoleObj } from '../types/auth';

const EVERY_MS = 60_000;
const sameRole = (a?: RoleObj | null, b?: RoleObj | null) =>
    !!a && !!b &&
    a.id === b.id &&
    a.role_name === b.role_name &&
    a.is_active === b.is_active &&
    JSON.stringify([...(a.permissions || [])].sort()) === JSON.stringify([...(b.permissions || [])].sort());

export const useRoleRefresh = () => {
    const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

    useEffect(() => {
        if (!isAuthenticated) return;
        let busy = false;
        const refresh = async () => {
            const user = useAuthStore.getState().user;
            if (busy || !user || !user.role_obj) return; // Super Admin has no school role
            busy = true;
            try {
                const latest = (await authService.getMyRole()) as RoleObj | null;
                if (latest && !sameRole(user.role_obj, latest)) {
                    useAuthStore.getState().setUser({ ...user, role_obj: { ...user.role_obj, ...latest } } as AuthUser);
                }
            } catch {
                // offline / signed out: try again next time
            } finally {
                busy = false;
            }
        };
        const onFocus = () => { void refresh(); };
        const timer = window.setInterval(refresh, EVERY_MS);
        window.addEventListener('focus', onFocus);
        return () => {
            window.clearInterval(timer);
            window.removeEventListener('focus', onFocus);
        };
    }, [isAuthenticated]);
};
