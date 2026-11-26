/**
 * Homework AI - teacher. Two tabs, both by date:
 *   Create Homework: the form (date = today by default) and the homework set for that date.
 *   Analytics: pick a date, then one of that day's homework, to see the class's results and flags.
 * (Homework AI is its own module; it is not the Homeworks feature.)
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { Button, ConfirmDialog, DataTable, FormField, FormInput, FormSelect, FormTextarea, LoadingSpinner, Modal, PageHeader } from '../../../components';
import type { IColumn } from '../../../types';
import { homeworkApi } from '../api/homeworkApi';
import PhotoPicker from '../components/PhotoPicker';
import SessionPhotos from '../components/SessionPhotos';
import { HomeworkAnalytics, Homework, HomeworkIntegrity } from '../types';

type ClassItem = { id: number; class_name?: string; name?: string };
type SectionItem = { id: number; section_name?: string; name?: string };

/** YYYY-MM-DD in the device's own time zone */
const localDay = (d: Date = new Date()) => {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};
const prettyDay = (day: string) => {
  const [y, m, d] = day.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
};
const DATE_INPUT = 'w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500';

const efficiencyBadge = (score: number | null | undefined) => {
  if (score === null || score === undefined) return 'N/A';
  if (score >= 80) return 'High Efficiency';
  if (score >= 60) return 'Steady';
  return 'Needs Review';
};

// Checks on a submission: finished unusually fast, or the same photo as another student
const pageCheck = (integrity?: HomeworkIntegrity) => {
  if (!integrity) return { text: '-', tone: 'text-gray-500' };
  const problems = [
    integrity.fast_finish && (integrity.fast_finish_note || 'finished unusually fast'),
    integrity.same_photo_with?.length && `same photo as ${integrity.same_photo_with.join(', ')}`,
  ].filter(Boolean);
  if (problems.length) return { text: problems.join('; '), tone: 'text-amber-700 dark:text-amber-400' };
  return { text: 'OK', tone: 'text-emerald-700 dark:text-emerald-400' };
};

