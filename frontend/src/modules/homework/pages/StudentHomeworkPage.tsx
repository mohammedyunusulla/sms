/**
 * Homework AI - student. Two tabs:
 *   Today's Homework: today's homework (plus any started earlier and not yet handed in). Pick one, press Start
 *     to see the questions (the timer starts then), ask for hints, upload photos of the work for AI grading.
 *   Past Homeworks: pick a date to see that day's homework, view only (questions and your result).
 * (Homework AI is its own module; it is not the Assignments feature.)
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { Badge, Button, ConfirmDialog, FormField, FormTextarea, LoadingSpinner, PageHeader } from '../../../components';
import { useAuth } from '../../../hooks/useAuth';
import { ChevronDownIcon } from '../../../icons';
import { homeworkApi } from '../api/homeworkApi';
import HomeworkPhotos from '../components/HomeworkPhotos';
import PhotoPicker from '../components/PhotoPicker';
import SessionPhotos from '../components/SessionPhotos';
import { Homework, HomeworkSession } from '../types';

const localDay = (d: Date = new Date()) => {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};
const yesterday = () => {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return localDay(d);
};
const prettyDay = (day?: string | null) => {
  if (!day) return '';
  const [y, m, d] = day.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' });
};
function formatDuration(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  return [h, m, s].map((n) => String(n).padStart(2, '0')).join(':');
}
function formatDateTime(value?: string | null): string {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '-' : date.toLocaleString();
}
const errorText = (error: unknown, fallback: string) => (error as { message?: string })?.message || fallback;
const DATE_INPUT = 'w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500';

/** status badge for a homework card */
function StatusBadge({ hw }: { hw: Homework }) {
  const s = hw.current_session_status;
  if (s === 'graded' || s === 'submitted') {
    return <Badge variant="success" size="sm">Done{hw.my_accuracy_score != null ? ` · ${Math.round(hw.my_accuracy_score)}%` : ''}</Badge>;
  }
  if (s === 'in_progress' || s === 'paused') return <Badge variant="warning" size="sm">In progress</Badge>;
  return hw.is_past ? <Badge variant="danger" size="sm">Not done</Badge> : <Badge variant="secondary" size="sm">Not started</Badge>;
}

