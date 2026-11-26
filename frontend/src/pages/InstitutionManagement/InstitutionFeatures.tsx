/**
 * Features & Logins (Super Admin): what one institution has switched on.
 *   Features - each optional feature; switching one on brings what it needs (Timetable needs Subjects),
 *              switching one off asks about the features that need it.
 *   Sign-in  - which roles can sign in (and get a login when they are created).
 * Nothing is saved until Save.
 */
import { FC, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import toast from 'react-hot-toast';
import { Badge, Button, ConfirmDialog, LoadingSpinner, PageHeader } from '../../components';
import Switch from '../../components/form/switch/Switch';
import { institutionService } from '../../services/modules/institutionService';
import type { FeatureCatalogue, InstitutionFeatureSettings } from '../../services/modules/institutionService';
import ProvisionLoginsModal from './ProvisionLoginsModal';

const sameSet = (a: string[], b: string[]) => a.length === b.length && a.every((x) => b.includes(x));

const InstitutionFeatures: FC = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const [settings, setSettings] = useState<InstitutionFeatureSettings | null>(null);
    const [features, setFeatures] = useState<string[]>([]);
    const [loginRoles, setLoginRoles] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    // switching off a feature other features need: ask first
    const [turnOff, setTurnOff] = useState<{ key: string; also: string[] } | null>(null);
    const [provisionOpen, setProvisionOpen] = useState(false);
    // the shared Switch keeps its own on/off: a new number redraws every switch from our state
    const [drawn, setDrawn] = useState(0);

    useEffect(() => {
        if (!id) return;
        let cancelled = false;
        setLoading(true);
        institutionService.getFeatureSettings(id)
            .then((data) => {
                if (cancelled) return;
                setSettings(data);
                setFeatures(data.features);
                setLoginRoles(data.login_roles);
            })
            .catch((err: unknown) => !cancelled && toast.error((err as { message?: string })?.message || 'Failed to load'))
            .finally(() => !cancelled && setLoading(false));
        return () => {
            cancelled = true;
        };
    }, [id]);

    const catalogue: FeatureCatalogue | undefined = settings?.catalogue;
    const byKey = useMemo(() => new Map((catalogue?.features || []).map((f) => [f.key, f])), [catalogue]);
    const label = (key: string) => byKey.get(key)?.label || key;
    const names = (keys: string[]) => keys.map(label).join(', ');

    // everything a feature needs, directly or through another feature
    const needsOf = (key: string, found: string[] = []): string[] => {
        (byKey.get(key)?.requires || []).forEach((needed) => {
            if (!found.includes(needed)) {
                found.push(needed);
                needsOf(needed, found);
            }
        });
        return found;
    };

    const toggleFeature = (key: string, on: boolean) => {
        if (on) {
            const added = needsOf(key).filter((k) => !features.includes(k));
            setFeatures((prev) => [...new Set([...prev, key, ...added])]);
            if (added.length) toast(`Also switched on: ${names(added)} (${label(key)} needs ${added.length === 1 ? 'it' : 'them'})`);
            return;
        }
        const also = (byKey.get(key)?.needed_by || []).filter((k) => features.includes(k));
        if (also.length) setTurnOff({ key, also });
        else setFeatures((prev) => prev.filter((k) => k !== key));
    };

    const confirmTurnOff = () => {
        if (!turnOff) return;
        const gone = [turnOff.key, ...turnOff.also];
        setFeatures((prev) => prev.filter((k) => !gone.includes(k)));
        setTurnOff(null);
    };

    const toggleRole = (code: string, on: boolean) =>
        setLoginRoles((prev) => (on ? [...new Set([...prev, code])] : prev.filter((r) => r !== code)));

    const changed = !!settings && (!sameSet(features, settings.features) || !sameSet(loginRoles, settings.login_roles));
    const newlyOnRoles = settings ? loginRoles.filter((r) => !settings.login_roles.includes(r)) : [];

    const save = async () => {
        if (!id || !settings) return;
        try {
            setSaving(true);
            const offerLogins = newlyOnRoles.length > 0;
            const saved = await institutionService.updateFeatureSettings(id, { features, login_roles: loginRoles });
            setSettings({ ...settings, ...saved });
            setFeatures(saved.features);
            setLoginRoles(saved.login_roles);
            toast.success('Saved. People already signed in see the change within a minute.');
            if (offerLogins) setProvisionOpen(true); // people added while sign-in was off have no login yet
        } catch (err: unknown) {
            toast.error((err as { message?: string })?.message || 'Failed to save');
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <LoadingSpinner fullHeight message="Loading..." />;
    if (!settings || !catalogue) {
        return <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">Institution not found.</div>;
    }

    const card = 'rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800';
    const row = 'flex items-start justify-between gap-4 rounded-lg border border-gray-200 p-4 dark:border-gray-700';

    return (
        <div className="space-y-6">
            <PageHeader
                title="Features & Logins"
                subtitle={`${settings.institution.name} (${settings.institution.code})`}
                breadcrumbs={[
                    { label: 'Dashboard', href: '/dashboard' },
                    { label: 'Institutions', href: '/institutions' },
                    { label: 'Features & Logins', href: '#' },
                ]}
            />

            <div className={card}>
                <h3 className="text-base font-semibold text-gray-900 dark:text-white">Always on</h3>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Every institution has these.</p>
                <div className="mt-3 flex flex-wrap gap-2">
                    {catalogue.always_on.map((name) => <Badge key={name} variant="secondary">{name}</Badge>)}
                </div>
            </div>

            <div className={card}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                            Features <span className="font-normal text-gray-500">({features.length} of {catalogue.features.length} on)</span>
                        </h3>
                        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                            A feature that is off is hidden for everyone at this institution. Its data is kept.
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={() => setFeatures(catalogue.features.map((f) => f.key))}>All on</Button>
                        <Button size="sm" variant="outline" onClick={() => setFeatures([])}>All off</Button>
                    </div>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2" data-testid="feature-list">
                    {catalogue.features.map((f) => {
                        const on = features.includes(f.key);
                        return (
                            <div key={f.key} className={row} data-testid={`feature-${f.key}`}>
                                <div className="min-w-0">
                                    <p className="font-medium text-gray-900 dark:text-white">{f.label}</p>
                                    <p className="text-sm text-gray-500 dark:text-gray-400">{f.about}</p>
                                    {f.requires.length > 0 && (
                                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Needs: {names(f.requires)}</p>
                                    )}
                                </div>
                                <Switch key={`${f.key}-${on}-${drawn}`} label="" defaultChecked={on} onChange={(v) => toggleFeature(f.key, v)} />
                            </div>
                        );
                    })}
                </div>
            </div>

            <div className={card}>
                <h3 className="text-base font-semibold text-gray-900 dark:text-white">Who can sign in</h3>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    People of a role that is off are added without a login and can't sign in. The Institution Admin can always sign in.
                </p>
                <div className="mt-4 grid gap-3 md:grid-cols-3" data-testid="login-role-list">
                    {catalogue.login_roles.map((r) => {
                        const on = loginRoles.includes(r.code);
                        return (
                            <div key={r.code} className={row} data-testid={`login-${r.code}`}>
                                <p className="font-medium text-gray-900 dark:text-white">{r.label}</p>
                                <Switch key={`${r.code}-${on}-${drawn}`} label="" defaultChecked={on} onChange={(v) => toggleRole(r.code, v)} />
                            </div>
                        );
                    })}
                </div>
                {settings.login_roles.length > 0 && (
                    <div className="mt-4">
                        <Button size="sm" variant="outline" onClick={() => setProvisionOpen(true)} disabled={changed}>
                            Create logins for existing people
                        </Button>
                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                            For people who were added while sign-in was off for their role.{changed ? ' Save your changes first.' : ''}
                        </p>
                    </div>
                )}
            </div>

            <div className="flex justify-end gap-3">
                <Button variant="outline" onClick={() => navigate('/institutions')}>Back to Institutions</Button>
                <Button onClick={save} isLoading={saving} loadingText="Saving..." disabled={!changed}>Save</Button>
            </div>

            <ConfirmDialog
                isOpen={!!turnOff}
                title={turnOff ? `Switch off ${label(turnOff.key)}?` : ''}
                message={turnOff ? `${names(turnOff.also)} ${turnOff.also.length === 1 ? 'needs' : 'need'} ${label(turnOff.key)}, so ${turnOff.also.length === 1 ? 'it' : 'they'} will be switched off too.` : ''}
                confirmText="Switch off"
                type="warning"
                onConfirm={confirmTurnOff}
                onCancel={() => { setTurnOff(null); setDrawn((n) => n + 1); }}
            />

            <ProvisionLoginsModal
                isOpen={provisionOpen}
                onClose={() => setProvisionOpen(false)}
                skid={settings.institution.skid}
                institutionId={settings.institution.id}
                roles={catalogue.login_roles.filter((r) => settings.login_roles.includes(r.code))}
            />
        </div>
    );
};

export default InstitutionFeatures;
