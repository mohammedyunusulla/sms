/**
 * Create logins for people who were added while sign-in was switched off for their role
 * (Super Admin > Features & Logins). One starting password for all; a report can be exported afterwards.
 */
import { FC, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { Button, Modal } from '../../components';
import { userService } from '../../services/modules/userService';
import { passwordProblem } from '../../utils/formValidation';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    skid: string;
    institutionId: number;
    /** roles whose sign-in is switched on */
    roles: Array<{ code: string; label: string }>;
}

const ProvisionLoginsModal: FC<Props> = ({ isOpen, onClose, skid, institutionId, roles }) => {
    const [provisionPassword, setProvisionPassword] = useState('');
    const [provisionShowPassword, setProvisionShowPassword] = useState(false);
    const [provisionRoleFilter, setProvisionRoleFilter] = useState('');
    const [provisionLoading, setProvisionLoading] = useState(false);
    const [provisionResult, setProvisionResult] = useState<any>(null);

    useEffect(() => {
        if (isOpen) {
            setProvisionPassword('');
            setProvisionRoleFilter('');
            setProvisionResult(null);
        }
    }, [isOpen]);

    // Handle bulk provisioning
    const handleBulkProvision = async () => {
        const problem = passwordProblem(provisionPassword);
        if (problem) {
            toast.error(problem);
            return;
        }
        

        try {
            setProvisionLoading(true);
            const result = await userService.provisionBulkLogins({
                skid: skid,
                institution_id: institutionId,
                default_password: provisionPassword,
                role_filter: provisionRoleFilter || undefined,
            });
            setProvisionResult(result);
            if (result.success_count > 0) {
                toast.success(`${result.success_count} login(s) created successfully`);
            }
            if (result.failed_count > 0) {
                toast.error(`${result.failed_count} login(s) failed`);
            }
        } catch (err: any) {
            toast.error(err.message || 'Failed to provision logins');
        } finally {
            setProvisionLoading(false);
        }
    };

    // Export provisioning report
    const handleExportReport = async () => {
        
        try {
            const report = await userService.getProvisioningReport(skid, institutionId);

            // Build a map of failure reasons from provisioning result (institution_user_id -> reason)
            const failureReasons: Record<number, string> = {};
            if (provisionResult?.failures) {
                for (const f of provisionResult.failures) {
                    failureReasons[f.institution_user_id] = f.reason;
                }
            }

            // Build a set of successfully provisioned user IDs
            const provisionedIds = new Set<number>();
            if (provisionResult?.successes) {
                for (const s of provisionResult.successes) {
                    provisionedIds.add(s.institution_user_id);
                }
            }

            // Generate CSV
            const headers = ['Name', 'Email', 'Username', 'Role', 'Phone', 'Gender', 'Login Status', 'Login Active', 'Login Username', 'Remarks'];
            const csvRows = [headers.join(',')];
            for (const u of report.users) {
                // Determine login status and reason
                let loginStatus = '';
                let remarks = '';
                if (u.has_login) {
                    if (provisionedIds.has(u.institution_user_id)) {
                        loginStatus = 'Login Created';
                    } else {
                        loginStatus = 'Has Login';
                    }
                } else if (failureReasons[u.institution_user_id]) {
                    loginStatus = 'Failed';
                    remarks = failureReasons[u.institution_user_id];
                } else {
                    loginStatus = 'No Login';
                }

                csvRows.push([
                    `"${u.full_name}"`,
                    `"${u.email}"`,
                    `"${u.username}"`,
                    `"${u.role}"`,
                    `"${u.phone || ''}"`,
                    `"${u.gender || ''}"`,
                    `"${loginStatus}"`,
                    u.login_active ? 'Yes' : 'No',
                    `"${u.login_username || ''}"`,
                    `"${remarks}"`,
                ].join(','));
            }
            const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${report.institution_name}_users_login_report.csv`;
            a.click();
            URL.revokeObjectURL(url);
            toast.success('Report exported successfully');
        } catch (err: any) {
            toast.error(err.message || 'Failed to export report');
        }
    };

    return (
        <>
            {/* Bulk Provisioning Modal */}
            <Modal
                isOpen={isOpen}
                onClose={onClose}
                title="Create logins for existing people"
                size="lg"
                closeButton={!!provisionResult}
                footer={
                    !provisionResult ? (
                        <div className="flex justify-between">
                            <Button
                                variant="secondary"
                                onClick={() => onClose()}
                            >
                                Skip
                            </Button>
                            <Button
                                variant="primary"
                                onClick={handleBulkProvision}
                                disabled={provisionLoading || !!passwordProblem(provisionPassword)}
                                isLoading={provisionLoading}
                                loadingText="Provisioning..."
                            >
                                Provision Logins
                            </Button>
                        </div>
                    ) : (
                        <div className="flex justify-between">
                            <Button
                                variant="secondary"
                                onClick={handleExportReport}
                            >
                                Export Report
                            </Button>
                            <Button
                                variant="primary"
                                onClick={() => onClose()}
                            >
                                Done
                            </Button>
                        </div>
                    )
                }
            >
                {!provisionResult ? (
                    <>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                            People added while sign-in was off have no login. Create logins now for everyone whose role has sign-in switched on, with one starting password they can change later.
                        </p>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Default Password *
                                </label>
                                <div className="relative">
                                    <input
                                        type={provisionShowPassword ? 'text' : 'password'}
                                        value={provisionPassword}
                                        onChange={(e) => setProvisionPassword(e.target.value)}
                                        placeholder="8+ characters, with upper and lower case letters and a digit"
                                        className="w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setProvisionShowPassword(!provisionShowPassword)}
                                        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                                    >
                                        {provisionShowPassword ? (
                                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                                            </svg>
                                        ) : (
                                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                            </svg>
                                        )}
                                    </button>
                                </div>
                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                    This password will be set for all newly provisioned users
                                </p>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Role Filter
                                </label>
                                <select
                                    value={provisionRoleFilter}
                                    onChange={(e) => setProvisionRoleFilter(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="">Everyone whose sign-in is on</option>
                                    {roles.map((r) => <option key={r.code} value={r.code}>{r.label}s only</option>)}
                                </select>
                            </div>
                        </div>
                    </>
                ) : (
                    <div className="space-y-4">
                        {/* Results Summary */}
                        <div className="grid grid-cols-2 gap-3">
                            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 text-center">
                                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{provisionResult.total_eligible}</p>
                                <p className="text-xs text-blue-600 dark:text-blue-400">Total Eligible</p>
                            </div>
                            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 text-center">
                                <p className="text-2xl font-bold text-gray-600 dark:text-gray-400">{provisionResult.already_provisioned}</p>
                                <p className="text-xs text-gray-600 dark:text-gray-400">Already Had Login</p>
                            </div>
                            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 text-center">
                                <p className="text-2xl font-bold text-green-600 dark:text-green-400">{provisionResult.success_count}</p>
                                <p className="text-xs text-green-600 dark:text-green-400">Logins Created</p>
                            </div>
                            <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3 text-center">
                                <p className="text-2xl font-bold text-red-600 dark:text-red-400">{provisionResult.failed_count}</p>
                                <p className="text-xs text-red-600 dark:text-red-400">Failed</p>
                            </div>
                        </div>

                        {/* Failures List */}
                        {provisionResult.failures && provisionResult.failures.length > 0 && (
                            <div>
                                <h4 className="text-sm font-semibold text-red-600 dark:text-red-400 mb-2">Failed Users:</h4>
                                <div className="max-h-40 overflow-y-auto space-y-2">
                                    {provisionResult.failures.map((f: any, i: number) => (
                                        <div key={i} className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-lg p-2">
                                            <p className="text-sm font-medium text-red-700 dark:text-red-300">{f.name} ({f.role})</p>
                                            <p className="text-xs text-red-600 dark:text-red-400">{f.reason}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </Modal>
        </>
    );
};

export default ProvisionLoginsModal;
