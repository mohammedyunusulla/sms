/**
 * Teacher Form Component
 * Form for creating and editing teachers
 */

import { FC, useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { useNavigate, useParams } from 'react-router';
import { PageHeader, Button, LoadingSpinner, PasswordToggleButton } from '../../components';
import { teacherService } from '../../services/modules/teacherService';

interface ITeacherFormProps {
    initialData?: any;
    mode?: 'create' | 'update' | 'view';
}

const TeacherForm: FC<ITeacherFormProps> = ({ initialData, mode: propMode = 'create' }) => {
    const navigate = useNavigate();
    const { id } = useParams();
    const [loading, setLoading] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errors, setErrors] = useState<Record<string, string>>({});
    const [showPassword, setShowPassword] = useState(false);
    // Auto-detect mode based on URL - if id exists, it's update mode
    const mode = id ? 'update' : propMode;
    const [formData, setFormData] = useState({
        // Base user fields
        username: '',
        password: '',
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        gender: '',
        date_of_birth: '',
        address: '',
        has_login: false,
        is_active: true,
        // Teacher specific fields
        employee_id: '',
        designation: '',
        date_of_joining: '',
        salary: '',
        qualifications: '',
        role_id: 3, //TEACHER
        role: "TEACHER",
        ...initialData,
    });

    useEffect(() => {
        if (mode === 'update' && id) {
            fetchTeacher();
        }
    }, [id, mode]);

    const fetchTeacher = async () => {
        try {
            setLoading(true);
            const response = await teacherService.getById(id!);
            // Teacher-specific fields come nested under `profile`; date inputs need YYYY-MM-DD
            const profile = response?.profile || {};
            const toDateInput = (value: unknown) => {
                if (!value) return '';
                const text = String(value);
                if (/^\d{4}-\d{2}-\d{2}/.test(text)) return text.slice(0, 10);
                const parsed = new Date(text);
                return isNaN(parsed.getTime()) ? '' : parsed.toISOString().slice(0, 10);
            };
            setFormData((prev: typeof formData) => ({
                ...prev,
                username: response?.username ?? '',
                first_name: response?.first_name ?? '',
                last_name: response?.last_name ?? '',
                email: response?.email ?? '',
                phone: response?.phone ?? '',
                gender: response?.gender ?? '',
                date_of_birth: toDateInput(response?.date_of_birth),
                address: response?.address ?? '',
                is_active: response?.is_active ?? true,
                employee_id: profile.employee_id ?? '',
                designation: profile.designation ?? '',
                date_of_joining: toDateInput(profile.date_of_joining),
                salary: profile.salary != null ? String(profile.salary) : '',
                qualifications: profile.qualifications ?? '',
            }));
        } catch (error) {
            console.error('Error fetching teacher:', error);
            toast.error('Failed to fetch teacher');
        } finally {
            setLoading(false);
        }
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
        const { name, value, type } = e.target;
        setFormData((prev: typeof formData) => ({
            ...prev,
            [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
        }));
        // Clear a field's error as soon as the user edits it
        if (errors[name]) {
            setErrors((prev) => {
                const next = { ...prev };
                delete next[name];
                return next;
            });
        }
    };

    // Every field is mandatory (password only when creating)
    const validate = (): Record<string, string> => {
        const v = (key: keyof typeof formData) => {
            const raw = String(formData[key] ?? '').trim();
            return key === 'date_of_birth' || key === 'date_of_joining' ? raw.slice(0, 10) : raw;
        };
        const next: Record<string, string> = {};
        if (!v('username')) next.username = 'Username is required';
        else if (v('username').length < 3) next.username = 'Username must be at least 3 characters';
        if (mode === 'create') {
            const pw = String(formData.password ?? '');
            if (!pw) next.password = 'Password is required';
            else if (pw.length < 8) next.password = 'Password must be at least 8 characters';
            else if (!/[A-Z]/.test(pw)) next.password = 'Password must contain an uppercase letter';
            else if (!/[a-z]/.test(pw)) next.password = 'Password must contain a lowercase letter';
            else if (!/[0-9]/.test(pw)) next.password = 'Password must contain a digit';
        }
        if (!v('first_name')) next.first_name = 'First name is required';
        if (!v('last_name')) next.last_name = 'Last name is required';
        if (!v('email')) next.email = 'Email is required';
        else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v('email'))) next.email = 'Enter a valid email address';
        if (!v('employee_id')) next.employee_id = 'Employee ID is required';
        if (!v('gender')) next.gender = 'Gender is required';
        const today = new Date().toISOString().slice(0, 10);
        if (!v('date_of_birth')) next.date_of_birth = 'Date of birth is required';
        else if (v('date_of_birth') >= today) next.date_of_birth = 'Date of birth must be in the past';
        if (!v('address')) next.address = 'Address is required';
        if (!v('designation')) next.designation = 'Designation is required';
        if (!v('date_of_joining')) next.date_of_joining = 'Date of joining is required';
        else if (v('date_of_joining') > today) next.date_of_joining = 'Date of joining cannot be in the future';
        else if (v('date_of_birth') && !next.date_of_birth && v('date_of_joining') <= v('date_of_birth')) next.date_of_joining = 'Date of joining must be after date of birth';
        if (!v('salary')) next.salary = 'Salary is required';
        else if (!(Number(v('salary')) > 0)) next.salary = 'Salary must be a positive number';
        if (!v('qualifications')) next.qualifications = 'Qualifications are required';
        if (!v('phone')) next.phone = 'Phone is required';
        else if (!/^\d{10}$/.test(v('phone').replace(/[\s-]/g, ''))) next.phone = 'Enter a 10-digit phone number';
        return next;
    };

    const inputClass = (name: string) =>
        `w-full px-4 py-2 border rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50 ${errors[name]
            ? 'border-red-500 dark:border-red-500 focus:ring-red-500'
            : 'border-gray-300 dark:border-gray-600'}`;

    const fieldError = (name: string) =>
        errors[name] ? <p id={`${name}-error`} role="alert" className="mt-1 text-sm text-red-600 dark:text-red-400">{errors[name]}</p> : null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        const found = validate();
        setErrors(found);
        if (Object.keys(found).length > 0) {
            const count = Object.keys(found).length;
            toast.error(`Please fix ${count} highlighted field${count > 1 ? 's' : ''}`);
            const first = document.querySelector<HTMLElement>(`[name="${Object.keys(found)[0]}"]`);
            first?.focus();
            return;
        }

        try {
            setIsSubmitting(true);
            if (mode === 'update' && id) {
                await teacherService.update(id, formData);
                toast.success('Teacher updated successfully');
            } else {
                await teacherService.create(formData);
                toast.success('Teacher created successfully');
            }
            navigate('/teachers');
        } catch (error: any) {
            toast.error(error.message || 'Failed to save teacher');
        } finally {
            setIsSubmitting(false);
        }
    };

    if (loading) {
        return <LoadingSpinner fullHeight message="Loading teacher..." />;
    }

    const isViewMode = mode === 'view';

    return (
        <div className="space-y-6">
            <PageHeader
                title={mode === 'create' ? 'Create Teacher' : mode === 'update' ? 'Edit Teacher' : 'View Teacher'}
                subtitle="Manage teacher information"
                breadcrumbs={[
                    { label: 'Dashboard', href: '/dashboard' },
                    { label: 'Teachers', href: '/teachers' },
                    { label: mode === 'create' ? 'Create' : 'Edit', href: '#' },
                ]}
            />

            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
                <form onSubmit={handleSubmit} noValidate className="space-y-8">
                    {/* Account Information Section */}
                    <div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Account Information</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Username */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Username *
                                </label>
                                <input
                                    type="text"
                                    name="username"
                                    value={formData.username}
                                    onChange={handleInputChange}
                                    disabled={isViewMode}
                                    className={inputClass('username')}
                                    aria-invalid={!!errors.username}
                                    aria-describedby={errors.username ? 'username-error' : undefined}
                                    placeholder="Enter username"
                                />
                                {fieldError('username')}
                            </div>

                            {/* Password */}
                            {mode === 'create' && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                        Password *
                                    </label>
                                    <div className="relative">
                                        <input
                                            type={showPassword ? 'text' : 'password'}
                                            name="password"
                                            value={formData.password}
                                            onChange={handleInputChange}
                                            disabled={isViewMode}
                                            className={`${inputClass('password')} pr-11`}
                                            aria-invalid={!!errors.password}
                                            aria-describedby={errors.password ? 'password-error' : undefined}
                                            placeholder="Enter password"
                                            autoComplete="new-password"
                                        />
                                        <PasswordToggleButton visible={showPassword} onToggle={() => setShowPassword((v) => !v)} disabled={isViewMode} />
                                    </div>
                                {fieldError('password')}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Personal Information Section */}
                    <div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Personal Information</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* First Name */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    First Name *
                                </label>
                                <input
                                    type="text"
                                    name="first_name"
                                    value={formData.first_name}
                                    onChange={handleInputChange}
                                    disabled={isViewMode}
                                    className={inputClass('first_name')}
                                    aria-invalid={!!errors.first_name}
                                    aria-describedby={errors.first_name ? 'first_name-error' : undefined}
                                    placeholder="Enter first name"
                                />
                                {fieldError('first_name')}
                            </div>

                            {/* Last Name */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Last Name *
                                </label>
                                <input
                                    type="text"
                                    name="last_name"
                                    value={formData.last_name}
                                    onChange={handleInputChange}
                                    disabled={isViewMode}
                                    className={inputClass('last_name')}
                                    aria-invalid={!!errors.last_name}
                                    aria-describedby={errors.last_name ? 'last_name-error' : undefined}
                                    placeholder="Enter last name"
                                />
                                {fieldError('last_name')}
                            </div>

                            {/* Email */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Email *
                                </label>
                                <input
                                    type="email"
                                    name="email"
                                    value={formData.email}
                                    onChange={handleInputChange}
                                    disabled={isViewMode}
                                    className={inputClass('email')}
                                    aria-invalid={!!errors.email}
                                    aria-describedby={errors.email ? 'email-error' : undefined}
                                    placeholder="Enter email"
                                />
                                {fieldError('email')}
                            </div>

                            {/* Phone */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Phone *
                                </label>
                                <input
                                    type="tel"
                                    name="phone"
                                    value={formData.phone}
                                    onChange={handleInputChange}
                                    disabled={isViewMode}
                                    className={inputClass('phone')}
                                    aria-invalid={!!errors.phone}
                                    aria-describedby={errors.phone ? 'phone-error' : undefined}
                                    placeholder="Enter phone number"
                                />
                                {fieldError('phone')}
                            </div>

                            {/* Gender */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Gender *
                                </label>
                                <select
                                    name="gender"
                                    value={formData.gender}
                                    onChange={handleInputChange}
                                    disabled={isViewMode}
                                    className={inputClass('gender')}
                                    aria-invalid={!!errors.gender}
                                    aria-describedby={errors.gender ? 'gender-error' : undefined}
                                >
                                    <option value="">Select Gender</option>
                                    <option value="Male">Male</option>
                                    <option value="Female">Female</option>
                                    <option value="Other">Other</option>
                                </select>
                                {fieldError('gender')}
                            </div>

                            {/* Date of Birth */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Date of Birth *
                                </label>
                                <input
                                    type="date"
                                    name="date_of_birth"
                                    value={formData.date_of_birth}
                                    onChange={handleInputChange}
                                    disabled={isViewMode}
                                    className={inputClass('date_of_birth')}
                                    aria-invalid={!!errors.date_of_birth}
                                    aria-describedby={errors.date_of_birth ? 'date_of_birth-error' : undefined}
                                />
                                {fieldError('date_of_birth')}
                            </div>
                        </div>

                        {/* Address */}
                        <div className="mt-6">
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Address *
                            </label>
                            <textarea
                                name="address"
                                value={formData.address}
                                onChange={handleInputChange}
                                disabled={isViewMode}
                                rows={2}
                                className={inputClass('address')}
                                    aria-invalid={!!errors.address}
                                    aria-describedby={errors.address ? 'address-error' : undefined}
                                placeholder="Enter address"
                            />
                                {fieldError('address')}
                        </div>
                    </div>

                    {/* Teacher Specific Information */}
                    <div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Teacher Information</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Employee ID */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Employee ID *
                                </label>
                                <input
                                    type="text"
                                    name="employee_id"
                                    value={formData.employee_id}
                                    onChange={handleInputChange}
                                    disabled={isViewMode}
                                    className={inputClass('employee_id')}
                                    aria-invalid={!!errors.employee_id}
                                    aria-describedby={errors.employee_id ? 'employee_id-error' : undefined}
                                    placeholder="Enter employee ID"
                                />
                                {fieldError('employee_id')}
                            </div>

                            {/* Designation */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Designation *
                                </label>
                                <input
                                    type="text"
                                    name="designation"
                                    value={formData.designation}
                                    onChange={handleInputChange}
                                    disabled={isViewMode}
                                    className={inputClass('designation')}
                                    aria-invalid={!!errors.designation}
                                    aria-describedby={errors.designation ? 'designation-error' : undefined}
                                    placeholder="Enter designation"
                                />
                                {fieldError('designation')}
                            </div>

                            {/* Date of Joining */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Date of Joining *
                                </label>
                                <input
                                    type="date"
                                    name="date_of_joining"
                                    value={formData.date_of_joining}
                                    onChange={handleInputChange}
                                    disabled={isViewMode}
                                    className={inputClass('date_of_joining')}
                                    aria-invalid={!!errors.date_of_joining}
                                    aria-describedby={errors.date_of_joining ? 'date_of_joining-error' : undefined}
                                />
                                {fieldError('date_of_joining')}
                            </div>

                            {/* Salary */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Salary *
                                </label>
                                <input
                                    type="number"
                                    name="salary"
                                    value={formData.salary}
                                    onChange={handleInputChange}
                                    disabled={isViewMode}
                                    className={inputClass('salary')}
                                    aria-invalid={!!errors.salary}
                                    aria-describedby={errors.salary ? 'salary-error' : undefined}
                                    placeholder="Enter salary"
                                />
                                {fieldError('salary')}
                            </div>
                        </div>

                        {/* Qualifications */}
                        <div className="mt-6">
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Qualifications *
                            </label>
                            <textarea
                                name="qualifications"
                                value={formData.qualifications}
                                onChange={handleInputChange}
                                disabled={isViewMode}
                                rows={4}
                                className={inputClass('qualifications')}
                                    aria-invalid={!!errors.qualifications}
                                    aria-describedby={errors.qualifications ? 'qualifications-error' : undefined}
                                placeholder="Enter qualifications"
                            />
                                {fieldError('qualifications')}
                        </div>
                    </div>

                    {/* Buttons */}
                    {!isViewMode && (
                        <div className="flex gap-4 justify-end">
                            <Button
                                variant="secondary"
                                onClick={() => navigate('/teachers')}
                                type="button"
                            >
                                Cancel
                            </Button>
                            <Button
                                variant="primary"
                                type="submit"
                                disabled={isSubmitting}
                            >
                                {isSubmitting ? 'Saving...' : mode === 'create' ? 'Create Teacher' : 'Update Teacher'}
                            </Button>
                        </div>
                    )}
                    {isViewMode && (
                        <div className="flex gap-4 justify-end">
                            <Button
                                variant="secondary"
                                onClick={() => navigate('/teachers')}
                            >
                                Back
                            </Button>
                        </div>
                    )}
                </form>
            </div>
        </div>
    );
};

export default TeacherForm;
