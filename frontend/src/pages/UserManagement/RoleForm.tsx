/**
 * Role Form Component
 * Form for creating and editing roles with permissions assignment
 */

import { FC, useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { useNavigate, useParams } from 'react-router';
import { PageHeader, Button, LoadingSpinner } from '../../components';
import { roleService } from '../../services/modules/roleService';
import { Permission } from '../../config/permissions';

// Permissions grouped by module, stored as flat string arrays in the backend Role.permissions column.
// Every permission the app checks (the Permission enum) must have a tick box here: the check below fails
// the type check (npm run build) if one is missing. Permissions a role holds that aren't listed are kept on save.
const PERMISSION_GROUPS = [
    {
        module: 'User Management',
        permissions: [
            { key: Permission.VIEW_USERS, label: 'View Users' },
            { key: Permission.MANAGE_USERS, label: 'Create / Edit Users' },
            { key: Permission.DELETE_USERS, label: 'Delete Users' },
        ],
    },
    {
        module: 'Student Management',
        permissions: [
            { key: Permission.VIEW_STUDENTS, label: 'View Students' },
            { key: Permission.MANAGE_STUDENTS, label: 'Create / Edit Students' },
            { key: Permission.DELETE_STUDENTS, label: 'Delete Students' },
        ],
    },
    {
        module: 'Teacher Management',
        permissions: [
            { key: Permission.VIEW_TEACHERS, label: 'View Teachers' },
            { key: Permission.MANAGE_TEACHERS, label: 'Create / Edit Teachers' },
            { key: Permission.DELETE_TEACHERS, label: 'Delete Teachers' },
        ],
    },
    {
        module: 'Class & Section',
        permissions: [
            { key: Permission.VIEW_CLASSES, label: 'View Classes & Sections' },
            { key: Permission.MANAGE_CLASSES, label: 'Create / Edit Classes & Sections' },
        ],
    },
    {
        module: 'Attendance',
        permissions: [
            { key: Permission.VIEW_ATTENDANCE, label: 'View Attendance' },
            { key: Permission.MANAGE_ATTENDANCE, label: 'Mark / Edit Attendance' },
            { key: Permission.APPROVE_LEAVE, label: 'Approve Leave (all students and staff; class teachers approve their own class without this)' },
        ],
    },
    {
        module: 'Timetable',
        permissions: [
            { key: Permission.VIEW_TIMETABLE, label: 'View Timetable' },
            { key: Permission.MANAGE_TIMETABLE, label: 'Create / Edit Timetable' },
        ],
    },
    {
        module: 'Exams & Marks',
        permissions: [
            { key: Permission.VIEW_EXAMS, label: 'View Exams & Marks' },
            { key: Permission.MANAGE_EXAMS, label: 'Create / Edit Exams' },
            { key: Permission.MANAGE_ROOMS, label: 'Exam Rooms' },
            { key: Permission.MANAGE_MARKS, label: 'Enter / Edit Marks' },
            { key: Permission.VIEW_MARKS, label: 'View Marks (own / class results)' },
        ],
    },
    {
        module: 'Finance',
        permissions: [
            { key: Permission.VIEW_FEES, label: 'View Fees & Payments' },
            { key: Permission.MANAGE_FEES, label: 'Manage Fee Structure & Collection' },
            { key: Permission.VIEW_EXPENSES, label: 'View Expenses' },
            { key: Permission.MANAGE_EXPENSES, label: 'Create / Edit Expenses' },
            { key: Permission.MANAGE_FEE_SETTINGS, label: 'Fee Settings & Corrections (structures, installments, discounts, cancel payments)' },
            { key: Permission.MANAGE_SALARIES, label: 'Salary Setup & Payments' },
        ],
    },
    {
        module: 'Announcements',
        permissions: [
            { key: Permission.VIEW_ANNOUNCEMENTS, label: 'View Announcements' },
            { key: Permission.MANAGE_ANNOUNCEMENTS, label: 'Create / Edit Announcements' },
        ],
    },
    {
        module: 'Assignments',
        permissions: [
            { key: Permission.VIEW_ASSIGNMENTS, label: 'View Assignments' },
            { key: Permission.MANAGE_ASSIGNMENTS, label: 'Create / Edit / Review Assignments' },
        ],
    },
    {
        module: 'Syllabus',
        permissions: [
            { key: Permission.VIEW_SYLLABUS_AND_PROGRESS, label: 'View Syllabus & Progress' },
            { key: Permission.MANAGE_SYLLABUS, label: 'Create / Edit Syllabus' },
        ],
    },
    {
        module: 'Administration',
        permissions: [
            { key: Permission.MANAGE_ROLES, label: 'Manage Roles & Permissions' },
            { key: Permission.MANAGE_ACADEMIC_YEARS, label: 'Manage Academic Years' },
        ],
    },
    {
        module: 'Student - Own Pages',
        permissions: [
            { key: Permission.VIEW_MY_TIMETABLE, label: 'My Timetable' },
        ],
    },
    {
        module: "Parent - Child's Pages",
        permissions: [
            { key: Permission.VIEW_CHILD_ASSIGNMENTS, label: "My Child's Assignments" },
            { key: Permission.VIEW_CHILD_TIMETABLE, label: "My Child's Timetable" },
            { key: Permission.VIEW_CHILD_FEES, label: "My Child's Fees" },
            { key: Permission.VIEW_CHILD_SYLLABUS, label: "My Child's Syllabus" },
        ],
    },
    {
        module: 'Bus Scan',
        permissions: [
            { key: Permission.VIEW_BUS_SCAN, label: 'View Bus Scan' },
            { key: Permission.MANAGE_BUS_SCAN, label: 'Scan QR & Manage Bus Scan' },
        ],
    },
] as const;

// A custom role is stored on login accounts as one of these built-in staff roles (backend CUSTOM_ROLE_BASES)
const BASE_ROLE_OPTIONS = [
    { value: 'PRINCIPAL', label: 'Principal' },
    { value: 'CLERK', label: 'Clerk (fee counter)' },
    { value: 'BUS_STAFF', label: 'Bus Staff' },
];

type ListedPermission = (typeof PERMISSION_GROUPS)[number]['permissions'][number]['key'];
type UnlistedPermission = Exclude<Permission, ListedPermission>;
// If this line errors, add the permission named in the error to PERMISSION_GROUPS above.
const everyPermissionListed: [UnlistedPermission] extends [never] ? true : UnlistedPermission = true;
void everyPermissionListed;

const RoleForm: FC = () => {
    const navigate = useNavigate();
    const { id } = useParams();
    const isEditMode = !!id;

    const [loading, setLoading] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);
    const [formData, setFormData] = useState({
        role_name: '',
        role_code: '',
        description: '',
        base_role: '',
    });
    // Built-in roles are fixed; custom roles are "based on" a built-in staff role
    const [isSystemRole, setIsSystemRole] = useState(false);

    useEffect(() => {
        if (isEditMode && id) {
            fetchRole();
        }
    }, [id]);

    const fetchRole = async () => {
        try {
            setLoading(true);
            const role = await roleService.getById(id!);
            setFormData({
                role_name: role.role_name || '',
                role_code: role.role_code || '',
                description: role.description || '',
                base_role: role.base_role || '',
            });
            setIsSystemRole(!!role.is_system_role);
            setSelectedPermissions(role.permissions || []);
        } catch (error: any) {
            console.error('Error fetching role:', error);
            toast.error(error.message || 'Failed to fetch role');
        } finally {
            setLoading(false);
        }
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const generateRoleCode = (name: string) => {
        return name.trim().toUpperCase().replace(/\s+/g, '_').replace(/[^A-Z0-9_]/g, '');
    };

    const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { value } = e.target;
        setFormData(prev => ({
            ...prev,
            role_name: value,
            // Auto-generate role_code only in create mode
            ...(!isEditMode ? { role_code: generateRoleCode(value) } : {}),
        }));
    };

    const togglePermission = (key: string) => {
        setSelectedPermissions(prev =>
            prev.includes(key) ? prev.filter(p => p !== key) : [...prev, key]
        );
    };

    const toggleModuleAll = (modulePerms: readonly { key: string }[]) => {
        const keys = modulePerms.map(p => p.key);
        const allSelected = keys.every(k => selectedPermissions.includes(k));
        if (allSelected) {
            setSelectedPermissions(prev => prev.filter(p => !keys.includes(p)));
        } else {
            setSelectedPermissions(prev => [...new Set([...prev, ...keys])]);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!formData.role_name.trim()) {
            toast.error('Role name is required');
            return;
        }
        if (!formData.role_code.trim()) {
            toast.error('Role code is required');
            return;
        }
        if (!isSystemRole && !formData.base_role) {
            toast.error('Choose what the role is based on');
            return;
        }

        try {
            setIsSubmitting(true);
            if (isEditMode) {
                // built-in roles: only their permissions can change
                if (!isSystemRole) {
                    await roleService.update(id!, {
                        role_name: formData.role_name,
                        description: formData.description,
                        base_role: formData.base_role,
                    });
                }
                await roleService.assignPermissions(id!, selectedPermissions);
                toast.success('Role updated successfully');
            } else {
                const created = await roleService.create({
                    role_name: formData.role_name,
                    role_code: formData.role_code,
                    description: formData.description,
                    base_role: formData.base_role,
                });
                if (created?.id && selectedPermissions.length > 0) {
                    await roleService.assignPermissions(created.id, selectedPermissions);
                }
                toast.success('Role created successfully');
            }
            navigate('/roles');
        } catch (error: any) {
            toast.error(error.message || 'Failed to save role');
        } finally {
            setIsSubmitting(false);
        }
    };

    if (loading) {
        return <LoadingSpinner fullHeight message="Loading role..." />;
    }

    return (
        <div className="space-y-6">
            <PageHeader
                title={isEditMode ? 'Edit Role' : 'Create Role'}
                subtitle="Manage role information and permissions"
                breadcrumbs={[
                    { label: 'Dashboard', href: '/dashboard' },
                    { label: 'Roles', href: '/roles' },
                    { label: isEditMode ? 'Edit' : 'Create', href: '#' },
                ]}
            />

            <form onSubmit={handleSubmit}>
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Role Details */}
                    <div className="lg:col-span-1 bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 space-y-5 self-start">
                        <h3 className="text-base font-semibold text-gray-900 dark:text-white">Role Details</h3>
                        {isSystemRole && (
                            <p className="text-sm text-amber-700 dark:text-amber-400" data-testid="built-in-note">
                                Built-in role: its name and description can't be changed. Only its permissions can.
                            </p>
                        )}

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                                Role Name <span className="text-red-500">*</span>
                            </label>
                            <input
                                type="text"
                                name="role_name"
                                value={formData.role_name}
                                onChange={handleNameChange}
                                disabled={isSystemRole}
                                className="disabled:opacity-60 disabled:cursor-not-allowed w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                placeholder="e.g. Class Teacher"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                                Role Code <span className="text-red-500">*</span>
                            </label>
                            <input
                                type="text"
                                name="role_code"
                                value={formData.role_code}
                                onChange={handleInputChange}
                                disabled={isEditMode}
                                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-60 disabled:cursor-not-allowed focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                placeholder="e.g. CLASS_TEACHER"
                            />
                            {isEditMode && (
                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Role code cannot be changed</p>
                            )}
                        </div>

                        {!isSystemRole && (
                            <div>
                                <label htmlFor="base_role" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                                    Based on <span className="text-red-500">*</span>
                                </label>
                                <select
                                    id="base_role"
                                    name="base_role"
                                    value={formData.base_role}
                                    onChange={(e) => setFormData((prev) => ({ ...prev, base_role: e.target.value }))}
                                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                >
                                    <option value="">Choose a built-in role</option>
                                    {BASE_ROLE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                                </select>
                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                    People with this role sign in as this built-in role: it decides their dashboard and what the
                                    server allows them to do. The tick boxes below decide their menu, so ticking a page the
                                    built-in role can't use will show it but it won't load. Can't be changed once people have the role.
                                </p>
                            </div>
                        )}

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                                Description
                            </label>
                            <textarea
                                name="description"
                                value={formData.description}
                                onChange={handleInputChange}
                                disabled={isSystemRole}
                                rows={3}
                                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                placeholder="Describe what this role can do"
                            />
                        </div>

                        <div className="flex gap-3 justify-end pt-2">
                            <Button variant="secondary" type="button" onClick={() => navigate('/roles')}>
                                Cancel
                            </Button>
                            <Button variant="primary" type="submit" disabled={isSubmitting}>
                                {isSubmitting ? 'Saving...' : isEditMode ? 'Update Role' : 'Create Role'}
                            </Button>
                        </div>
                    </div>

                    {/* Permissions Section */}
                    <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 self-start">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-base font-semibold text-gray-900 dark:text-white">Permissions</h3>
                            <span className="text-sm text-gray-500 dark:text-gray-400">
                                {selectedPermissions.length} selected
                            </span>
                        </div>

                        <div className="space-y-4 max-h-[540px] overflow-y-auto pr-1">
                            {PERMISSION_GROUPS.map((group) => {
                                const allKeys = group.permissions.map(p => p.key);
                                const allSelected = allKeys.every(k => selectedPermissions.includes(k));
                                const someSelected = allKeys.some(k => selectedPermissions.includes(k));

                                return (
                                    <div key={group.module} className="border border-gray-200 dark:border-gray-700 rounded-lg">
                                        {/* Module header */}
                                        <label className="flex items-center gap-3 px-4 py-2.5 bg-gray-50 dark:bg-gray-700/50 rounded-t-lg cursor-pointer select-none">
                                            <input
                                                type="checkbox"
                                                checked={allSelected}
                                                ref={(el) => { if (el) el.indeterminate = someSelected && !allSelected; }}
                                                onChange={() => toggleModuleAll(group.permissions)}
                                                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                            />
                                            <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                                                {group.module}
                                            </span>
                                        </label>
                                        {/* Individual permissions */}
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 px-4 py-2.5">
                                            {group.permissions.map((perm) => (
                                                <label
                                                    key={perm.key}
                                                    className="flex items-center gap-2.5 py-1.5 cursor-pointer select-none"
                                                >
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedPermissions.includes(perm.key)}
                                                        onChange={() => togglePermission(perm.key)}
                                                        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                                    />
                                                    <span className="text-sm text-gray-700 dark:text-gray-300">
                                                        {perm.label}
                                                    </span>
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </form>
        </div>
    );
};

export default RoleForm;
