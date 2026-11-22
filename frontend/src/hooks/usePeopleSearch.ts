/**
 * Students / teachers for the header search (QA A31: it only found page names).
 * Uses the normal list endpoints, so the server's rules apply: a teacher only finds students in their
 * own sections, and nobody without the Students / Teachers tick gets those lists.
 */
import { useEffect, useState } from 'react';
import { studentService } from '../services/modules/studentService';
import { teacherService } from '../services/modules/teacherService';
import type { SearchablePage } from '../data/searchablePages';

interface Options {
    query: string;
    canOpen: (path: string) => boolean;
}

interface PersonRow {
    id: number | string;
    full_name?: string;
    first_name?: string;
    last_name?: string;
    email?: string;
    profile?: { admission_number?: string | null } | null;
    class?: { class_name?: string } | null;
    section?: { section_name?: string } | null;
}

const nameOf = (p: PersonRow) => p.full_name || [p.first_name, p.last_name].filter(Boolean).join(' ') || p.email || 'Unnamed';

export const usePeopleSearch = ({ query, canOpen }: Options) => {
    const [people, setPeople] = useState<{ category: string; pages: SearchablePage[] }[]>([]);
    const [loading, setLoading] = useState(false);
    const canStudents = canOpen('/students');
    const canTeachers = canOpen('/teachers');

    useEffect(() => {
        const term = query.trim();
        if (term.length < 2 || (!canStudents && !canTeachers)) { setPeople([]); setLoading(false); return; }
        let cancelled = false;
        setLoading(true);
        const timer = setTimeout(async () => {
            const [students, teachers] = await Promise.all([
                canStudents ? studentService.list({ search: term, limit: 5 }).then((r) => (r.data || []) as PersonRow[]).catch(() => []) : Promise.resolve([] as PersonRow[]),
                canTeachers ? teacherService.list({ search: term, limit: 5 }).then((r) => (r.data || []) as unknown as PersonRow[]).catch(() => []) : Promise.resolve([] as PersonRow[]),
            ]);
            if (cancelled) return;
            const groups: { category: string; pages: SearchablePage[] }[] = [];
            if (students.length) groups.push({
                category: 'Students',
                pages: students.map((s) => ({
                    id: `student-${s.id}`,
                    name: nameOf(s),
                    description: [
                        s.profile?.admission_number,
                        s.class?.class_name ? `${s.class.class_name}${s.section?.section_name ? ` – ${s.section.section_name}` : ''}` : 'No class',
                    ].filter(Boolean).join(' · '),
                    route: `/students?search=${encodeURIComponent(nameOf(s))}`,
                    keywords: [], category: 'Students', icon: '🎓', roles: [],
                })),
            });
            if (teachers.length) groups.push({
                category: 'Teachers',
                pages: teachers.map((t) => ({
                    id: `teacher-${t.id}`,
                    name: nameOf(t),
                    description: t.email || 'Teacher',
                    route: `/teachers?search=${encodeURIComponent(nameOf(t))}`,
                    keywords: [], category: 'Teachers', icon: '👩‍🏫', roles: [],
                })),
            });
            setPeople(groups);
            setLoading(false);
        }, 300);
        return () => { cancelled = true; clearTimeout(timer); };
    }, [query, canStudents, canTeachers]);

    return { people, loading };
};
