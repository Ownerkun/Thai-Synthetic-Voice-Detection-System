// Types ตรงกับ Pydantic schema ใน app/schemas/* ของ backend (ดู docs/API_MOCKUP.md)

export type Verdict = 'real' | 'spoof';

export interface Health {
  status: string;
  model_version: string;
  using_mock_model: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface SegmentResult {
  index: number;
  start_seconds: number;
  end_seconds: number;
  spoof_probability: number;
  is_spoof: boolean;
}

export interface DetectionResult {
  id: string | null;
  original_filename: string;
  duration_seconds: number;
  sample_rate: number;
  num_segments: number;
  mean_probability: number;
  max_probability: number;
  threshold_used: number;
  verdict: Verdict;
  possible_partial_spoof: boolean;
  model_version: string;
  processing_ms: number;
  segments: SegmentResult[];
  saved_to_history: boolean;
}

// (string & {}) = รับค่าใหม่ที่ backend อาจเพิ่มในอนาคตได้ โดยยังมี autocomplete ของค่าที่รู้จัก
export type FailureReason =
  | 'unsupported_format'
  | 'file_too_large'
  | 'empty_audio'
  | 'decode_failed'
  | (string & {});

export interface FailedFile {
  filename: string;
  reason: FailureReason;
  message: string;
}

export interface BatchDetectionResult {
  results: DetectionResult[];
  failed_files: FailedFile[];
}

export interface DetectionRecord {
  id: string;
  created_at: string;
  original_filename: string;
  duration_seconds: number;
  verdict: Verdict;
  mean_probability: number;
  max_probability: number;
  possible_partial_spoof: boolean;
}

export interface DetectionDetail extends DetectionRecord {
  threshold_used: number;
  model_version: string;
  processing_ms: number;
  segments: SegmentResult[];
}

export interface Feedback {
  id: string;
  detection_id: string;
  user_agrees: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface FeedbackHistoryItem extends Feedback {
  original_filename: string;
  verdict: Verdict;
}

export interface Threshold {
  id: string;
  value: number;
  effective_from: string;
  changed_by_admin_id: string;
  note: string | null;
}

export interface ThresholdUpdateResponse {
  previous_value: number | null;
  current: Threshold;
}

export interface StatsOverview {
  total_detections: number;
  total_spoof_verdicts: number;
  total_real_verdicts: number;
  total_users: number;
  feedback_agreement_rate: number | null;
}

export interface AdminUser {
  id: string;
  email: string;
  display_name: string | null;
  created_at: string;
  last_login_at: string | null;
  is_active: boolean;
  detection_count: number;
}

export interface AdminUserList {
  items: AdminUser[];
  total: number;
  limit: number;
  offset: number;
}

// ---- /users/me (PR #21) ----
export interface UserProfile {
  id: string;
  email: string;
  display_name: string | null;
  created_at: string;
}

// ---- /admin/detections (PR #20, #22) ----
export type DetectionSort = 'created_at' | 'mean_probability' | 'processing_ms';
export type FeedbackFilter = 'agree' | 'disagree' | 'none';

export interface AdminDetectionFilters {
  limit: number;
  offset: number;
  sort?: DetectionSort;
  order?: 'asc' | 'desc';
  verdict?: Verdict;
  date_from?: string; // YYYY-MM-DD ตามเวลาไทย
  date_to?: string;
  q?: string;
  user_id?: string;
  user_email?: string;
  guest?: boolean;
  model_version?: string;
  partial_spoof?: boolean;
  feedback?: FeedbackFilter;
  min_prob?: number;
  max_prob?: number;
}

export interface AdminDetectionItem {
  id: string;
  created_at: string;
  original_filename: string;
  duration_seconds: number;
  num_segments: number;
  mean_probability: number;
  max_probability: number;
  threshold_used: number;
  verdict: Verdict;
  possible_partial_spoof: boolean;
  model_version: string;
  processing_ms: number;
  user_id: string | null;
  user_email: string | null;
  feedback: 'agree' | 'disagree' | null;
}

export interface AdminDetectionList {
  items: AdminDetectionItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface AdminDetectionDetail extends AdminDetectionItem {
  sample_rate: number;
  file_size_bytes: number;
  audio_format: string;
  feedback_created_at: string | null;
  feedback_updated_at: string | null;
  segments: SegmentResult[];
}
