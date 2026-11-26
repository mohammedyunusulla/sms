/**
 * Parent Form Component
 * Form for creating and editing parents with all fields
 */

import { useRoleGetsLogin } from '../../config/features';
import { FC, useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { useNavigate, useParams } from 'react-router';
import { PageHeader, Button, LoadingSpinner, PasswordToggleButton } from '../../components';
import { parentService } from '../../services/modules/parentService';
import { fieldInputClass, isValidEmail, passwordProblem } from '../../utils/formValidation';

interface IParentFormProps {
    initialData?: any;
    mode?: 'create' | 'update' | 'view';
    isModal?: boolean;
    onSubmitSuccess?: (parentData: any) => void;
}

const ParentForm: FC<IParentFormProps> = ({ initialData, mode: propMode = 'create', isModal = false, onSubmitSuccess }) => {
    const navigate = useNavigate();
    const { id } = useParams();
    const [loading, setLoading] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errors, setErrors] = useState<Record<string, string>>({});
    const [showPassword, setShowPassword] = useState(false);
    const createsLogin = useRoleGetsLogin('PARENT'); // is parent sign-in switched on for the institution?
    // Auto-detect mode based on URL - if id exists and not in modal, it's update mode
    const mode = !isModal && id ? 'update' : propMode;
    const [formData, setFormData] = useState({
        // Base user fields
        username: null,
        password: null,
        first_name: null,
        last_name: null,
        email: null,
        phone: null,
        gender: null,
        date_of_birth: null,
        address: null,
        has_login: false,
        is_active: true,
        // Parent specific fields
        relation_type: null,
        father_full_name: null,
        father_phone: null,
        father_occupation: null,
        father_qualification: null,
        mother_full_name: null,
        mother_phone: null,
        mother_occupation: null,
        mother_qualification: null,
        city: null,
        state: null,
        postal_code: null,
        ...initialData,
    });

    useEffect(() => {
        if (mode === 'update' && id) {
            fetchParent();
        }
    }, [id, mode]);

    const fetchParent = async () => {
        try {
            setLoading(true);
            const response = await parentService.getById(id!);
            setFormData(response.data);
        } catch (error) {
            console.error('Error fetching parent:', error);
            toast.error('Failed to fetch parent');
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
        if (errors[name]) {
            setErrors((prev) => {
                const next = { ...prev };
                delete next[name];
                return next;
            });
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // Mandatory: username (used as the login email) + password when creating; father's name
        // (it becomes the account's first name, which the database requires)
        const v = (key: string) => String((formData as Record<string, unknown>)[key] ?? '').trim();
        const found: Record<string, string> = {};
        if (mode === 'create') {
            if (!v('username')) found.username = 'Username is required';
            else if (!isValidEmail(v('username'))) found.username = 'Username must be a valid email address';
            if (createsLogin) {
                const problem = passwordProblem(String(formData.password ?? ''));
                if (problem) found.password = problem;
            }
        }
        if (!v('father_full_name')) found.father_full_name = "Father's name is required";
        setErrors(found);
        if (Object.keys(found).length > 0) {
            const count = Object.keys(found).length;
            toast.error(`Please fix ${count} highlighted field${count > 1 ? 's' : ''}`);
            document.querySelector<HTMLElement>(`#parent-form [name="${Object.keys(found)[0]}"]`)?.focus();
            return;
        }

        try {
            setIsSubmitting(true);
            // The account's first/last name come from the father's/mother's names. Username and email
            // are only sent when creating: the edit page doesn't load them, and sending null used to
            // overwrite required columns (every parent edit failed with a 500).
            const { username, email, password, ...rest } = formData as Record<string, unknown>;
            const names = {
                first_name: String(formData.father_full_name ?? '').trim(),
                last_name: String(formData.mother_full_name ?? '').trim(),
            };
            let result: any;
            if (mode === 'update' && id) {
                const payload: Record<string, unknown> = { ...rest, ...names };
                if (username) payload.username = username;
                if (email) payload.email = email;
                await parentService.update(id, payload);
                toast.success('Parent updated successfully');
                result = payload;
            } else {
                result = await parentService.create({ ...rest, ...names, username, password, email: email || username });
                toast.success('Parent created successfully');
            }

            if (isModal && onSubmitSuccess) {
                onSubmitSuccess(result);
            } else {
                navigate('/parents');
            }
        } catch (error: any) {
            toast.error(error.message || 'Failed to save parent');
        } finally {
            setIsSubmitting(false);
        }
    };

    if (loading) {
        return <LoadingSpinner fullHeight message="Loading parent..." />;
    }

    const isViewMode = mode === 'view';

    const formContent = (
        <form id="parent-form" onSubmit={handleSubmit} noValidate className="space-y-8">
            {/* Account Information Section */}
            <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Account Information</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Username */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Username (email) *
                        </label>
                        <input
                            type="text"
                            name="username"
                            value={formData.username}
                            onChange={handleInputChange}
                            disabled={isViewMode}
                            className={fieldInputClass(!!errors.username)}
                            aria-invalid={!!errors.username}
                            aria-describedby={errors.username ? 'parent-username-error' : undefined}
                            placeholder="e.g. parent@example.com"
                        />
                        {errors.username && <p id="parent-username-error" role="alert" className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.username}</p>}
                    </div>

                    {/* Password (only where parent sign-in is switched on) */}
                    {mode === 'create' && !createsLogin && (
                        <div className="rounded-lg bg-gray-50 p-3 text-sm text-gray-600 dark:bg-gray-800 dark:text-gray-300" data-testid="no-login-note">
                            Sign-in isn't switched on for parents at your institution, so no password is needed.
                        </div>
                    )}
                    {mode === 'create' && createsLogin && (
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
                                    className={`${fieldInputClass(!!errors.password)} pr-11`}
                                    aria-invalid={!!errors.password}
                                    aria-describedby={errors.password ? 'parent-password-error' : undefined}
                                    placeholder="Enter password"
                                    autoComplete="new-password"
                                />
                                <PasswordToggleButton visible={showPassword} onToggle={() => setShowPassword((v) => !v)} disabled={isViewMode} />
                            </div>
                            {errors.password && <p id="parent-password-error" role="alert" className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.password}</p>}
                        </div>
                    )}
                </div>
            </div>

            {/* Parent Relationship Information */}
            <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Parent Relationship Information</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Relation Type */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Relation Type
                        </label>
                        <select
                            name="relation_type"
                            value={formData.relation_type}
                            onChange={handleInputChange}
                            disabled={isViewMode}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50"
                        >
                            <option value="">Select Relation Type</option>
                            <option value="Father">Father</option>
                            <option value="Mother">Mother</option>
                            <option value="Guardian">Guardian</option>
                            <option value="Other">Other</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* Father Information */}
            <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Father Information</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Father Full Name */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Full Name *
                        </label>
                        <input
                            type="text"
                            name="father_full_name"
                            value={formData.father_full_name}
                            onChange={handleInputChange}
                            disabled={isViewMode}
                            className={fieldInputClass(!!errors.father_full_name)}
                            aria-invalid={!!errors.father_full_name}
                            aria-describedby={errors.father_full_name ? 'parent-father_full_name-error' : undefined}
                            placeholder="Enter father's full name"
                        />
                        {errors.father_full_name && <p id="parent-father_full_name-error" role="alert" className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.father_full_name}</p>}
                    </div>

                    {/* Father Phone */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Phone Number
                        </label>
                        <input
                            type="tel"
                            name="father_phone"
                            value={formData.father_phone}
                            onChange={handleInputChange}
                            disabled={isViewMode}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50"
                            placeholder="Enter father's phone number"
                        />
                    </div>

                    {/* Father Occupation */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Occupation
                        </label>
                        <input
                            type="text"
                            name="father_occupation"
                            value={formData.father_occupation}
                            onChange={handleInputChange}
                            disabled={isViewMode}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50"
                            placeholder="Enter father's occupation"
                        />
                    </div>

                    {/* Father Qualification */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Qualification
                        </label>
                        <input
                            type="text"
                            name="father_qualification"
                            value={formData.father_qualification}
                            onChange={handleInputChange}
                            disabled={isViewMode}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50"
                            placeholder="Enter father's qualification"
                        />
                    </div>
                </div>
            </div>

            {/* Mother Information */}
            <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Mother Information</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Mother Full Name */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Full Name
                        </label>
                        <input
                            type="text"
                            name="mother_full_name"
                            value={formData.mother_full_name}
                            onChange={handleInputChange}
                            disabled={isViewMode}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50"
                            placeholder="Enter mother's full name"
                        />
                    </div>

                    {/* Mother Phone */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Phone Number
                        </label>
                        <input
                            type="tel"
                            name="mother_phone"
                            value={formData.mother_phone}
                            onChange={handleInputChange}
                            disabled={isViewMode}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50"
                            placeholder="Enter mother's phone number"
                        />
                    </div>

                    {/* Mother Occupation */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Occupation
                        </label>
                        <input
                            type="text"
                            name="mother_occupation"
                            value={formData.mother_occupation}
                            onChange={handleInputChange}
                            disabled={isViewMode}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50"
                            placeholder="Enter mother's occupation"
                        />
                    </div>

                    {/* Mother Qualification */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Qualification
                        </label>
                        <input
                            type="text"
                            name="mother_qualification"
                            value={formData.mother_qualification}
                            onChange={handleInputChange}
                            disabled={isViewMode}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50"
                            placeholder="Enter mother's qualification"
                        />
                    </div>
                </div>
            </div>

            {/* Address Details */}
            <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Address Details</h3>
                {/* Personal Address */}
                <div >
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Address
                    </label>
                    <textarea
                        name="address"
                        value={formData.address}
                        onChange={handleInputChange}
                        disabled={isViewMode}
                        rows={2}
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50"
                        placeholder="Enter address"
                    />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* City */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            City
                        </label>
                        <input
                            type="text"
                            name="city"
                            value={formData.city}
                            onChange={handleInputChange}
                            disabled={isViewMode}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50"
                            placeholder="Enter city"
                        />
                    </div>

                    {/* State */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            State
                        </label>
                        <input
                            type="text"
                            name="state"
                            value={formData.state}
                            onChange={handleInputChange}
                            disabled={isViewMode}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50"
                            placeholder="Enter state"
                        />
                    </div>

                    {/* Postal Code */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Postal Code
                        </label>
                        <input
                            type="text"
                            name="postal_code"
                            value={formData.postal_code}
                            onChange={handleInputChange}
                            disabled={isViewMode}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50"
                            placeholder="Enter postal code"
                        />
                    </div>
                </div>
            </div>

        </form>
    );

    // If modal mode, return just the form
    if (isModal) {
        return formContent;
    }

    // Otherwise return full page layout
    return (
        <div className="space-y-6">
            <PageHeader
                title={mode === 'create' ? 'Create Parent' : mode === 'update' ? 'Edit Parent' : 'View Parent'}
                subtitle="Manage parent information"
                breadcrumbs={[
                    { label: 'Dashboard', href: '/dashboard' },
                    { label: 'Parents', href: '/parents' },
                    { label: mode === 'create' ? 'Create' : 'Edit', href: '#' },
                ]}
            />

            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
                {formContent}

                {/* Buttons */}
                {!isViewMode && (
                    <div className="flex gap-4 justify-end mt-8">
                        <Button
                            variant="secondary"
                            onClick={() => navigate('/parents')}
                            type="button"
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="primary"
                            type="submit"
                            form="parent-form"
                            disabled={isSubmitting}
                        >
                            {isSubmitting ? 'Saving...' : mode === 'create' ? 'Create Parent' : 'Update Parent'}
                        </Button>
                    </div>
                )}
                {isViewMode && (
                    <div className="flex gap-4 justify-end mt-8">
                        <Button
                            variant="secondary"
                            onClick={() => navigate('/parents')}
                        >
                            Back
                        </Button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ParentForm;
