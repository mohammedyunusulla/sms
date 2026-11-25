import { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import PageInfo from '../../../components/common/PageInfo';
import { getPageHelp } from '../../../config/pageHelp';
import { useAuth } from '../../../hooks/useAuth';
import { homeworkApi } from '../api/homeworkApi';
import HomeworkPhotos from '../components/HomeworkPhotos';
import PhotoPicker from '../components/PhotoPicker';
import SessionPhotos from '../components/SessionPhotos';
import { HomeworkAssignment, HomeworkSession } from '../types';

const studentHelp = getPageHelp('/homework/student', undefined);

function formatDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const hh = String(hours).padStart(2, '0');
  const mm = String(minutes).padStart(2, '0');
  const ss = String(seconds).padStart(2, '0');
  return `${hh}:${mm}:${ss}`;
}

function formatDateTime(value?: string | null): string {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
}

export default function StudentHomeworkPage() {
  const { user } = useAuth();
  const [assignments, setAssignments] = useState<HomeworkAssignment[]>([]);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<number>(0);
  // photo of the blank notebook page with the institution's QR sticker (starts the homework)
  const [startPhotos, setStartPhotos] = useState<File[]>([]);
  const [session, setSession] = useState<HomeworkSession | null>(null);
  const [hintText, setHintText] = useState('');
  const [hintFile, setHintFile] = useState<File | undefined>(undefined);
  const [submissionFiles, setSubmissionFiles] = useState<File[]>([]);
  const [latestHint, setLatestHint] = useState('');
  const [grading, setGrading] = useState<Record<string, unknown> | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [tick, setTick] = useState(0);

  const role = (user?.role || '').toUpperCase();
  const isStudent = role === 'STUDENT' || role === 'LEARNER';

  const selectedAssignment = assignments.find((item) => item.id === selectedAssignmentId) || null;

  useEffect(() => {
    const load = async () => {
      if (!isStudent) return;
      try {
        const rows = await homeworkApi.listAssignments();
        setAssignments(rows);
      } catch (error: any) {
        toast.error(error?.message || 'Failed to load homework list');
      }
    };
    void load();
  }, [isStudent]);

  useEffect(() => {
    if (!session || session.status !== 'in_progress') return;
    const timer = window.setInterval(() => setTick((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [session]);

  useEffect(() => {
    if (!selectedAssignmentId) {
      setSession(null);
      setGrading(null);
      setLatestHint('');
      setSubmissionFiles([]);
      return;
    }
    const loadLatestSession = async () => {
      try {
        const latest = await homeworkApi.latestSession(selectedAssignmentId);
        setSession(latest);
        setGrading(latest?.ai_feedback_json || null);
        setLatestHint('');
        setSubmissionFiles([]);
      } catch {
        setSession(null);
        setGrading(null);
      }
    };
    void loadLatestSession();
  }, [selectedAssignmentId]);

  const liveDuration = useMemo(() => {
    if (!session) return 0;
    const base = session.active_duration_seconds || 0;
    if (session.status !== 'in_progress' || !session.last_resumed_at) return base;
    const resumedAt = new Date(session.last_resumed_at).getTime();
    const now = Date.now();
    const live = Math.floor((now - resumedAt) / 1000);
    return base + Math.max(live, 0);
  }, [session, tick]);

  if (!isStudent) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-800">
        This view is available only for student accounts.
      </div>
    );
  }

  // An open (in progress / paused) session resumes without a new photo
  const canResume = selectedAssignment?.current_session_status === 'in_progress' || selectedAssignment?.current_session_status === 'paused';
  const isSessionActive = !!session && (session.status === 'in_progress' || session.status === 'paused');
  const isSessionCompleted = !!session && (session.status === 'submitted' || session.status === 'graded');

  const startSession = async () => {
    if (!selectedAssignmentId) {
      toast.error('Select the homework first.');
      return;
    }
    if (!canResume && startPhotos.length === 0) {
      toast.error('Take a photo of the blank page with its QR sticker to start.');
      return;
    }
    try {
      setIsBusy(true);
      const response = await homeworkApi.startSession(selectedAssignmentId, canResume ? undefined : startPhotos[0]);
      setSession(response);
      setGrading(response.ai_feedback_json || null);
      setStartPhotos([]);
      toast.success(canResume ? 'Homework resumed' : 'Homework started');
    } catch (error: any) {
      toast.error(error?.message || 'Failed to start session');
    } finally {
      setIsBusy(false);
    }
  };

  const togglePause = async () => {
    if (!session) return;
    try {
      setIsBusy(true);
      const response = await homeworkApi.togglePause(session.id);
      setSession(response);
      toast.success(response.status === 'paused' ? 'Session paused' : 'Session resumed');
    } catch (error: any) {
      toast.error(error?.message || 'Unable to update session status');
    } finally {
      setIsBusy(false);
    }
  };

  const askHint = async () => {
    if (!session) return;
    if (!hintText.trim() && !hintFile) {
      toast.error('Enter a question or add a notebook photo for a hint.');
      return;
    }
    try {
      setIsBusy(true);
      const response = await homeworkApi.askHint(session.id, hintText.trim() || undefined, hintFile);
      setLatestHint(response.hint);
      setHintText('');
      setHintFile(undefined);
      setSession((prev) => (prev ? { ...prev, hints_used_count: response.hints_used_count } : prev));
      toast.success('Hint generated');
    } catch (error: any) {
      toast.error(error?.message || 'Failed to fetch hint');
    } finally {
      setIsBusy(false);
    }
  };

  const submitHomework = async () => {
    if (!session) return;
    if (submissionFiles.length === 0) {
      toast.error('Add a photo of the finished page with its QR sticker.');
      return;
    }
    try {
      setIsBusy(true);
      const response = await homeworkApi.submitSession(session.id, submissionFiles);
      setSession(response.session);
      setGrading(response.grading);
      toast.success('Homework submitted and graded');
    } catch (error: any) {
      toast.error(error?.message || 'Failed to submit homework');
    } finally {
      setIsBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          AI Homework Session
          {studentHelp && <span className="ml-2 inline-flex align-middle"><PageInfo title="AI Homework" help={studentHelp} /></span>}
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Photograph the blank page with its QR sticker, work with the timer, ask for hints, then photograph the finished page for AI grading.</p>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
        <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Step 1: Start</h2>
        <div className="space-y-4">
          <select
            value={selectedAssignmentId || ''}
            onChange={(event) => setSelectedAssignmentId(Number(event.target.value))}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 md:w-1/2"
          >
            <option value="">Select homework</option>
            {assignments.map((assignment) => (
              <option key={assignment.id} value={assignment.id}>
                {assignment.title} ({assignment.subject})
              </option>
            ))}
          </select>
          {canResume ? (
            <p className="text-sm text-gray-600 dark:text-gray-300">You've already started this homework. Tap Resume to continue.</p>
          ) : (
            <div>
              <p className="mb-2 text-sm text-gray-600 dark:text-gray-300">
                Take a photo of the <strong>blank page</strong> you will write on, with its <strong>QR sticker</strong> clearly visible.
              </p>
              <PhotoPicker
                photos={startPhotos}
                onChange={setStartPhotos}
                max={1}
                label="Blank page with QR sticker"
                disabled={isBusy}
                tip="Hold the phone close so the QR sticker is large, in focus and fully in the photo."
                preserveOriginal
                liveQrScan
              />
            </div>
          )}
        </div>
        <button
          onClick={startSession}
          disabled={isBusy}
          className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-70"
        >
          {canResume ? 'Resume Homework' : 'Start Homework'}
        </button>
      </div>

      {selectedAssignment && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{selectedAssignment.title}</h3>
          {selectedAssignment.description && (
            <p className="mt-1 whitespace-pre-line text-sm text-gray-500 dark:text-gray-400">{selectedAssignment.description}</p>
          )}
          {!!selectedAssignment.photo_count && (
            <div className="mt-3">
              <HomeworkPhotos assignmentId={selectedAssignment.id} count={selectedAssignment.photo_count} />
            </div>
          )}
          <p className="mt-2 text-xs text-gray-500">Expected time: {selectedAssignment.expected_time_minutes} minutes</p>
        </div>
      )}

      {session && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
          <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
            {isSessionCompleted ? 'Step 2: View Result (Read-only)' : 'Step 2: Focus & AI Tutor'}
          </h2>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
            <Metric title="Status" value={session.status} />
            <Metric title="Active Time" value={formatDuration(liveDuration)} />
            <Metric title="Hints Used" value={String(session.hints_used_count)} />
            <Metric title="Session ID" value={String(session.id)} />
          </div>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
            <Metric title="Started At" value={formatDateTime(session.started_at)} />
            <Metric title="Finished At" value={formatDateTime(session.submitted_at)} />
            <Metric title="Correctness" value={session.accuracy_score != null ? `${session.accuracy_score}%` : '-'} />
          </div>
          {isSessionCompleted && (
            <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-300">
              Submission is complete. Editing and re-upload are disabled for this session.
            </div>
          )}
          <div className="mt-4 flex gap-2">
            <button
              onClick={togglePause}
              disabled={isBusy || !isSessionActive}
              className="rounded-lg bg-gray-800 px-4 py-2 text-sm font-semibold text-white hover:bg-gray-900 disabled:opacity-70"
            >
              {session.status === 'paused' ? 'Resume' : 'Pause / Break'}
            </button>
          </div>
          <div className="mt-5 rounded-lg border border-indigo-200 bg-indigo-50 p-4 dark:border-indigo-900/40 dark:bg-indigo-900/10">
            <h3 className="text-sm font-semibold text-indigo-800 dark:text-indigo-300">Ask AI for a Hint (Socratic)</h3>
            <textarea
              value={hintText}
              onChange={(event) => setHintText(event.target.value)}
              placeholder="Write your doubt..."
              disabled={!isSessionActive || isBusy}
              className="mt-2 h-24 w-full rounded-lg border border-indigo-200 bg-white px-3 py-2 text-sm dark:border-indigo-800 dark:bg-gray-800"
            />
            <input
              type="file"
              accept="image/*"
              onChange={(event) => setHintFile(event.target.files?.[0] || undefined)}
              disabled={!isSessionActive || isBusy}
              className="mt-2 block text-sm"
            />
            <button
              onClick={askHint}
              disabled={isBusy || !isSessionActive}
              className="mt-3 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-70"
            >
              Get Hint
            </button>
            {latestHint && (
              <div className="mt-3 rounded-lg border border-indigo-200 bg-white p-3 text-sm text-gray-700 dark:border-indigo-800 dark:bg-gray-900 dark:text-gray-200">
                {latestHint}
              </div>
            )}
          </div>
          {isSessionCompleted && (
            <div className="mt-5">
              <SessionPhotos
                sessionId={session.id}
                hasStartPhoto={!!session.has_start_photo}
                pageCount={Array.isArray(session.submission_image_paths) ? session.submission_image_paths.length : 0}
              />
            </div>
          )}
        </div>
      )}

      {isSessionActive && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
          <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Step 3: Finish & Upload</h2>
          <p className="mb-2 text-sm text-gray-600 dark:text-gray-300">
            Photograph the <strong>same page</strong> now that it's done, with its <strong>QR sticker</strong> visible.
            If your answer continues on more pages, add those photos too.
          </p>
          <PhotoPicker
            photos={submissionFiles}
            onChange={setSubmissionFiles}
            max={10}
            label="Finished pages"
            disabled={isBusy}
            preserveOriginal
          />
          <button
            onClick={submitHomework}
            disabled={isBusy}
            className="mt-4 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-70"
          >
            Submit for AI Grading
          </button>
        </div>
      )}

      {isSessionCompleted && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 dark:border-emerald-800 dark:bg-emerald-900/10">
          <h2 className="text-lg font-semibold text-emerald-900 dark:text-emerald-300">AI Feedback & Report Card</h2>
          <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Metric title="Accuracy" value={`${session.accuracy_score ?? 0}%`} />
            <Metric title="Efficiency" value={`${session.efficiency_score ?? 0}%`} />
            <Metric title="Active Time" value={formatDuration(session.active_duration_seconds)} />
            <Metric title="Hints Used" value={String(session.hints_used_count)} />
          </div>
          {grading && (
            <div className="mt-4 space-y-2 text-sm text-gray-700 dark:text-gray-200">
              <p><span className="font-semibold">Summary:</span> {String(grading.overall_summary || '-')}</p>
              <p><span className="font-semibold">Strengths:</span> {Array.isArray(grading.strengths) ? grading.strengths.join(', ') : '-'}</p>
              <p><span className="font-semibold">Areas to Improve:</span> {Array.isArray(grading.areas_to_improve) ? grading.areas_to_improve.join(', ') : '-'}</p>
              <p><span className="font-semibold">Common Mistakes:</span> {Array.isArray(grading.common_mistakes) ? grading.common_mistakes.join(', ') : '-'}</p>
              {Array.isArray(grading.line_by_line_review) && grading.line_by_line_review.length > 0 && (
                <div>
                  <p className="font-semibold">Explanation by Answer</p>
                  <ul className="ml-5 list-disc space-y-1">
                    {grading.line_by_line_review.map((item, index) => (
                      <li key={index}>{String(item)}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Metric({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900">
      <p className="text-xs uppercase tracking-wider text-gray-500">{title}</p>
      <p className="mt-1 text-base font-semibold text-gray-900 dark:text-white">{value}</p>
    </div>
  );
}
