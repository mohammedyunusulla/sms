/**
 * Add an existing student to a section (QA A30: a section could only create NEW students).
 * Searches all students; ones already in another section are moved, which the list says before adding.
 */
import { FC, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import Modal from '../../components/modals/Modal';
import Button from '../../components/ui/button/Button';
import { studentService } from '@/services/modules/studentService';
import { classService } from '@/services/modules/classService';
import { useDebounce } from '../../hooks/useDebounce';

interface FoundStudent {
    id: number;
    full_name: string;
    profile?: { admission_number?: string | null; roll_no?: string | null } | null;
    class?: { class_name?: string } | null;
    section?: { id?: number; section_name?: string } | null;
}

interface Props {
    isOpen: boolean;
    sectionId: number;
    sectionLabel: string;
    onClose: () => void;
    onAdded: () => void;
}

const AddExistingStudentModal: FC<Props> = ({ isOpen, sectionId, sectionLabel, onClose, onAdded }) => {
    const [term, setTerm] = useState('');
    const debounced = useDebounce(term, 400);
    const [results, setResults] = useState<FoundStudent[]>([]);
    const [loading, setLoading] = useState(false);
    const [adding, setAdding] = useState<number | null>(null);

    useEffect(() => {
        if (!isOpen) { setTerm(''); setResults([]); return; }
        if (debounced.trim().length < 2) { setResults([]); return; }
        let cancelled = false;
        setLoading(true);
        studentService.list({ search: debounced.trim(), limit: 20, status: 'active' })
            .then((res) => !cancelled && setResults(((res.data || []) as FoundStudent[]).filter((s) => s.section?.id !== sectionId)))
            .catch(() => !cancelled && setResults([]))
            .finally(() => !cancelled && setLoading(false));
        return () => { cancelled = true; };
    }, [debounced, isOpen, sectionId]);

    const add = async (student: FoundStudent) => {
        try {
            setAdding(student.id);
            await classService.addStudentsToSection(sectionId, [student.id]);
            toast.success(`${student.full_name} added to ${sectionLabel}`);
            setResults((prev) => prev.filter((s) => s.id !== student.id));
            onAdded();
        } catch (err) {
            toast.error((err as Error).message || 'Failed to add the student');
        } finally {
            setAdding(null);
        }
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title={`Add an existing student to ${sectionLabel}`} size="md">
            <div className="space-y-3" data-testid="add-existing-student">
                <input
                    type="search"
                    autoFocus
                    value={term}
                    onChange={(e) => setTerm(e.target.value)}
                    placeholder="Search by name, email or admission number"
                    aria-label="Search students"
                    className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                />
                {loading && <p className="text-sm text-gray-500">Searching…</p>}
                {!loading && debounced.trim().length >= 2 && results.length === 0 && (
                    <p className="text-sm text-gray-500">No students found outside this section.</p>
                )}
                <ul className="divide-y divide-gray-100 dark:divide-gray-700">
                    {results.map((s) => {
                        const where = s.class?.class_name
                            ? `${s.class.class_name}${s.section?.section_name ? ` – ${s.section.section_name}` : ' – no section'}`
                            : 'No class yet';
                        const moves = !!s.section?.id;
                        return (
                            <li key={s.id} className="flex items-center justify-between gap-3 py-2">
                                <div>
                                    <p className="font-medium text-gray-900 dark:text-white">{s.full_name}</p>
                                    <p className="text-xs text-gray-500 dark:text-gray-400">
                                        {[s.profile?.admission_number, where].filter(Boolean).join(' · ')}
                                        {moves && <span className="ml-1 text-amber-600">(will move here)</span>}
                                    </p>
                                </div>
                                <Button size="sm" variant="primary" onClick={() => add(s)} disabled={adding !== null}>
                                    {adding === s.id ? 'Adding…' : 'Add'}
                                </Button>
                            </li>
                        );
                    })}
                </ul>
            </div>
        </Modal>
    );
};

export default AddExistingStudentModal;
