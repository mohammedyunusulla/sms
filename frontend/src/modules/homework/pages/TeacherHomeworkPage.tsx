import { Fragment, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { homeworkApi } from '../api/homeworkApi';
import PhotoPicker from '../components/PhotoPicker';
import SessionPhotos from '../components/SessionPhotos';
import { HomeworkAnalytics, HomeworkAssignment, HomeworkIntegrity } from '../types';

type ClassItem = { id: number; class_name?: string; name?: string };
type SectionItem = { id: number; section_name?: string; name?: string };

export default function TeacherHomeworkPage() {
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [sections, setSections] = useState<SectionItem[]>([]);
  const [assignments, setAssignments] = useState<HomeworkAssignment[]>([]);
  const [analytics, setAnalytics] = useState<HomeworkAnalytics | null>(null);
  // the submission whose photos (start page + finished pages) are open in the analytics table
  const [photosFor, setPhotosFor] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  // null = all classes (admins); otherwise only the sections this teacher teaches
  const [scopeSections, setScopeSections] = useState<Array<{ class_id: number; class_name: string; section_id: number; section_name: string }> | null>(null);
  const [scopeLoaded, setScopeLoaded] = useState(false);
  // subjects of the selected section (teachers: only the ones they teach there)
  const [subjects, setSubjects] = useState<Array<{ id: number; subject_name: string }>>([]);
  const [subjectsLoading, setSubjectsLoading] = useState(false);
  // photos of the homework (e.g. the board): shown to students and given to the AI
  const [photos, setPhotos] = useState<File[]>([]);
  const [drafting, setDrafting] = useState(false);

  const [form, setForm] = useState({
    class_id: 0,
    section_id: 0,
    subject: '',
    title: '',
    description: '',
    expected_time_minutes: 15,
    reference_answer_key: '',
    due_date: '',
  });
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<number>(0);
  const hasSections = sections.length > 0;

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
        if (classRows.length > 0) {
          setForm((prev) => ({ ...prev, class_id: classRows[0].id }));
        }
      } catch (error: any) {
        toast.error(error?.message || 'Failed to load class list');
      }
    };
    void init();
  }, []);

  useEffect(() => {
    if (!form.class_id) return;
    const loadClassData = async () => {
      try {
        const [sectionRows, assignmentRows] = await Promise.all([
          scopeSections === null
            ? homeworkApi.listSections(form.class_id)
            : Promise.resolve(
                scopeSections
                  .filter((row) => row.class_id === form.class_id)
                  .map((row) => ({ id: row.section_id, section_name: row.section_name }))
              ),
          homeworkApi.listAssignments({ class_id: form.class_id, section_id: form.section_id || undefined }),
        ]);
        setSections(sectionRows);
        if (!form.section_id && sectionRows.length > 0) {
          setForm((prev) => ({ ...prev, section_id: sectionRows[0].id }));
        }
        setAssignments(assignmentRows);
      } catch (error: any) {
        toast.error(error?.message || 'Failed to load class homework data');
      }
    };
    void loadClassData();
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
        setForm((prev) => (rows.some((row) => row.subject_name === prev.subject) ? prev : { ...prev, subject: '' }));
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

  const efficiencyBadge = (score: number | null | undefined) => {
    if (score === null || score === undefined) return 'N/A';
    if (score >= 80) return 'High Efficiency';
    if (score >= 60) return 'Steady';
    return 'Needs Review';
  };

  const onCreateAssignment = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.section_id) {
      toast.error('Please create/select a section first from Class Management.');
      return;
    }
    if (!form.description.trim() && photos.length === 0) {
      toast.error('Write the instructions or add a photo of the homework.');
      return;
    }
    try {
      setLoading(true);
      await homeworkApi.createAssignment({
        class_id: form.class_id,
        section_id: form.section_id,
        subject: form.subject,
        title: form.title,
        description: form.description,
        expected_time_minutes: form.expected_time_minutes,
        reference_answer_key: form.reference_answer_key || undefined,
        due_date: form.due_date || undefined,
      }, photos);
      toast.success('Homework created');
      setPhotos([]);
      const assignmentRows = await homeworkApi.listAssignments({
        class_id: form.class_id,
        section_id: form.section_id || undefined,
      });
      setAssignments(assignmentRows);
      setForm((prev) => ({ ...prev, title: '', description: '', reference_answer_key: '', due_date: '' }));
    } catch (error: any) {
      toast.error(error?.message || 'Failed to create homework');
    } finally {
      setLoading(false);
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

  // Page check for a submission: QR matched by the server; blank start / same page judged by the AI from the photos
  const pageCheck = (integrity?: HomeworkIntegrity) => {
    if (!integrity || integrity.qr_matched === undefined || integrity.qr_matched === null) return { text: '-', tone: 'text-gray-500' };
    const problems = [
      integrity.page_blank_at_start === false && 'page not blank at start',
      integrity.same_page_as_start === false && 'looks like a different page',
    ].filter(Boolean);
    return problems.length
      ? { text: `⚠ ${problems.join('; ')}`, tone: 'text-amber-700 dark:text-amber-400' }
      : { text: '✓ Same QR page', tone: 'text-emerald-700 dark:text-emerald-400' };
  };

  const onLoadAnalytics = async () => {
    if (!selectedAssignmentId) return;
    try {
      setLoading(true);
      setPhotosFor(null);
      const response = await homeworkApi.getAssignmentAnalytics(selectedAssignmentId);
      setAnalytics(response);
    } catch (error: any) {
      toast.error(error?.message || 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">AI Homework & Efficiency (Teacher)</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Create homework and review class efficiency. Students start each homework on a notebook page with a school QR sticker.
        </p>
      </div>

      {scopeLoaded && scopeSections !== null && scopeSections.length === 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-700/40 dark:bg-amber-900/20 dark:text-amber-200">
          You aren't assigned to any class yet. Ask the school admin to make you a class teacher, assign you subjects, or add you to a published timetable.
        </div>
      )}

      <div className="grid grid-cols-1 gap-6">
        <form onSubmit={onCreateAssignment} className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Create Homework</h2>
          {form.section_id > 0 && !subjectsLoading && subjects.length === 0 && (
            <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-700/40 dark:bg-amber-900/20 dark:text-amber-200">
              No subjects found for this section{scopeSections === null ? '. Add subjects to it in Class Management.' : ' that you teach.'}
            </div>
          )}
          {!hasSections && form.class_id > 0 && (
            <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-700/40 dark:bg-amber-900/20 dark:text-amber-200">
              No sections found for this class. Create one in Class Management, then return here.
            </div>
          )}
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <select
              value={form.class_id || ''}
              onChange={(event) => setForm((prev) => ({ ...prev, class_id: Number(event.target.value), section_id: 0, subject: '' }))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
            >
              <option value="">Select class</option>
              {classes.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.class_name || row.name || `Class ${row.id}`}
                </option>
              ))}
            </select>
            <select
              value={form.section_id || ''}
              onChange={(event) => setForm((prev) => ({ ...prev, section_id: Number(event.target.value) }))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
            >
              <option value="">Select section</option>
              {sections.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.section_name || row.name || `Section ${row.id}`}
                </option>
              ))}
            </select>
            <select
              aria-label="Subject"
              name="subject"
              value={form.subject}
              onChange={(event) => setForm((prev) => ({ ...prev, subject: event.target.value }))}
              disabled={!form.section_id || subjectsLoading || subjects.length === 0}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm disabled:opacity-60 dark:border-gray-600 dark:bg-gray-800"
              required
            >
              <option value="">
                {!form.section_id ? 'Select section first' : subjectsLoading ? 'Loading subjects…' : subjects.length === 0 ? 'No subjects for this section' : 'Select subject'}
              </option>
              {subjects.map((row) => (
                <option key={row.id} value={row.subject_name}>
                  {row.subject_name}
                </option>
              ))}
            </select>
            <input
              placeholder="Expected minutes"
              type="number"
              min={1}
              value={form.expected_time_minutes}
              onChange={(event) => setForm((prev) => ({ ...prev, expected_time_minutes: Number(event.target.value) }))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
              required
            />
          </div>
          <input
            placeholder="Title"
            value={form.title}
            onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))}
            className="mt-3 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
            required
          />
          <div className="mt-3 rounded-lg border border-dashed border-gray-300 p-3 dark:border-gray-600">
            <PhotoPicker photos={photos} onChange={setPhotos} max={5} label="Homework photos (e.g. the board)" disabled={loading} />
            {photos.length > 0 && (
              <button
                type="button"
                onClick={onDraftInstructions}
                disabled={drafting || loading}
                className="mt-2 rounded-lg border border-indigo-300 px-3 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-50 disabled:opacity-60 dark:border-indigo-700 dark:text-indigo-300 dark:hover:bg-indigo-900/20"
              >
                {drafting ? 'Reading photo…' : '✨ Fill instructions from photo'}
              </button>
            )}
          </div>
          <textarea
            placeholder={photos.length > 0 ? 'Instructions (optional with a photo, e.g. "Do Q3-Q7 from the board")' : 'Instructions'}
            value={form.description}
            onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
            className="mt-3 h-24 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
            required={photos.length === 0}
            name="description"
          />
          <textarea
            placeholder="Optional answer key / rubric"
            value={form.reference_answer_key}
            onChange={(event) => setForm((prev) => ({ ...prev, reference_answer_key: event.target.value }))}
            className="mt-3 h-24 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
          />
          <input
            type="datetime-local"
            value={form.due_date}
            onChange={(event) => setForm((prev) => ({ ...prev, due_date: event.target.value }))}
            className="mt-3 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
          />
          <button
            type="submit"
            disabled={loading}
            className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-70"
          >
            {loading ? 'Saving...' : 'Create Homework'}
          </button>
        </form>

      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Homework & Efficiency Analytics</h2>
        <div className="flex flex-col gap-3 md:flex-row">
          <select
            value={selectedAssignmentId || ''}
            onChange={(event) => setSelectedAssignmentId(Number(event.target.value))}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 md:max-w-lg"
          >
            <option value="">Select homework</option>
            {assignments.map((row) => (
              <option key={row.id} value={row.id}>
                {row.title} ({row.subject})
              </option>
            ))}
          </select>
          <button
            onClick={onLoadAnalytics}
            disabled={!selectedAssignmentId || loading}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-70"
          >
            Load Analytics
          </button>
        </div>

        {analytics && (
          <div className="mt-5 space-y-4">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
              <MetricCard title="Completion %" value={`${analytics.completion_rate}%`} />
              <MetricCard title="Avg Accuracy" value={`${analytics.average_accuracy_score}%`} />
              <MetricCard title="Avg Efficiency" value={`${analytics.average_efficiency_score}%`} />
              <MetricCard title="Avg Time" value={`${Math.round(analytics.average_time_seconds / 60)} min`} />
              <MetricCard title="Expected" value={`${analytics.expected_time_minutes} min`} />
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm dark:divide-gray-700">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wider text-gray-500">
                    <th className="py-2 pr-3">Student</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3">Active Time</th>
                    <th className="py-2 pr-3">Hints</th>
                    <th className="py-2 pr-3">Accuracy</th>
                    <th className="py-2 pr-3">Efficiency</th>
                    <th className="py-2 pr-3">Band</th>
                    <th className="py-2 pr-3">Page check</th>
                    <th className="py-2 pr-3">Photos</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                  {analytics.students.map((row) => (
                    <Fragment key={row.session_id}>
                    <tr>
                      <td className="py-2 pr-3">{row.student_name || `Student ${row.student_id}`}</td>
                      <td className="py-2 pr-3">{row.status}</td>
                      <td className="py-2 pr-3">{Math.round(row.active_duration_seconds / 60)} min</td>
                      <td className="py-2 pr-3">{row.hints_used_count}</td>
                      <td className="py-2 pr-3">{row.accuracy_score ?? '-'}</td>
                      <td className="py-2 pr-3">{row.efficiency_score ?? '-'}</td>
                      <td className="py-2 pr-3">{efficiencyBadge(row.efficiency_score)}</td>
                      <td className={`py-2 pr-3 ${pageCheck(row.integrity).tone}`} title={row.integrity?.notes || ''}>{pageCheck(row.integrity).text}</td>
                      <td className="py-2 pr-3">
                        {(row.has_start_photo || (row.page_count ?? 0) > 0) ? (
                          <button
                            type="button"
                            onClick={() => setPhotosFor(photosFor === row.session_id ? null : row.session_id)}
                            className="rounded-md border border-gray-300 px-2 py-1 text-xs font-medium hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800"
                          >
                            {photosFor === row.session_id ? 'Hide' : 'View'}
                          </button>
                        ) : '-'}
                      </td>
                    </tr>
                    {photosFor === row.session_id && (
                      <tr>
                        <td colSpan={9} className="bg-gray-50 p-3 dark:bg-gray-800/50">
                          <SessionPhotos sessionId={row.session_id} hasStartPhoto={!!row.has_start_photo} pageCount={row.page_count ?? 0} />
                          {row.integrity?.notes && <p className="mt-2 text-xs text-gray-600 dark:text-gray-300">AI page check: {row.integrity.notes}</p>}
                        </td>
                      </tr>
                    )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Common Conceptual Mistakes</h3>
              {analytics.common_conceptual_mistakes.length === 0 ? (
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">No recurring mistakes found yet.</p>
              ) : (
                <ul className="mt-2 space-y-1 text-sm text-gray-700 dark:text-gray-300">
                  {analytics.common_conceptual_mistakes.map((row) => (
                    <li key={row.mistake}>
                      {row.mistake} ({row.count})
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </div>
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
