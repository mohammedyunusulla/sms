export type HomeworkSessionStatus = 'in_progress' | 'paused' | 'submitted' | 'graded';

export interface HomeworkAssignment {
  id: number;
  class_id: number;
  section_id: number;
  subject: string;
  title: string;
  description: string;
  reference_answer_key?: string | null;
  expected_time_minutes: number;
  due_date?: string | null;
  /** number of homework photos (e.g. of the board) */
  photo_count?: number;
  created_by: number;
  created_at: string;
  current_session_status?: HomeworkSessionStatus | null;
}

export interface HomeworkSession {
  id: number;
  student_id: number;
  assignment_id: number;
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
}

export interface HomeworkAnalytics {
  assignment: HomeworkAssignment;
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
  }>;
}

export interface StudentStickerRow {
  student_id: number;
  name: string;
  roll_no?: string;
  class_id?: number;
  section_id?: number;
  qr_code_value?: string | null;
  sticker_assigned: boolean;
}