export default function TeacherHomeworkPage() {
  const [activeTab, setActiveTab] = useState<'create' | 'analytics'>('create');
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [sections, setSections] = useState<SectionItem[]>([]);
  // null = all classes (admins); otherwise only the sections this teacher teaches
  const [scopeSections, setScopeSections] = useState<Array<{ class_id: number; class_name: string; section_id: number; section_name: string }> | null>(null);
  const [scopeLoaded, setScopeLoaded] = useState(false);
  // subjects of the selected section (teachers: only the ones they teach there)
  const [subjects, setSubjects] = useState<Array<{ id: number; subject_name: string }>>([]);
  const [subjectsLoading, setSubjectsLoading] = useState(false);
  // photos of the homework (e.g. the board): shown to students once they start, and given to the AI
  const [photos, setPhotos] = useState<File[]>([]);
  const [drafting, setDrafting] = useState(false);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    homework_date: localDay(),
    class_id: 0,
    section_id: 0,
    subject: '',
    title: '',
    description: '',
    expected_time_minutes: 15,
    reference_answer_key: '',
  });

  // Create tab: the homework of the chosen date
  const [dayList, setDayList] = useState<Homework[]>([]);
  const [dayLoading, setDayLoading] = useState(false);
  const [deleting, setDeleting] = useState<Homework | null>(null);

  // Analytics tab
  const [analyticsDate, setAnalyticsDate] = useState(localDay());
  const [analyticsList, setAnalyticsList] = useState<Homework[]>([]);
  const [selectedHomeworkId, setSelectedHomeworkId] = useState<number>(0);
  const [analytics, setAnalytics] = useState<HomeworkAnalytics | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  // "Results" from the day list: select that homework once the date's list has loaded
  const pendingSelect = useRef<number | null>(null);
  // the submission whose photos are open (in a pop-up)
  const [photosFor, setPhotosFor] = useState<number | null>(null);

  const classLabel = (classId: number, sectionId: number) => {
    const scope = scopeSections?.find((r) => r.section_id === sectionId);
    if (scope) return `${scope.class_name} - ${scope.section_name}`;
    const cls = classes.find((c) => c.id === classId);
    const sec = sections.find((s) => s.id === sectionId);
    return [cls?.class_name || cls?.name, sec?.section_name || sec?.name].filter(Boolean).join(' - ') || `Class ${classId}`;
  };

  useEffect(() => {
    const init = async () => {
      try {
        const scope = await homeworkApi.getTeachingScope();
        let classRows: ClassItem[];
        if (scope.all) {
          setScopeSections(null);
          classRows = await homeworkApi.listClasses();
        } else {
          setScopeSections(scope.sections);
          const byId = new Map<number, ClassItem>();
          scope.sections.forEach((row) => byId.set(row.class_id, { id: row.class_id, class_name: row.class_name }));
          classRows = [...byId.values()];
        }
        setScopeLoaded(true);
        setClasses(classRows);
        if (classRows.length > 0) setForm((prev) => ({ ...prev, class_id: classRows[0].id }));
      } catch (error: unknown) {
        toast.error((error as { message?: string })?.message || 'Failed to load class list');
      }
    };
    void init();
  }, []);

  useEffect(() => {
    if (!form.class_id) return;
    const load = async () => {
      try {
        const sectionRows = scopeSections === null
          ? await homeworkApi.listSections(form.class_id)
          : scopeSections.filter((row) => row.class_id === form.class_id).map((row) => ({ id: row.section_id, section_name: row.section_name }));
        setSections(sectionRows);
        if (!form.section_id && sectionRows.length > 0) setForm((prev) => ({ ...prev, section_id: sectionRows[0].id }));
      } catch (error: unknown) {
        toast.error((error as { message?: string })?.message || 'Failed to load sections');
      }
    };
    void load();
  }, [form.class_id, form.section_id, scopeSections]);

  useEffect(() => {
    if (!form.section_id) {
      setSubjects([]);
      return;
    }
    let cancelled = false;
    setSubjectsLoading(true);
    homeworkApi
      .listSectionSubjects(form.section_id)
      .then((rows) => {
        if (cancelled) return;
        setSubjects(rows);
        setForm((prev) => (rows.some((row) => row.subject_name === prev.subject) ? prev : { ...prev, subject: rows.length === 1 ? rows[0].subject_name : '' }));
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setSubjects([]);
        toast.error((error as { message?: string })?.message || 'Failed to load subjects');
      })
      .finally(() => !cancelled && setSubjectsLoading(false));
    return () => {
      cancelled = true;
    };
  }, [form.section_id]);

  const loadDay = useCallback(async () => {
    setDayLoading(true);
    try {
      setDayList(await homeworkApi.listHomework({ date: form.homework_date }));
    } catch (error: unknown) {
      toast.error((error as { message?: string })?.message || 'Failed to load homework');
      setDayList([]);
    } finally {
      setDayLoading(false);
    }
  }, [form.homework_date]);

  useEffect(() => {
    if (activeTab === 'create') void loadDay();
  }, [activeTab, loadDay]);

  useEffect(() => {
    if (activeTab !== 'analytics') return;
    let cancelled = false;
    setAnalytics(null);
    setSelectedHomeworkId(0);
    homeworkApi.listHomework({ date: analyticsDate })
      .then((rows) => {
        if (cancelled) return;
        setAnalyticsList(rows);
        const wanted = pendingSelect.current;
        pendingSelect.current = null;
        if (wanted && rows.some((r) => r.id === wanted)) setSelectedHomeworkId(wanted);
        else if (rows.length === 1) setSelectedHomeworkId(rows[0].id);
      })
      .catch(() => !cancelled && setAnalyticsList([]));
    return () => {
      cancelled = true;
    };
  }, [activeTab, analyticsDate]);

  useEffect(() => {
    if (!selectedHomeworkId) {
      setAnalytics(null);
      return;
    }
    let cancelled = false;
    setAnalyticsLoading(true);
    setPhotosFor(null);
    homeworkApi.getHomeworkAnalytics(selectedHomeworkId)
      .then((res) => !cancelled && setAnalytics(res))
      .catch((error: unknown) => !cancelled && toast.error((error as { message?: string })?.message || 'Failed to load analytics'))
      .finally(() => !cancelled && setAnalyticsLoading(false));
    return () => {
      cancelled = true;
    };
  }, [selectedHomeworkId]);

  const onCreate = async () => {
    if (!form.section_id) {
      toast.error('Choose a class and section first.');
      return;
    }
    if (!form.subject) {
      toast.error('Choose the subject.');
      return;
    }
    if (!form.title.trim()) {
      toast.error('Give the homework a title.');
      return;
    }
    if (!form.description.trim() && photos.length === 0) {
      toast.error('Write the instructions or add a photo of the homework.');
      return;
    }
    try {
      setSaving(true);
      await homeworkApi.createHomework({
        class_id: form.class_id,
        section_id: form.section_id,
        subject: form.subject,
        title: form.title.trim(),
        description: form.description,
        expected_time_minutes: form.expected_time_minutes,
        reference_answer_key: form.reference_answer_key || undefined,
        homework_date: form.homework_date,
      }, photos);
      toast.success('Homework created');
      setPhotos([]);
      setForm((prev) => ({ ...prev, title: '', description: '', reference_answer_key: '' }));
      void loadDay();
    } catch (error: unknown) {
      toast.error((error as { message?: string })?.message || 'Failed to create homework');
    } finally {
      setSaving(false);
    }
  };

  const onDraftInstructions = async () => {
    if (photos.length === 0) return;
    try {
      setDrafting(true);
      const text = await homeworkApi.draftInstructionsFromPhotos(photos, form.subject || undefined);
      // keep anything the teacher already typed, add the drafted text after it
      setForm((prev) => ({ ...prev, description: prev.description.trim() ? `${prev.description.trim()}\n\n${text}` : text }));
      toast.success('Instructions filled from the photo. Check and edit before saving.');
    } catch (error: unknown) {
      toast.error((error as { message?: string })?.message || "Couldn't read the photo");
    } finally {
      setDrafting(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      await homeworkApi.deleteHomework(deleting.id);
      toast.success('Homework deleted');
      void loadDay();
    } catch (error: unknown) {
      toast.error((error as { message?: string })?.message || 'Failed to delete');
    } finally {
      setDeleting(null);
    }
  };

  type StudentRow = HomeworkAnalytics['students'][number];
  const photoRow = analytics?.students.find((row) => row.session_id === photosFor) || null;
  const studentColumns: IColumn<StudentRow>[] = [
    { key: 'sl_no', label: '#', className: '!text-center whitespace-nowrap !px-2', width: 40, render: (_v, _row, index) => index + 1 },
    { key: 'student_name', label: 'Student', className: 'whitespace-nowrap', render: (_v, row) => row.student_name || `Student ${row.student_id}` },
    {
      key: 'status', className: '!text-center whitespace-nowrap', label: 'Status',
      render: (_v, row) => (row.status === 'graded' || row.status === 'submitted' ? 'Done' : row.status === 'paused' ? 'Paused' : 'In progress'),
    },
    { key: 'active_duration_seconds', className: '!text-center whitespace-nowrap', label: 'Active Time', render: (_v, row) => `${Math.round(row.active_duration_seconds / 60)} min` },
    { key: 'hints_used_count', className: '!text-center whitespace-nowrap', label: 'Hints', render: (_v, row) => String(row.hints_used_count) },
    { key: 'accuracy_score', className: '!text-center whitespace-nowrap', label: 'Accuracy', render: (_v, row) => (row.accuracy_score ?? '-') },
    { key: 'efficiency_score', className: '!text-center whitespace-nowrap', label: 'Efficiency', render: (_v, row) => (row.efficiency_score ?? '-') },
    { key: 'band', className: '!text-center whitespace-nowrap', label: 'Band', render: (_v, row) => efficiencyBadge(row.efficiency_score) },
    {
      key: 'checks', className: '!text-center whitespace-nowrap', label: 'Checks', render: (_v, row) => {
        const c = pageCheck(row.integrity);
        return <span className={c.tone}>{c.text}</span>;
      },
    },
    {
      key: 'photos', className: '!text-center whitespace-nowrap', label: 'Photos', render: (_v, row) => ((row.page_count ?? 0) > 0
        ? <Button size="sm" variant="secondary" onClick={() => setPhotosFor(row.session_id)}>View</Button> : '-'),
    },
  ];

  const tabClass = (on: boolean) => `flex-1 px-6 py-3 text-sm font-medium transition-colors border-b-2 ${on
    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`;
  const today = localDay();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Homework AI"
        subtitle="Set daily homework and see how each class did"
        breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'Homework AI', href: '#' }]}
      />

      {scopeLoaded && scopeSections !== null && scopeSections.length === 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-700/40 dark:bg-amber-900/20 dark:text-amber-200">
          You aren't assigned to any class yet. Ask the institution admin to make you a class teacher, assign you subjects, or add you to a published timetable.
        </div>
      )}

      <div className="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
        <div className="border-b border-gray-200 dark:border-gray-700">
          <div className="flex" role="tablist">
            <button type="button" role="tab" aria-selected={activeTab === 'create'} onClick={() => setActiveTab('create')} className={tabClass(activeTab === 'create')}>
              Create Homework
            </button>
            <button type="button" role="tab" aria-selected={activeTab === 'analytics'} onClick={() => setActiveTab('analytics')} className={tabClass(activeTab === 'analytics')}>
              Analytics
            </button>
          </div>
        </div>

        <div className="p-6">
          {/* ===== CREATE HOMEWORK ===== */}
          {activeTab === 'create' && (
            <div className="space-y-6">
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                  <FormField label="Date" required>
                    <input type="date" value={form.homework_date} min={today} aria-label="Homework date"
                      onChange={(e) => e.target.value && setForm((prev) => ({ ...prev, homework_date: e.target.value }))}
                      className={DATE_INPUT} />
                  </FormField>
                  <FormField label="Class" required>
                    <FormSelect name="class_id" value={form.class_id || ''} placeholder="Select class"
                      onChange={(e) => setForm((prev) => ({ ...prev, class_id: Number(e.target.value), section_id: 0, subject: '' }))}
                      options={classes.map((row) => ({ value: row.id, label: row.class_name || row.name || `Class ${row.id}` }))} />
                  </FormField>
                  <FormField label="Section" required>
                    <FormSelect name="section_id" value={form.section_id || ''} placeholder={sections.length ? 'Select section' : 'No sections'}
                      onChange={(e) => setForm((prev) => ({ ...prev, section_id: Number(e.target.value), subject: '' }))}
                      options={sections.map((row) => ({ value: row.id, label: row.section_name || row.name || `Section ${row.id}` }))} />
                  </FormField>
                  <FormField label="Subject" required>
                    <FormSelect name="subject" value={form.subject}
                      placeholder={!form.section_id ? 'Select section first' : subjectsLoading ? 'Loading subjects…' : subjects.length === 0 ? 'No subjects for this section' : 'Select subject'}
                      disabled={!form.section_id || subjectsLoading || subjects.length === 0}
                      onChange={(e) => setForm((prev) => ({ ...prev, subject: e.target.value }))}
                      options={subjects.map((row) => ({ value: row.subject_name, label: row.subject_name }))} />
                  </FormField>
                  <FormField label="Expected time (minutes)" required>
                    <FormInput type="number" min={1} max={600} name="expected_time_minutes" value={form.expected_time_minutes}
                      onChange={(e) => setForm((prev) => ({ ...prev, expected_time_minutes: Number(e.target.value) }))} />
                  </FormField>
                </div>
                {form.section_id > 0 && !subjectsLoading && subjects.length === 0 && (
                  <p className="text-sm text-amber-700 dark:text-amber-400">
                    No subjects found for this section{scopeSections === null ? '. Add subjects to it in Class Management.' : ' that you teach.'}
                  </p>
                )}

                <FormField label="Title" required help='Students see only the title until they press Start. Keep it general (e.g. "Fractions practice", not "Exercise 5.2 Q1-10").'>
                  <FormInput name="title" value={form.title} maxLength={255} placeholder="e.g. Fractions practice"
                    onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))} />
                </FormField>

                <FormField label="Homework photos (optional, e.g. the board)">
                  <div className="rounded-lg border border-dashed border-gray-300 p-3 dark:border-gray-600">
                    <PhotoPicker photos={photos} onChange={setPhotos} max={5} label="Photos" disabled={saving} />
                    {photos.length > 0 && (
                      <Button type="button" size="sm" variant="outline" className="mt-2" onClick={onDraftInstructions} isLoading={drafting} loadingText="Reading photo…" disabled={saving}>
                        Fill instructions from photo
                      </Button>
                    )}
                  </div>
                </FormField>

                <FormField label="Instructions" required={photos.length === 0}>
                  <FormTextarea name="description" rows={4} value={form.description}
                    placeholder={photos.length > 0 ? 'Optional with a photo, e.g. "Do Q3-Q7 from the board"' : 'e.g. Solve these 5 sums...'}
                    onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))} />
                </FormField>
                <FormField label="Answer key / rubric (optional)" help="Only the AI grader sees this; students never do.">
                  <FormTextarea name="reference_answer_key" rows={3} value={form.reference_answer_key}
                    onChange={(e) => setForm((prev) => ({ ...prev, reference_answer_key: e.target.value }))} />
                </FormField>

                <div className="flex justify-end">
                  <Button onClick={onCreate} isLoading={saving} loadingText="Saving...">Create Homework</Button>
                </div>
              </div>

              <div className="border-t border-gray-200 dark:border-gray-700" />

              <div>
                <h3 className="mb-4 text-base font-semibold text-gray-900 dark:text-white" data-testid="day-heading">
                  Homework for {form.homework_date === today ? 'today' : prettyDay(form.homework_date)} ({dayList.length})
                </h3>
                {dayLoading ? (
                  <LoadingSpinner message="Loading homework..." />
                ) : dayList.length === 0 ? (
                  <p className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">No homework set for this date yet.</p>
                ) : (
                  <div className="space-y-3" data-testid="day-list">
                    {dayList.map((hw) => (
                      <div key={hw.id} className="flex flex-col gap-2 rounded-lg border border-gray-200 p-4 dark:border-gray-700 sm:flex-row sm:items-center sm:justify-between">
                        <div className="min-w-0">
                          <p className="font-medium text-gray-900 dark:text-white">{hw.title}</p>
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            {classLabel(hw.class_id, hw.section_id)} · {hw.subject} · about {hw.expected_time_minutes} min · {hw.started_count ?? 0} started
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" variant="secondary" onClick={() => { pendingSelect.current = hw.id; setAnalyticsDate(hw.homework_date || today); setActiveTab('analytics'); }}>
                            Results
                          </Button>
                          {!hw.started_count && <Button size="sm" variant="ghost" onClick={() => setDeleting(hw)}>Delete</Button>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ===== ANALYTICS ===== */}
          {activeTab === 'analytics' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <FormField label="Date">
                  <input type="date" value={analyticsDate} aria-label="Analytics date"
                    onChange={(e) => e.target.value && setAnalyticsDate(e.target.value)} className={DATE_INPUT} />
                </FormField>
                <div className="md:col-span-2">
                  <FormField label="Homework">
                    <FormSelect name="homework" value={selectedHomeworkId || ''}
                      placeholder={analyticsList.length ? 'Select homework' : 'No homework on this date'}
                      disabled={analyticsList.length === 0}
                      onChange={(e) => setSelectedHomeworkId(Number(e.target.value))}
                      options={analyticsList.map((row) => ({ value: row.id, label: `${row.title} · ${classLabel(row.class_id, row.section_id)} · ${row.subject}` }))} />
                  </FormField>
                </div>
              </div>

              {analyticsLoading && <LoadingSpinner message="Loading results..." />}
              {analytics && !analyticsLoading && (
                <div className="space-y-4" data-testid="analytics">
                  <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
                    <MetricCard title="Completion %" value={`${analytics.completion_rate}%`} />
                    <MetricCard title="Avg Accuracy" value={`${analytics.average_accuracy_score}%`} />
                    <MetricCard title="Avg Efficiency" value={`${analytics.average_efficiency_score}%`} />
                    <MetricCard title="Avg Time" value={`${Math.round(analytics.average_time_seconds / 60)} min`} />
                    <MetricCard title="Expected" value={`${analytics.expected_time_minutes} min`} />
                  </div>

                  <DataTable
                    columns={studentColumns}
                    data={analytics.students.map((row) => ({ ...row, id: row.session_id }))}
                    emptyMessage="No student has started this homework yet."
                  />

                  <div>
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Common Conceptual Mistakes</h3>
                    {analytics.common_conceptual_mistakes.length === 0 ? (
                      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">No recurring mistakes found yet.</p>
                    ) : (
                      <ul className="mt-2 space-y-1 text-sm text-gray-700 dark:text-gray-300">
                        {analytics.common_conceptual_mistakes.map((row) => (
                          <li key={row.mistake}>{row.mistake} ({row.count})</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <Modal isOpen={!!photoRow} onClose={() => setPhotosFor(null)} size="lg"
        title={photoRow ? `${photoRow.student_name || `Student ${photoRow.student_id}`}: photos` : ''}>
        {photoRow && (
          <SessionPhotos sessionId={photoRow.session_id} pageCount={photoRow.page_count ?? 0} />
        )}
      </Modal>

      <ConfirmDialog
        isOpen={!!deleting}
        title="Delete homework?"
        message={deleting ? `Delete "${deleting.title}"? No student has started it yet.` : ''}
        confirmText="Delete"
        type="danger"
        onConfirm={confirmDelete}
        onCancel={() => setDeleting(null)}
      />
    </div>
  );
}

function MetricCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
      <p className="text-xs uppercase tracking-wider text-gray-500">{title}</p>
      <p className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{value}</p>
    </div>
  );
}
