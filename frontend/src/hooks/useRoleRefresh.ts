/**
 * Keeps the signed-in user's role permissions (and so the menu) in step with the server:
 * re-reads the role every minute and when the tab gets focus, and updates the stored user if an admin
 * changed the role's tick boxes. The server applies the same ticks within a minute (A15).
 * The same call brings the institution's feature and sign-in switches (config/features.ts), so the menu
 * also follows what the Super Admin switches on or off.
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

const sameList = (a?: string[], b?: string[]) =>
    b === undefined || JSON.stringify([...(a || [])].sort()) === JSON.stringify([...b].sort());

export const useRoleRefresh = () => {
    const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

    useEffect(() => {
        if (!isAuthenticated) return;
        let busy = false;
        const refresh = async () => {
            const user = useAuthStore.getState().user;
            if (busy || !user || !user.role_obj) return; // Super Admin has no institution role
            busy = true;
            try {
                const access = await authService.getMyAccess();
                const latest = access.role as RoleObj | null;
                const roleChanged = !!latest && !sameRole(user.role_obj, latest);
                const switchesChanged = !sameList(user.features, access.features) || !sameList(user.login_roles, access.login_roles);
                if (roleChanged || switchesChanged) {
                    useAuthStore.getState().setUser({
                        ...user,
                        role_obj: roleChanged && latest ? { ...user.role_obj, ...latest } : user.role_obj,
                        features: access.features ?? user.features,
                        login_roles: access.login_roles ?? user.login_roles,
                    } as AuthUser);
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
