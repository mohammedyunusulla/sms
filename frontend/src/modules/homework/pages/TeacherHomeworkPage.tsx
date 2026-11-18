import { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import QRCode from 'qrcode';
import { useNavigate } from 'react-router';
import { homeworkApi } from '../api/homeworkApi';
import { HomeworkAnalytics, HomeworkAssignment, StudentStickerRow } from '../types';

type ClassItem = { id: number; class_name?: string; name?: string };
type SectionItem = { id: number; section_name?: string; name?: string };

export default function TeacherHomeworkPage() {
  const navigate = useNavigate();
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [sections, setSections] = useState<SectionItem[]>([]);
  const [assignments, setAssignments] = useState<HomeworkAssignment[]>([]);
  const [stickers, setStickers] = useState<StudentStickerRow[]>([]);
  const [analytics, setAnalytics] = useState<HomeworkAnalytics | null>(null);
  const [qrImages, setQrImages] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

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
        const classRows = await homeworkApi.listClasses();
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
        const [sectionRows, stickerRows, assignmentRows] = await Promise.all([
          homeworkApi.listSections(form.class_id),
          homeworkApi.listStickers(form.class_id, form.section_id || undefined),
          homeworkApi.listAssignments({ class_id: form.class_id, section_id: form.section_id || undefined }),
        ]);
        setSections(sectionRows);
        if (!form.section_id && sectionRows.length > 0) {
          setForm((prev) => ({ ...prev, section_id: sectionRows[0].id }));
        }
        setStickers(stickerRows);
        setAssignments(assignmentRows);
      } catch (error: any) {
        toast.error(error?.message || 'Failed to load class homework data');
      }
    };
    void loadClassData();
  }, [form.class_id, form.section_id]);

  useEffect(() => {
    const buildQrImages = async () => {
      const entries = await Promise.all(
        stickers
          .filter((item) => !!item.qr_code_value)
          .map(async (item) => {
            const value = item.qr_code_value as string;
            const dataUrl = await QRCode.toDataURL(value, { width: 84, margin: 1 });
            return [value, dataUrl] as const;
          })
      );
      setQrImages(Object.fromEntries(entries));
    };
    void buildQrImages();
  }, [stickers]);

  const efficiencyBadge = (score: number | null | undefined) => {
    if (score === null || score === undefined) return 'N/A';
    if (score >= 80) return 'High Efficiency';
    if (score >= 60) return 'Steady';
    return 'Needs Review';
  };

  const classLabel = useMemo(() => {
    const selected = classes.find((item) => item.id === form.class_id);
    return selected?.class_name || selected?.name || 'Class';
  }, [classes, form.class_id]);

  const onCreateAssignment = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.section_id) {
      toast.error('Please create/select a section first from Class Management.');
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
      });
      toast.success('Homework assignment created');
      const assignmentRows = await homeworkApi.listAssignments({
        class_id: form.class_id,
        section_id: form.section_id || undefined,
      });
      setAssignments(assignmentRows);
      setForm((prev) => ({ ...prev, title: '', description: '', reference_answer_key: '', due_date: '' }));
    } catch (error: any) {
      toast.error(error?.message || 'Failed to create assignment');
    } finally {
      setLoading(false);
    }
  };

  const onGenerateSticker = async (studentId: number) => {
    try {
      await homeworkApi.assignSticker(studentId);
      toast.success('Sticker generated');
      const stickerRows = await homeworkApi.listStickers(form.class_id, form.section_id || undefined);
      setStickers(stickerRows);
    } catch (error: any) {
      toast.error(error?.message || 'Failed to assign sticker');
    }
  };

  const onLoadAnalytics = async () => {
    if (!selectedAssignmentId) return;
    try {
      setLoading(true);
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
          Create homework, generate student QR stickers, and review class efficiency.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <form onSubmit={onCreateAssignment} className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Create Assignment</h2>
          {!hasSections && form.class_id > 0 && (
            <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-700/40 dark:bg-amber-900/20 dark:text-amber-200">
              No sections found for this class. Create one in Class Management, then return here.
            </div>
          )}
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <select
              value={form.class_id || ''}
              onChange={(event) => setForm((prev) => ({ ...prev, class_id: Number(event.target.value) }))}
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
            <button
              type="button"
              onClick={() => form.class_id && navigate(`/classes/${form.class_id}`)}
              disabled={!form.class_id}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
            >
              Manage Sections
            </button>
            <input
              placeholder="Subject"
              value={form.subject}
              onChange={(event) => setForm((prev) => ({ ...prev, subject: event.target.value }))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
              required
            />
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
          <textarea
            placeholder="Instructions"
            value={form.description}
            onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
            className="mt-3 h-24 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
            required
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

        <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Sticker Manager ({classLabel})</h2>
          <div className="space-y-3">
            {stickers.length === 0 && (
              <p className="text-sm text-gray-500 dark:text-gray-400">No students found for selected class/section.</p>
            )}
            {stickers.map((student) => (
              <div key={student.student_id} className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
                <div className="mb-2 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-gray-900 dark:text-white">{student.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Roll No: {student.roll_no || '-'}</p>
                  </div>
                  <button
                    onClick={() => onGenerateSticker(student.student_id)}
                    className="rounded-md bg-gray-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-gray-900"
                  >
                    {student.sticker_assigned ? 'Regenerate' : 'Generate'}
                  </button>
                </div>
                {student.qr_code_value ? (
                  <div className="flex items-center gap-3">
                    <img
                      src={qrImages[student.qr_code_value] || ''}
                      alt={`QR for ${student.name}`}
                      className="h-[84px] w-[84px] rounded border border-gray-200"
                    />
                    <div>
                      <p className="text-xs text-gray-600 dark:text-gray-300">{student.qr_code_value}</p>
                      <p className="text-xs text-gray-400">Print and stick in notebook</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-gray-500 dark:text-gray-400">Sticker not assigned yet.</p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Homework & Efficiency Analytics</h2>
        <div className="flex flex-col gap-3 md:flex-row">
          <select
            value={selectedAssignmentId || ''}
            onChange={(event) => setSelectedAssignmentId(Number(event.target.value))}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 md:max-w-lg"
          >
            <option value="">Select assignment</option>
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
                    <th className="py-2 pr-3">Student ID</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3">Active Time</th>
                    <th className="py-2 pr-3">Hints</th>
                    <th className="py-2 pr-3">Accuracy</th>
                    <th className="py-2 pr-3">Efficiency</th>
                    <th className="py-2 pr-3">Band</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                  {analytics.students.map((row) => (
                    <tr key={row.session_id}>
                      <td className="py-2 pr-3">{row.student_id}</td>
                      <td className="py-2 pr-3">{row.status}</td>
                      <td className="py-2 pr-3">{Math.round(row.active_duration_seconds / 60)} min</td>
                      <td className="py-2 pr-3">{row.hints_used_count}</td>
                      <td className="py-2 pr-3">{row.accuracy_score ?? '-'}</td>
                      <td className="py-2 pr-3">{row.efficiency_score ?? '-'}</td>
                      <td className="py-2 pr-3">{efficiencyBadge(row.efficiency_score)}</td>
                    </tr>
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