export default function StudentHomeworkPage() {
  const { user } = useAuth();
  const role = (user?.role || '').toUpperCase();
  const isStudent = role === 'STUDENT' || role === 'LEARNER';

  const [activeTab, setActiveTab] = useState<'today' | 'past'>('today');
  const [allHomework, setAllHomework] = useState<Homework[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [pastDate, setPastDate] = useState(yesterday());
  const [pastList, setPastList] = useState<Homework[]>([]);
  const [pastLoading, setPastLoading] = useState(false);

  const [selectedId, setSelectedId] = useState<number>(0);
  const [session, setSession] = useState<HomeworkSession | null>(null);
  const [confirmStart, setConfirmStart] = useState(false);
  const [hintText, setHintText] = useState('');
  const [hintFile, setHintFile] = useState<File | undefined>(undefined);
  const [latestHint, setLatestHint] = useState('');
  const [submissionFiles, setSubmissionFiles] = useState<File[]>([]);
  const [grading, setGrading] = useState<Record<string, unknown> | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [now, setNow] = useState(Date.now());

  const today = localDay();

  const loadAll = useCallback(async () => {
    setListLoading(true);
    try {
      setAllHomework(await homeworkApi.listHomework());
    } catch (error: unknown) {
      toast.error(errorText(error, 'Failed to load homework'));
    } finally {
      setListLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isStudent) void loadAll();
  }, [isStudent, loadAll]);

  useEffect(() => {
    if (!isStudent || activeTab !== 'past') return;
    let cancelled = false;
    setPastLoading(true);
    homeworkApi.listHomework({ date: pastDate })
      .then((rows) => !cancelled && setPastList(rows))
      .catch(() => !cancelled && setPastList([]))
      .finally(() => !cancelled && setPastLoading(false));
    return () => {
      cancelled = true;
    };
  }, [isStudent, activeTab, pastDate]);

  // Today: today's homework, plus anything started on an earlier day and not handed in yet
  const todayList = useMemo(() => allHomework.filter((hw) => hw.homework_date === today
    || (!!hw.is_past && (hw.current_session_status === 'in_progress' || hw.current_session_status === 'paused'))), [allHomework, today]);

  const selected = useMemo(
    () => [...todayList, ...pastList].find((hw) => hw.id === selectedId) || null,
    [todayList, pastList, selectedId],
  );

  // the selected homework's session (with its questions once started)
  useEffect(() => {
    setSession(null);
    setGrading(null);
    setLatestHint('');
    setSubmissionFiles([]);
    if (!selectedId) return;
    let cancelled = false;
    homeworkApi.latestSession(selectedId)
      .then((latest) => {
        if (cancelled) return;
        setSession(latest);
        setGrading(latest?.ai_feedback_json || null);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  // live timer while in progress
  useEffect(() => {
    if (!session || session.status !== 'in_progress') return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [session]);

  if (!isStudent) {
    return <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-800">This view is available only for student accounts.</div>;
  }

  const isActive = !!session && (session.status === 'in_progress' || session.status === 'paused');
  const isDone = !!session && (session.status === 'submitted' || session.status === 'graded');
  const viewOnly = activeTab === 'past' && !isActive;
  const questions = session?.homework || (selected && !selected.questions_hidden ? selected : null);
  const liveDuration = !session ? 0
    : session.status === 'in_progress' && session.last_resumed_at
      ? (session.active_duration_seconds || 0) + Math.max(Math.floor((now - new Date(session.last_resumed_at).getTime()) / 1000), 0)
      : session.active_duration_seconds || 0;

  const startOrResume = async () => {
    setConfirmStart(false);
    if (!selectedId) return;
    try {
      setIsBusy(true);
      const response = await homeworkApi.startSession(selectedId);
      setSession(response);
      setGrading(response.ai_feedback_json || null);
      setNow(Date.now());
      setAllHomework((rows) => rows.map((row) => (row.id === selectedId ? { ...row, current_session_status: response.status } : row)));
      toast.success('Homework started: the timer is running');
    } catch (error: unknown) {
      toast.error(errorText(error, 'Failed to start'));
    } finally {
      setIsBusy(false);
    }
  };

  const togglePause = async () => {
    if (!session) return;
    try {
      setIsBusy(true);
      const response = await homeworkApi.togglePause(session.id);
      setSession((prev) => (prev ? { ...response, homework: prev.homework } : response));
      setNow(Date.now());
      toast.success(response.status === 'paused' ? 'Paused' : 'Resumed');
    } catch (error: unknown) {
      toast.error(errorText(error, 'Unable to update'));
    } finally {
      setIsBusy(false);
    }
  };

  const askHint = async () => {
    if (!session) return;
    if (!hintText.trim() && !hintFile) {
      toast.error('Write your doubt or add a photo of your notebook.');
      return;
    }
    try {
      setIsBusy(true);
      const response = await homeworkApi.askHint(session.id, hintText.trim() || undefined, hintFile);
      setLatestHint(response.hint);
      setHintText('');
      setHintFile(undefined);
      setSession((prev) => (prev ? { ...prev, hints_used_count: response.hints_used_count } : prev));
    } catch (error: unknown) {
      toast.error(errorText(error, 'Failed to get a hint'));
    } finally {
      setIsBusy(false);
    }
  };

  const submit = async () => {
    if (!session) return;
    if (submissionFiles.length === 0) {
      toast.error('Add a photo of your finished work.');
      return;
    }
    try {
      setIsBusy(true);
      const response = await homeworkApi.submitSession(session.id, submissionFiles);
      setSession((prev) => ({ ...response.session, homework: prev?.homework }));
      setGrading(response.grading);
      setAllHomework((rows) => rows.map((row) => (row.id === selectedId
        ? { ...row, current_session_status: response.session.status, my_accuracy_score: response.session.accuracy_score } : row)));
      toast.success('Homework submitted and graded');
    } catch (error: unknown) {
      toast.error(errorText(error, 'Failed to submit'));
    } finally {
      setIsBusy(false);
    }
  };

  const tabClass = (on: boolean) => `flex-1 px-6 py-3 text-sm font-medium transition-colors border-b-2 ${on
    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`;

  const detail = () => (
    <div className="space-y-4 border-t border-gray-200 p-4 dark:border-gray-700" data-testid="homework-card">
          {/* only before starting; once started, Pause / Resume sits with the timer below */}
          {!viewOnly && !session && (
            <Button onClick={() => setConfirmStart(true)} isLoading={isBusy} loadingText="...">Start Homework</Button>
          )}

          {questions ? (
            <div>
              {questions.description && (
                <p className="whitespace-pre-line text-sm text-gray-700 dark:text-gray-300" data-testid="homework-questions">{questions.description}</p>
              )}
              {!!questions.photo_count && (
                <div className="mt-3"><HomeworkPhotos homeworkId={questions.id} count={questions.photo_count} /></div>
              )}
            </div>
          ) : (
            <p className="rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-500 dark:bg-gray-700/50 dark:text-gray-400" data-testid="questions-hidden-note">
              The questions appear when you press <strong>Start</strong>, and the timer starts at the same time. Have your notebook ready.
            </p>
          )}

          {viewOnly && !session && (
            <p className="text-sm text-red-600 dark:text-red-400" data-testid="not-done">You didn't do this homework.</p>
          )}

      {session && (isActive || isDone) && (
        <div>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Metric title="Status" value={isDone ? 'Done' : session.status === 'paused' ? 'Paused' : 'In progress'} />
            <Metric title="Active Time" value={formatDuration(liveDuration)} testId="active-time" />
            <Metric title="Hints Used" value={String(session.hints_used_count)} />
            <Metric title="Started At" value={formatDateTime(session.started_at)} />
          </div>

          {isActive && (
            <div className="mt-4 space-y-4">
              <Button variant="secondary" onClick={togglePause} disabled={isBusy}>
                {session.status === 'paused' ? 'Resume' : 'Pause / Break'}
              </Button>

              {session.status === 'in_progress' && (
                <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4 dark:border-indigo-900/40 dark:bg-indigo-900/10">
                  <FormField label="Stuck? Ask the AI for a hint">
                    <FormTextarea name="hint" rows={3} value={hintText} placeholder="Write your doubt..." onChange={(e) => setHintText(e.target.value)} />
                  </FormField>
                  <input type="file" accept="image/*" aria-label="Notebook photo for the hint"
                    onChange={(e) => setHintFile(e.target.files?.[0] || undefined)} className="mt-2 block text-sm" />
                  <Button size="sm" className="mt-3" onClick={askHint} isLoading={isBusy} loadingText="Thinking...">Get Hint</Button>
                  {latestHint && <div className="mt-3 rounded-lg border border-indigo-200 bg-white p-3 text-sm text-gray-700 dark:border-indigo-800 dark:bg-gray-900 dark:text-gray-200">{latestHint}</div>}
                </div>
              )}

              <div className="border-t border-gray-200 pt-4 dark:border-gray-700">
                <h4 className="mb-2 text-base font-semibold text-gray-900 dark:text-white">Finish & upload</h4>
                <p className="mb-2 text-sm text-gray-600 dark:text-gray-300">Photograph your <strong>finished work</strong>. If it's on more than one page, add a photo of each page.</p>
                <PhotoPicker photos={submissionFiles} onChange={setSubmissionFiles} max={10} label="Finished pages" disabled={isBusy} preserveOriginal />
                <Button variant="success" className="mt-4" onClick={submit} isLoading={isBusy} loadingText="Grading...">Submit for AI Grading</Button>
              </div>
            </div>
          )}

          {isDone && (
            <div className="mt-4 space-y-3">
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                <Metric title="Accuracy" value={`${session.accuracy_score ?? 0}%`} />
                <Metric title="Efficiency" value={`${session.efficiency_score ?? 0}%`} />
                <Metric title="Finished At" value={formatDateTime(session.submitted_at)} />
              </div>
              {grading && (
                <div className="space-y-2 text-sm text-gray-700 dark:text-gray-200">
                  <p><span className="font-semibold">Summary:</span> {String(grading.overall_summary || '-')}</p>
                  <p><span className="font-semibold">Strengths:</span> {Array.isArray(grading.strengths) ? grading.strengths.join(', ') : '-'}</p>
                  <p><span className="font-semibold">Areas to Improve:</span> {Array.isArray(grading.areas_to_improve) ? grading.areas_to_improve.join(', ') : '-'}</p>
                  {Array.isArray(grading.line_by_line_review) && grading.line_by_line_review.length > 0 && (
                    <div>
                      <p className="font-semibold">Explanation by Answer</p>
                      <ul className="ml-5 list-disc space-y-1">{grading.line_by_line_review.map((item, i) => <li key={i}>{String(item)}</li>)}</ul>
                    </div>
                  )}
                </div>
              )}
              <SessionPhotos sessionId={session.id} hasStartPhoto={!!session.has_start_photo}
                pageCount={Array.isArray(session.submission_image_paths) ? session.submission_image_paths.length : 0} />
            </div>
          )}
        </div>
      )}
    </div>
  );

  const cards = (rows: Homework[], empty: string) => (
    rows.length === 0 ? (
      <p className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">{empty}</p>
    ) : (
      <div className="space-y-3" data-testid="homework-cards">
        {rows.map((hw) => {
          const open = selectedId === hw.id;
          return (
            <div key={hw.id} className={`overflow-hidden rounded-lg border ${open ? 'border-blue-500 dark:border-blue-400' : 'border-gray-200 dark:border-gray-700'}`}>
              <button type="button" aria-expanded={open} onClick={() => setSelectedId(open ? 0 : hw.id)}
                className="flex w-full items-center gap-3 p-4 text-left transition-colors hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <span className={`shrink-0 text-gray-500 transition-transform ${open ? 'rotate-180' : ''}`}><ChevronDownIcon /></span>
                <span className="min-w-0 flex-1">
                  <span className="block font-medium text-gray-900 dark:text-white">{hw.title}</span>
                  <span className="mt-0.5 block text-sm text-gray-500 dark:text-gray-400">
                    {hw.subject} · about {hw.expected_time_minutes} min{hw.homework_date && hw.homework_date !== today ? ` · ${prettyDay(hw.homework_date)}` : ''}
                  </span>
                </span>
                <StatusBadge hw={hw} />
              </button>
              {open && detail()}
            </div>
          );
        })}
      </div>
    )
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Homework AI"
        subtitle="Do your homework with a timer and AI hints, and see your results"
        breadcrumbs={[{ label: 'Dashboard', href: '/dashboard' }, { label: 'Homework AI', href: '#' }]}
      />

      <div className="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
        <div className="border-b border-gray-200 dark:border-gray-700">
          <div className="flex" role="tablist">
            <button type="button" role="tab" aria-selected={activeTab === 'today'} className={tabClass(activeTab === 'today')}
              onClick={() => { setActiveTab('today'); setSelectedId(0); }}>
              Today's Homework
            </button>
            <button type="button" role="tab" aria-selected={activeTab === 'past'} className={tabClass(activeTab === 'past')}
              onClick={() => { setActiveTab('past'); setSelectedId(0); }}>
              Past Homeworks
            </button>
          </div>
        </div>

        <div className="p-6">
          {activeTab === 'today' && (listLoading ? <LoadingSpinner message="Loading homework..." /> : cards(todayList, 'No homework for today.'))}

          {activeTab === 'past' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <FormField label="Select Date">
                  <input type="date" value={pastDate} max={yesterday()} aria-label="Past homework date"
                    onChange={(e) => { if (e.target.value) { setPastDate(e.target.value); setSelectedId(0); } }} className={DATE_INPUT} />
                </FormField>
              </div>
              {pastLoading ? <LoadingSpinner message="Loading homework..." /> : cards(pastList, 'No homework on this date.')}
            </div>
          )}
        </div>
      </div>

      <ConfirmDialog
        isOpen={confirmStart}
        title="Start this homework?"
        message={`The questions will appear and the timer starts now${selected ? ` (about ${selected.expected_time_minutes} min)` : ''}. You can pause for a break, but you can start only once.`}
        confirmText="Start now"
        cancelText="Not yet"
        type="info"
        onConfirm={startOrResume}
        onCancel={() => setConfirmStart(false)}
      />
    </div>
  );
}

function Metric({ title, value, testId }: { title: string; value: string; testId?: string }) {
  return (
    <div className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
      <p className="text-xs uppercase tracking-wider text-gray-500">{title}</p>
      <p className="mt-1 text-base font-semibold text-gray-900 dark:text-white" data-testid={testId}>{value}</p>
    </div>
  );
}
