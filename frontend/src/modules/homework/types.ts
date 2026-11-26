export type HomeworkSessionStatus = 'in_progress' | 'paused' | 'submitted' | 'graded';

export interface Homework {
  id: number;
  class_id: number;
  section_id: number;
  subject: string;
  title: string;
  /** null for students until they start (the questions are hidden) */
  description: string | null;
  questions_hidden?: boolean;
  reference_answer_key?: string | null;
  expected_time_minutes: number;
  /** the day the homework is for (YYYY-MM-DD) */
  homework_date?: string | null;
  /** before today: view only */
  is_past?: boolean;
  /** student's own result (list) */
  my_accuracy_score?: number | null;
  my_efficiency_score?: number | null;
  /** teacher: how many students started it (0 = can be deleted) */
  started_count?: number;
  /** number of homework photos (e.g. of the board) */
  photo_count?: number;
  created_by: number;
  created_at: string;
  current_session_status?: HomeworkSessionStatus | null;
}

export interface HomeworkSession {
  id: number;
  student_id: number;
  homework_id: number;
  status: HomeworkSessionStatus;
  started_at?: string | null;
  last_resumed_at?: string | null;
  submitted_at?: string | null;
  active_duration_seconds: number;
  hints_used_count: number;
  submission_image_paths: string[];
  accuracy_score?: number | null;
  efficiency_score?: number | null;
  ai_feedback_json?: Record<string, unknown>;
  integrity?: HomeworkIntegrity;
  /** the homework with its questions, returned once the student has started */
  homework?: Homework;
}

export interface HomeworkAnalytics {
  homework: Homework;
  total_sessions: number;
  submitted_count: number;
  completion_rate: number;
  average_time_seconds: number;
  expected_time_minutes: number;
  average_accuracy_score: number;
  average_efficiency_score: number;
  efficiency_distribution: {
    high: number;
    steady: number;
    needs_review: number;
  };
  common_conceptual_mistakes: Array<{ mistake: string; count: number }>;
  students: Array<{
    session_id: number;
    student_id: number;
    status: HomeworkSessionStatus;
    active_duration_seconds: number;
    hints_used_count: number;
    accuracy_score?: number | null;
    efficiency_score?: number | null;
    submitted_at?: string | null;
    ai_feedback_json?: Record<string, unknown>;
    student_name?: string | null;
    page_count?: number;
    integrity?: HomeworkIntegrity;
  }>;
}

/** Checks on a submission, worked out when the teacher opens Analytics. */
export interface HomeworkIntegrity {
  flagged?: boolean;
  /** finished far quicker than the class usually takes */
  fast_finish?: boolean;
  fast_finish_note?: string;
  /** students whose page photo is nearly identical */
  same_photo_with?: string[];
}
