/**
 * PermissionGuard
 * Wraps route elements and redirects to /dashboard if the user lacks permission.
 * Acts as a safety net — the sidebar already hides items the user can't access,
 * but this prevents direct URL navigation to restricted routes.
 */

import { ReactNode } from 'react';
import { Navigate } from 'react-router';
import { usePermissions } from '../../hooks/usePermissions';
import { Permission, isPathHiddenForRole } from '../../config/permissions';
import { useAuthStore } from '../../stores/authStore';

interface PermissionGuardProps {
  children: ReactNode;
  /** Required permission key. Ignored if superAdminOnly is true. */
  permission?: Permission;
  /** Access granted if user has ANY of these permissions (OR logic) */
  anyPermission?: Permission[];
  /** If true, only SUPER_ADMIN can access this route. */
  superAdminOnly?: boolean;
  /** The route path, to apply ROLE_HIDDEN_PATHS. */
  path?: string;
}

export const PermissionGuard = ({
  children,
  permission,
  anyPermission,
  superAdminOnly,
  path,
}: PermissionGuardProps) => {
  const { hasPermission, hasAnyPermission, isSuperAdmin } = usePermissions();
  const role = useAuthStore((state) => state.user?.role);

  if (path && isPathHiddenForRole(role, path)) {
    return <Navigate to="/dashboard" replace />;
  }

  if (superAdminOnly) {
    if (!isSuperAdmin) {
      return <Navigate to="/dashboard" replace />;
    }
    return <>{children}</>;
  }

  if (anyPermission && anyPermission.length > 0 && !hasAnyPermission(anyPermission)) {
    return <Navigate to="/dashboard" replace />;
  }

  if (permission && !hasPermission(permission)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};
