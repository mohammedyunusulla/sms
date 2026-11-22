/**
 * My Profile
 * The logged-in user's own account: details (first/last name, phone are editable) and password change.
 * Backend: GET/PUT /auth/me, POST /auth/change-password.
 */
import { FC, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import PageMeta from '../components/common/PageMeta';
import { PageHeader, Button, Badge, PasswordToggleButton } from '../components';
import { authService } from '../services/auth/authService';
import { useAuthStore } from '../stores/authStore';
import { fieldInputClass, isValidPhone, passwordProblem } from '../utils/formValidation';

interface Account {
    username?: string;
    email?: string;
    first_name?: string;
    last_name?: string;
    phone?: string | null;
    role?: string;
    last_login?: string | null;
    created_at?: string | null;
}

const ROLE_LABELS: Record<string, string> = {
    SUPER_ADMIN: 'Super Admin', SCHOOL_ADMIN: 'School Admin', PRINCIPAL: 'Principal', TEACHER: 'Teacher',
    STUDENT: 'Student', PARENT: 'Parent', BUS_STAFF: 'Bus Staff',
};

const formatDateTime = (value?: string | null) => {
    if (!value) return '—';
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
};

// Same password rule as every other form (backend: app/utils/helpers.validate_password)
const newPasswordProblem = passwordProblem;

const errorMessage = (err: unknown, fallback: string) => (err as { message?: string })?.message || fallback;

const UserProfiles: FC = () => {
    const authUser = useAuthStore((s) => s.user);
    const setUser = useAuthStore((s) => s.setUser);

    const [account, setAccount] = useState<Account | null>(null);
    const [loadError, setLoadError] = useState<string | null>(null);

    // personal details
    const [editing, setEditing] = useState(false);
    const [details, setDetails] = useState({ first_name: '', last_name: '', phone: '' });
    const [detailErrors, setDetailErrors] = useState<Record<string, string>>({});
    const [savingDetails, setSavingDetails] = useState(false);

    // password
    const [passwords, setPasswords] = useState({ current: '', next: '', confirm: '' });
    const [passwordErrors, setPasswordErrors] = useState<Record<string, string>>({});
    const [show, setShow] = useState({ current: false, next: false, confirm: false });
    const [savingPassword, setSavingPassword] = useState(false);

    const load = async () => {
        setLoadError(null);
        try {
            const me = (await authService.getMe()) as Account;
            setAccount(me);
            setDetails({ first_name: me.first_name || '', last_name: me.last_name || '', phone: me.phone || '' });
        } catch (err) {
            setLoadError(errorMessage(err, 'Failed to load your profile'));
        }
    };

    useEffect(() => { load(); }, []);

    const saveDetails = async () => {
        const found: Record<string, string> = {};
        if (!details.first_name.trim()) found.first_name = 'First name is required';
        if (!details.last_name.trim()) found.last_name = 'Last name is required';
        if (details.phone.trim() && !isValidPhone(details.phone)) found.phone = 'Enter a 10-digit phone number';
        setDetailErrors(found);
        if (Object.keys(found).length) return;
        setSavingDetails(true);
        try {
            const updated = (await authService.updateMe({
                first_name: details.first_name.trim(),
                last_name: details.last_name.trim(),
                phone: details.phone.trim() || null,
            })) as Account;
            setAccount((prev) => ({ ...prev, ...updated }));
            // keep the header/top bar in step without a reload
            if (authUser) {
                setUser({
                    ...authUser,
                    first_name: String(updated.first_name ?? authUser.first_name),
                    last_name: String(updated.last_name ?? authUser.last_name),
                    full_name: `${updated.first_name ?? authUser.first_name} ${updated.last_name ?? authUser.last_name}`.trim(),
                    phone: String(updated.phone ?? ''),
                });
            }
            setEditing(false);
            toast.success('Profile updated');
        } catch (err) {
            toast.error(errorMessage(err, 'Failed to update profile'));
        } finally {
            setSavingDetails(false);
        }
    };

    const cancelEdit = () => {
        setDetails({ first_name: account?.first_name || '', last_name: account?.last_name || '', phone: account?.phone || '' });
        setDetailErrors({});
        setEditing(false);
    };

    const changePassword = async () => {
        const found: Record<string, string> = {};
        if (!passwords.current) found.current = 'Current password is required';
        const problem = newPasswordProblem(passwords.next);
        if (problem) found.next = problem;
        else if (passwords.next === passwords.current) found.next = 'New password must be different from the current one';
        if (!passwords.confirm) found.confirm = 'Confirm the new password';
        else if (passwords.confirm !== passwords.next) found.confirm = 'Passwords do not match';
        setPasswordErrors(found);
        if (Object.keys(found).length) return;
        setSavingPassword(true);
        try {
            const message = await authService.changePassword(passwords.current, passwords.next);
            toast.success(message);
            setPasswords({ current: '', next: '', confirm: '' });
        } catch (err) {
            const message = errorMessage(err, 'Failed to change password');
            if (/current password/i.test(message)) setPasswordErrors({ current: message });
            toast.error(message);
        } finally {
            setSavingPassword(false);
        }
    };

    const fieldError = (errors: Record<string, string>, name: string) =>
        errors[name] ? <p role="alert" className="mt-1 text-sm text-red-600 dark:text-red-400">{errors[name]}</p> : null;

    const passwordField = (key: 'current' | 'next' | 'confirm', label: string, autoComplete: string) => (
        <div>
            <label htmlFor={`password-${key}`} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">{label}</label>
            <div className="relative">
                <input
                    id={`password-${key}`}
                    name={`password_${key}`}
                    type={show[key] ? 'text' : 'password'}
                    value={passwords[key]}
                    onChange={(e) => {
                        setPasswords((p) => ({ ...p, [key]: e.target.value }));
                        if (passwordErrors[key]) setPasswordErrors((errs) => { const n = { ...errs }; delete n[key]; return n; });
                    }}
                    autoComplete={autoComplete}
                    className={`${fieldInputClass(!!passwordErrors[key])} pr-11`}
                    aria-invalid={!!passwordErrors[key]}
                />
                <PasswordToggleButton visible={show[key]} onToggle={() => setShow((s) => ({ ...s, [key]: !s[key] }))} />
            </div>
            {fieldError(passwordErrors, key)}
        </div>
    );

    const name = `${account?.first_name ?? ''} ${account?.last_name ?? ''}`.trim();
    const initials = `${account?.first_name?.[0] ?? ''}${account?.last_name?.[0] ?? ''}`.toUpperCase() || '?';

    return (
        <div className="space-y-6">
            <PageMeta title="My Profile | EduSpyre - Education Management System" description="Your EduSpyre account" />
            <PageHeader title="My Profile" subtitle="Your account details and password" />

            {loadError ? (
                <div className="p-4 rounded-lg border border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
                    {loadError} <Button variant="secondary" size="sm" className="ml-3" onClick={load}>Retry</Button>
                </div>
            ) : !account ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">Loading…</p>
            ) : (
                <>
                    {/* Header */}
                    <div className="flex flex-col sm:flex-row sm:items-center gap-4 p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-blue-100 text-xl font-semibold text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
                            {initials}
                        </div>
                        <div className="flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                                <h2 className="text-xl font-semibold text-gray-900 dark:text-white" data-testid="profile-name">{name}</h2>
                                {account.role && <Badge variant="primary" size="sm">{ROLE_LABELS[account.role] || account.role}</Badge>}
                            </div>
                            <p className="text-sm text-gray-600 dark:text-gray-400" data-testid="profile-email">{account.email}</p>
                        </div>
                        <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
                            <dt className="text-gray-500 dark:text-gray-400">Last login</dt>
                            <dd className="text-gray-900 dark:text-white">{formatDateTime(account.last_login)}</dd>
                            <dt className="text-gray-500 dark:text-gray-400">Member since</dt>
                            <dd className="text-gray-900 dark:text-white">{formatDateTime(account.created_at)}</dd>
                        </dl>
                    </div>

                    {/* Personal details */}
                    <div className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                        <div className="flex items-center justify-between mb-5">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Personal details</h3>
                            {!editing && <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>Edit</Button>}
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {(['first_name', 'last_name', 'phone'] as const).map((key) => (
                                <div key={key}>
                                    <label htmlFor={`profile-${key}`} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                        {{ first_name: 'First name', last_name: 'Last name', phone: 'Phone' }[key]}
                                        {key !== 'phone' && editing && <span className="text-red-500"> *</span>}
                                    </label>
                                    {editing ? (
                                        <>
                                            <input
                                                id={`profile-${key}`}
                                                name={key}
                                                type={key === 'phone' ? 'tel' : 'text'}
                                                value={details[key]}
                                                onChange={(e) => {
                                                    setDetails((d) => ({ ...d, [key]: e.target.value }));
                                                    if (detailErrors[key]) setDetailErrors((errs) => { const n = { ...errs }; delete n[key]; return n; });
                                                }}
                                                className={fieldInputClass(!!detailErrors[key])}
                                                aria-invalid={!!detailErrors[key]}
                                            />
                                            {fieldError(detailErrors, key)}
                                        </>
                                    ) : (
                                        <p className="text-gray-900 dark:text-white" data-testid={`profile-${key}`}>{(account[key] as string) || '—'}</p>
                                    )}
                                </div>
                            ))}
                            <div>
                                <p className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Username</p>
                                <p className="text-gray-900 dark:text-white">{account.username}</p>
                            </div>
                            <div className="md:col-span-2">
                                <p className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Email</p>
                                <p className="text-gray-900 dark:text-white">{account.email}</p>
                                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Username and email can only be changed by the school office.</p>
                            </div>
                        </div>
                        {editing && (
                            <div className="flex gap-3 mt-6">
                                <Button variant="secondary" onClick={cancelEdit} disabled={savingDetails}>Cancel</Button>
                                <Button variant="primary" onClick={saveDetails} disabled={savingDetails}>{savingDetails ? 'Saving…' : 'Save changes'}</Button>
                            </div>
                        )}
                    </div>

                    {/* Change password */}
                    <div className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Change password</h3>
                        <p className="mb-5 text-sm text-gray-500 dark:text-gray-400">
                            At least 8 characters, with an uppercase letter, a lowercase letter and a digit.
                        </p>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            {passwordField('current', 'Current password', 'current-password')}
                            {passwordField('next', 'New password', 'new-password')}
                            {passwordField('confirm', 'Confirm new password', 'new-password')}
                        </div>
                        <div className="mt-6">
                            <Button variant="primary" onClick={changePassword} disabled={savingPassword}>
                                {savingPassword ? 'Changing…' : 'Change password'}
                            </Button>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

export default UserProfiles;
