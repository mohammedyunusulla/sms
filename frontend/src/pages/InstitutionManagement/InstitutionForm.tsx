/**
 * Institution Form Page
 * Create and edit institutions with comprehensive form validation
 */

import { FC, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import toast from 'react-hot-toast';
import {
    PageHeader,
    Button,
    FormField,
    FormInput,
    LoadingSpinner,
} from '../../components';
import { institutionService } from '../../services/modules/institutionService';
import { IInstitution } from '../../types/index';

interface IFormData {
    name: string;
    code: string;
    email: string;
    phone: string;
    address: string;
    city: string;
    state: string;
    country: string;
    website: string;
}

interface IFormErrors {
    [key: string]: string;
}

const InstitutionForm: FC = () => {
    const navigate = useNavigate();
    const { id } = useParams();
    const isEditMode = Boolean(id);

    // State
    const [selectedInstitution, setSelectedInstitution] = useState<IInstitution | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Form state
    const [formData, setFormData] = useState<IFormData>({
        name: '',
        code: '',
        email: '',
        phone: '',
        address: '',
        city: '',
        state: '',
        country: '',
        website: '',
    });

    const [errors, setErrors] = useState<IFormErrors>({});
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Fetch institution data if editing
    useEffect(() => {
        if (isEditMode && id) {
            const fetchInstitution = async () => {
                setLoading(true);
                try {
                    const institution = await institutionService.getById(id);
                    setSelectedInstitution(institution);
                    setFormData({
                        name: institution.name,
                        code: institution.code,
                        email: institution.email,
                        phone: institution.phone,
                        address: institution.address,
                        city: institution.city || '',
                        state: institution.state || '',
                        country: institution.country || '',
                        website: institution.website || '',
                    });
                } catch (err: any) {
                    setError(err.message || 'Failed to load institution');
                } finally {
                    setLoading(false);
                }
            };
            fetchInstitution();
        }
    }, [id, isEditMode]);

    // Validate form
    const validateForm = (): boolean => {
        const newErrors: IFormErrors = {};

        // Name validation
        if (!formData.name.trim()) {
            newErrors.name = 'Institution name is required';
        } else if (formData.name.length < 3) {
            newErrors.name = 'Institution name must be at least 3 characters';
        }

        // Code validation
        if (!formData.code.trim()) {
            newErrors.code = 'Institution code is required';
        } else if (formData.code.length < 2) {
            newErrors.code = 'Institution code must be at least 2 characters';
        }

        // Email validation (optional)
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (formData.email.trim() && !emailRegex.test(formData.email)) {
            newErrors.email = 'Please enter a valid email address';
        }

        // Phone validation (optional)
        if (formData.phone.trim()) {
            const phoneRegex = /^[0-9]{10}$/;
            if (!phoneRegex.test(formData.phone.replace(/\D/g, ''))) {
                newErrors.phone = 'Please enter a valid 10-digit phone number';
            }
        }

        // Address validation
        if (!formData.address.trim()) {
            newErrors.address = 'Address is required';
        }

        // City validation
        if (!formData.city.trim()) {
            newErrors.city = 'City is required';
        }

        // State validation
        if (!formData.state.trim()) {
            newErrors.state = 'State is required';
        }

        // Country validation
        if (!formData.country.trim()) {
            newErrors.country = 'Country is required';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    // Handle input change
    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        setFormData((prev) => ({
            ...prev,
            [name]: value,
        }));

        // Clear error for this field
        if (errors[name]) {
            setErrors((prev) => ({
                ...prev,
                [name]: '',
            }));
        }
    };

    // Handle form submission
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!validateForm()) {
            toast.error('Please fix the errors in the form');
            return;
        }

        setIsSubmitting(true);

        try {
            if (isEditMode && id) {
                await institutionService.update(id, formData);
                toast.success('Institution updated successfully');
            } else {
                const created = await institutionService.create(formData as unknown as Omit<IInstitution, 'id' | 'created_at' | 'updated_at'>);
                toast.success('Institution created. Now switch on the features it needs.');
                // straight to its switches: a new institution starts with only the basics
                if (created?.id) {
                    setTimeout(() => navigate(`/institutions/${created.id}/features`), 800);
                    return;
                }
            }
            setTimeout(() => navigate('/institutions'), 1500);
        } catch (err: any) {
            toast.error(err.message || 'Failed to save institution');
        } finally {
            setIsSubmitting(false);
        }
    };

    // Show loading spinner while fetching data in edit mode
    if (isEditMode && loading && !selectedInstitution) {
        return <LoadingSpinner fullHeight message="Loading institution details..." />;
    }

    // Show error message
    if (error) {
        return (
            <div className="p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
                <Button variant="secondary" onClick={() => navigate('/institutions')}>
                    Back to Institutions
                </Button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Page Header */}
            <PageHeader
                title={isEditMode ? 'Edit Institution' : 'Add New Institution'}
                subtitle={
                    isEditMode
                        ? `Update details for ${selectedInstitution?.name}`
                        : 'Register a new institution in the system'
                }
                breadcrumbs={[
                    { label: 'Dashboard', href: '/dashboard' },
                    { label: 'Institutions', href: '/institutions' },
                    { label: isEditMode ? 'Edit' : 'New', href: '#' },
                ]}
            />

            {/* Form Card */}
            <div className="bg-white dark:bg-gray-800 p-8 rounded-lg border border-gray-200 dark:border-gray-700">
                <form onSubmit={handleSubmit} className="space-y-6">
                    {/* Basic Information Section */}
                    <div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                            Basic Information
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Institution Name */}
                            <FormField
                                label="Institution Name"
                                required
                                error={errors.name}
                            >
                                <FormInput
                                    name="name"
                                    type="text"
                                    value={formData.name}
                                    onChange={handleInputChange}
                                    placeholder="Enter institution name"
                                    error={Boolean(errors.name)}
                                    required
                                />
                            </FormField>

                            {/* Institution Code */}
                            <FormField
                                label="Institution Code"
                                required
                                error={errors.code}
                            >
                                <FormInput
                                    name="code"
                                    type="text"
                                    value={formData.code}
                                    onChange={handleInputChange}
                                    placeholder="Enter unique institution code"
                                    error={Boolean(errors.code)}
                                    required
                                    disabled={isEditMode}
                                />
                            </FormField>

                            {/* Phone */}
                            <FormField
                                label="Phone Number"
                                error={errors.phone}
                                help="10-digit phone number (optional)"
                            >
                                <FormInput
                                    name="phone"
                                    type="tel"
                                    value={formData.phone}
                                    onChange={handleInputChange}
                                    placeholder="Enter 10-digit phone number"
                                    error={Boolean(errors.phone)}
                                />
                            </FormField>

                            {/* Email */}
                            <FormField
                                label="Email Address"
                                error={errors.email}
                                help="Valid email address (optional)"
                            >
                                <FormInput
                                    name="email"
                                    type="email"
                                    value={formData.email}
                                    onChange={handleInputChange}
                                    placeholder="Enter email address"
                                    error={Boolean(errors.email)}
                                />
                            </FormField>

                            {/* Website */}
                            <FormField
                                label="Website"
                                error={errors.website}
                            >
                                <FormInput
                                    name="website"
                                    type="url"
                                    value={formData.website}
                                    onChange={handleInputChange}
                                    placeholder="https://www.institution.com"
                                    error={Boolean(errors.website)}
                                />
                            </FormField>

                        </div>
                    </div>

                    {/* Address Section */}
                    <div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                            Address Information
                        </h3>
                        <div className="space-y-4">
                            {/* Full Address */}
                            <FormField
                                label="Street Address"
                                required
                                error={errors.address}
                            >
                                <FormInput
                                    name="address"
                                    type="text"
                                    value={formData.address}
                                    onChange={handleInputChange}
                                    placeholder="Enter street address"
                                    error={Boolean(errors.address)}
                                    required
                                />
                            </FormField>

                            {/* City, State, Country Grid */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                {/* City */}
                                <FormField
                                    label="City"
                                    required
                                    error={errors.city}
                                >
                                    <FormInput
                                        name="city"
                                        type="text"
                                        value={formData.city}
                                        onChange={handleInputChange}
                                        placeholder="Enter city"
                                        error={Boolean(errors.city)}
                                        required
                                    />
                                </FormField>

                                {/* State */}
                                <FormField
                                    label="State/Province"
                                    required
                                    error={errors.state}
                                >
                                    <FormInput
                                        name="state"
                                        type="text"
                                        value={formData.state}
                                        onChange={handleInputChange}
                                        placeholder="Enter state"
                                        error={Boolean(errors.state)}
                                        required
                                    />
                                </FormField>

                                {/* Country */}
                                <FormField
                                    label="Country"
                                    required
                                    error={errors.country}
                                >
                                    <FormInput
                                        name="country"
                                        type="text"
                                        value={formData.country}
                                        onChange={handleInputChange}
                                        placeholder="Enter country"
                                        error={Boolean(errors.country)}
                                        required
                                    />
                                </FormField>
                            </div>
                        </div>
                    </div>

                    {/* Form Actions */}
                    <div className="flex items-center justify-between pt-6 border-t border-gray-200 dark:border-gray-700">
                        <Button
                            variant="secondary"
                            onClick={() => navigate('/institutions')}
                            disabled={isSubmitting}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="primary"
                            type="submit"
                            isLoading={isSubmitting}
                            loadingText={isEditMode ? 'Updating...' : 'Creating...'}
                        >
                            {isEditMode ? 'Update Institution' : 'Create Institution'}
                        </Button>
                    </div>
                </form>
            </div>

            {/* Info Box */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-4 rounded-lg">
                <p className="text-sm text-blue-700 dark:text-blue-300">
                    <strong>Note:</strong> All fields are required. Please ensure the information is accurate before submitting.
                    After creating an institution you choose which features and sign-ins it gets (Features & Logins).
                </p>
            </div>

        </div>
    );
};

export default InstitutionForm;
