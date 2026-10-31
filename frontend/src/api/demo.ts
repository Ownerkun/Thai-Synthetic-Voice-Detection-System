// ===== โหมดสาธิต (GitHub Pages) =====
// จำลอง backend ทั้งหมดในเบราว์เซอร์ ทำตามกติกาเดียวกับ FastAPI backend (app/) ให้มากที่สุด:
// - รับเฉพาะ .wav/.flac, ไม่เกิน 20 MB, ตรวจตามลำดับ นามสกุล → ว่าง → ขนาด → อ่านเสียง
// - ใช้ 10 วินาทีแรก แบ่งช่วงละ 4 วินาที คะแนนจำลองแบบ deterministic จาก hash ของไฟล์ (เหมือน MockSpoofAnalyzer)
// - ผลตัดสินจากค่าเฉลี่ย ≥ threshold, partial spoof เมื่อ std > 0.25
// ข้อมูลทั้งหมด (บัญชี ประวัติ feedback threshold) เก็บใน localStorage ของแต่ละเบราว์เซอร์ ไม่ส่งออกไปที่ไหน

import { ApiError } from './errors';
import type {
  AdminDetectionDetail,
  AdminDetectionFilters,
  AdminDetectionItem,
  AdminDetectionList,
  AdminUser,
  AdminUserList,
  BatchDetectionResult,
  DetectionDetail,
  DetectionRecord,
  DetectionResult,
  FailedFile,
  Feedback,
  FeedbackHistoryItem,
  Health,
  SegmentResult,
  StatsOverview,
  Threshold,
  ThresholdUpdateResponse,
  TokenResponse,
  UserProfile,
} from './types';

export const DEMO_ADMIN = { username: 'admin', password: 'demo1234' };

const STORE_KEY = 'tsvd.demo';
const SESSION_KEY = 'tsvd.session'; // ตรงกับ AuthContext
const MODEL_VERSION = 'demo (จำลองในเบราว์เซอร์)';
const MAX_BYTES = 20 * 1024 * 1024;
const MAX_SECONDS = 10;
const SEGMENT_SECONDS = 4;
const DEFAULT_THRESHOLD = 0.5;
const TOKEN_DAYS = 7;

interface DemoUser {
  id: string;
  email: string;
  password_hash: string;
  display_name: string | null;
  created_at: string;
  last_login_at: string | null;
  is_active: boolean;
}

interface DemoRecord extends DetectionDetail {
  user_id: string | null;
  file_size_bytes?: number;
  audio_format?: string;
  sample_rate?: number;
}

interface DemoFeedback extends Feedback {
  user_id: string;
}

interface DemoStore {
  admin_id: string;
  users: DemoUser[];
  records: DemoRecord[];
  feedback: DemoFeedback[];
  thresholds: Threshold[];
}

// ---------- storage ----------
let memoryStore: DemoStore | null = null;

function load(): DemoStore {
  if (memoryStore) return memoryStore;
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) memoryStore = JSON.parse(raw) as DemoStore;
  } catch {
    /* ใช้ค่าใหม่ */
  }
  memoryStore ??= { admin_id: uuid(), users: [], records: [], feedback: [], thresholds: [] };
  return memoryStore;
}

function save(store: DemoStore) {
  memoryStore = store;
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(store));
  } catch {
    /* storage เต็ม/ถูกปิด ข้อมูลอยู่ได้แค่ในแท็บนี้ */
  }
}

// ---------- helpers ----------
const delay = (ms = 250) => new Promise((r) => setTimeout(r, ms));
const now = () => new Date().toISOString();

function uuid(): string {
  return typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
      });
}

async function sha256(data: ArrayBuffer | string): Promise<Uint8Array> {
  const bytes = typeof data === 'string' ? new TextEncoder().encode(data) : data;
  return new Uint8Array(await crypto.subtle.digest('SHA-256', bytes));
}

const toHex = (bytes: Uint8Array) => Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
const hashPassword = async (password: string) => toHex(await sha256(`tsvd-demo:${password}`));

function base64url(text: string) {
  return btoa(unescape(encodeURIComponent(text))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

// token หน้าตาเหมือน JWT เพื่อให้ AuthContext อ่าน role/exp ได้ (ไม่มีลายเซ็นจริง เพราะเป็นข้อมูลในเครื่องตัวเอง)
function makeToken(sub: string, role: 'user' | 'admin'): TokenResponse {
  const exp = Math.floor(Date.now() / 1000) + TOKEN_DAYS * 24 * 3600;
  const token = [base64url('{"alg":"none","typ":"JWT"}'), base64url(JSON.stringify({ sub, role, exp })), 'demo'].join('.');
  return { access_token: token, token_type: 'bearer' };
}

function currentClaims(): { sub: string; role: string } | null {
  try {
    const token = localStorage.getItem(SESSION_KEY);
    if (!token) return null;
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))) as {
      sub: string;
      role: string;
      exp: number;
    };
    return payload.exp * 1000 > Date.now() ? payload : null;
  } catch {
    return null;
  }
}

function optionalUser(store: DemoStore): DemoUser | null {
  const claims = currentClaims();
  if (!claims || claims.role !== 'user') return null;
  const user = store.users.find((u) => u.id === claims.sub);
  return user && user.is_active ? user : null;
}

function requireUser(store: DemoStore): DemoUser {
  const claims = currentClaims();
  if (!claims || claims.role !== 'user') throw new ApiError(401, 'Authentication required');
  const user = store.users.find((u) => u.id === claims.sub);
  if (!user || !user.is_active) throw new ApiError(401, 'Invalid or suspended account');
  return user;
}

function requireAdmin(store: DemoStore) {
  const claims = currentClaims();
  if (!claims || claims.role !== 'admin' || claims.sub !== store.admin_id) {
    throw new ApiError(401, 'Insufficient permissions');
  }
}

function ownedRecord(store: DemoStore, id: string, userId: string): DemoRecord {
  const record = store.records.find((r) => r.id === id && r.user_id === userId);
  if (!record) throw new ApiError(404, 'Record not found');
  return record;
}

const currentThreshold = (store: DemoStore) => store.thresholds[0]?.value ?? DEFAULT_THRESHOLD;

const toRecordOut = (r: DemoRecord): DetectionRecord => ({
  id: r.id,
  created_at: r.created_at,
  original_filename: r.original_filename,
  duration_seconds: r.duration_seconds,
  verdict: r.verdict,
  mean_probability: r.mean_probability,
  max_probability: r.max_probability,
  possible_partial_spoof: r.possible_partial_spoof,
});

const toFeedbackOut = ({ user_id: _ignored, ...fb }: DemoFeedback): Feedback => fb;

// ---------- audio analysis (จำลอง) ----------
async function audioDuration(bytes: ArrayBuffer): Promise<number> {
  const ctx = new AudioContext();
  try {
    const decoded = await ctx.decodeAudioData(bytes.slice(0));
    return decoded.duration;
  } finally {
    void ctx.close();
  }
}

async function analyze(file: File, threshold: number): Promise<Omit<DetectionResult, 'id' | 'saved_to_history'>> {
  const started = performance.now();
  const bytes = await file.arrayBuffer();

  let duration: number;
  try {
    duration = await audioDuration(bytes);
  } catch {
    throw { reason: 'decode_failed', message: 'Could not read the audio data - the file may be corrupted or not a real audio file' };
  }
  if (!(duration > 0)) throw { reason: 'empty_audio', message: 'The file contains no audio samples' };
  duration = Math.min(duration, MAX_SECONDS);

  const count = Math.max(1, Math.ceil(duration / SEGMENT_SECONDS - 1e-9));
  const seed = toHex(await sha256(bytes));
  const probs: number[] = [];
  for (let i = 0; i < count; i++) {
    const digest = await sha256(`${seed}:${i}`);
    probs.push(new DataView(digest.buffer).getUint32(0, true) / 0xffffffff);
  }

  const segments: SegmentResult[] = probs.map((p, i) => {
    const start = i * SEGMENT_SECONDS;
    const end = duration > start ? Math.min(start + SEGMENT_SECONDS, duration) : start + SEGMENT_SECONDS;
    return {
      index: i,
      start_seconds: Math.round(start * 1000) / 1000,
      end_seconds: Math.round(end * 1000) / 1000,
      spoof_probability: p,
      is_spoof: p >= threshold,
    };
  });
  const mean = probs.reduce((a, b) => a + b, 0) / probs.length;
  const std = Math.sqrt(probs.reduce((a, p) => a + (p - mean) ** 2, 0) / probs.length);

  return {
    original_filename: file.name,
    duration_seconds: Math.round(duration * 1000) / 1000,
    sample_rate: 16000,
    num_segments: segments.length,
    mean_probability: Math.round(mean * 10000) / 10000,
    max_probability: Math.round(Math.max(...probs) * 10000) / 10000,
    threshold_used: threshold,
    verdict: mean >= threshold ? 'spoof' : 'real',
    possible_partial_spoof: segments.length > 1 && std > 0.25,
    model_version: MODEL_VERSION,
    processing_ms: Math.round(performance.now() - started),
    segments,
  };
}

function validateFormat(file: File): FailedFile | null {
  const dot = file.name.lastIndexOf('.');
  const ext = dot >= 0 ? file.name.slice(dot).toLowerCase() : '';
  if (ext !== '.wav' && ext !== '.flac') {
    return {
      filename: file.name,
      reason: 'unsupported_format',
      message: `Unsupported file type '${ext || '(none)'}' - allowed: .wav, .flac`,
    };
  }
  if (file.size <= 0) return { filename: file.name, reason: 'empty_audio', message: 'The file is empty' };
  if (file.size > MAX_BYTES) {
    return {
      filename: file.name,
      reason: 'file_too_large',
      message: `The file is ${(file.size / 1024 / 1024).toFixed(1)} MB - the limit is 20 MB`,
    };
  }
  return null;
}

// ---------- API (รูปแบบเดียวกับ realApi ใน client.ts) ----------
export const demoApi = {
  health: async (): Promise<Health> => {
    await delay(50);
    return { status: 'ok', model_version: MODEL_VERSION, using_mock_model: true };
  },

  register: async (body: { email: string; password: string; display_name?: string | null }): Promise<TokenResponse> => {
    await delay();
    const store = load();
    const email = body.email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) throw new ApiError(422, 'value is not a valid email address');
    if (body.password.length < 8 || body.password.length > 128) {
      throw new ApiError(422, 'String should have at least 8 characters');
    }
    if (store.users.some((u) => u.email === email)) throw new ApiError(409, 'Email already in use');
    const user: DemoUser = {
      id: uuid(),
      email,
      password_hash: await hashPassword(body.password),
      display_name: body.display_name ?? null,
      created_at: now(),
      last_login_at: null,
      is_active: true,
    };
    save({ ...store, users: [...store.users, user] });
    return makeToken(user.id, 'user');
  },

  login: async (body: { email: string; password: string }): Promise<TokenResponse> => {
    await delay();
    const store = load();
    const user = store.users.find((u) => u.email === body.email.trim().toLowerCase());
    if (!user || user.password_hash !== (await hashPassword(body.password))) {
      throw new ApiError(401, 'Invalid email or password');
    }
    if (!user.is_active) throw new ApiError(403, 'Account suspended');
    user.last_login_at = now();
    save(store);
    return makeToken(user.id, 'user');
  },

  adminLogin: async (body: { username: string; password: string }): Promise<TokenResponse> => {
    await delay();
    if (body.username !== DEMO_ADMIN.username || body.password !== DEMO_ADMIN.password) {
      throw new ApiError(401, 'Invalid username or password');
    }
    return makeToken(load().admin_id, 'admin');
  },

  predict: async (files: File[]): Promise<BatchDetectionResult> => {
    await delay(400);
    const store = load();
    const threshold = currentThreshold(store);
    const user = optionalUser(store);
    const results: DetectionResult[] = [];
    const failed_files: FailedFile[] = [];

    for (const file of files) {
      const invalid = validateFormat(file);
      if (invalid) {
        failed_files.push(invalid);
        continue;
      }
      let report: Awaited<ReturnType<typeof analyze>>;
      try {
        report = await analyze(file, threshold);
      } catch (e) {
        const { reason, message } = e as { reason: string; message: string };
        failed_files.push({ filename: file.name, reason, message });
        continue;
      }
      const id = uuid();
      // backend บันทึกทุกผล (guest = user_id null) แต่ guest ไม่เห็นในประวัติ
      store.records.unshift({
        ...report,
        id,
        created_at: now(),
        user_id: user?.id ?? null,
        file_size_bytes: file.size,
        audio_format: file.name.slice(file.name.lastIndexOf('.') + 1).toLowerCase(),
      });
      results.push({ ...report, id, saved_to_history: user !== null });
    }
    save(store);
    return { results, failed_files };
  },

  listHistory: async (limit = 200): Promise<DetectionRecord[]> => {
    await delay(150);
    const store = load();
    const user = requireUser(store);
    return store.records.filter((r) => r.user_id === user.id).slice(0, limit).map(toRecordOut);
  },

  getHistory: async (id: string): Promise<DetectionDetail> => {
    await delay(150);
    const store = load();
    const r = ownedRecord(store, id, requireUser(store).id);
    return { ...toRecordOut(r), threshold_used: r.threshold_used, model_version: r.model_version, processing_ms: r.processing_ms, segments: r.segments };
  },

  deleteHistory: async (id: string): Promise<void> => {
    await delay();
    const store = load();
    const record = ownedRecord(store, id, requireUser(store).id);
    save({
      ...store,
      records: store.records.filter((r) => r !== record),
      feedback: store.feedback.filter((f) => f.detection_id !== id),
    });
  },

  getFeedback: async (id: string): Promise<Feedback> => {
    await delay(100);
    const store = load();
    ownedRecord(store, id, requireUser(store).id);
    const fb = store.feedback.find((f) => f.detection_id === id);
    if (!fb) throw new ApiError(404, 'No feedback submitted for this record');
    return toFeedbackOut(fb);
  },

  submitFeedback: async (id: string, userAgrees: boolean): Promise<Feedback> => {
    await delay();
    const store = load();
    const user = requireUser(store);
    ownedRecord(store, id, user.id);
    if (store.feedback.some((f) => f.detection_id === id)) {
      throw new ApiError(409, 'Feedback already submitted for this record');
    }
    const fb: DemoFeedback = {
      id: uuid(),
      detection_id: id,
      user_id: user.id,
      user_agrees: userAgrees,
      created_at: now(),
      updated_at: null,
    };
    save({ ...store, feedback: [fb, ...store.feedback] });
    return toFeedbackOut(fb);
  },

  updateFeedback: async (id: string, userAgrees: boolean): Promise<Feedback> => {
    await delay();
    const store = load();
    ownedRecord(store, id, requireUser(store).id);
    const fb = store.feedback.find((f) => f.detection_id === id);
    if (!fb) throw new ApiError(404, 'No feedback submitted for this record yet. submit it with POST first');
    fb.user_agrees = userAgrees;
    fb.updated_at = now();
    save(store);
    return toFeedbackOut(fb);
  },

  listMyFeedback: async (limit = 50, offset = 0): Promise<FeedbackHistoryItem[]> => {
    await delay(150);
    const store = load();
    const user = requireUser(store);
    return store.feedback
      .filter((f) => f.user_id === user.id)
      .slice(offset, offset + limit)
      .flatMap((f) => {
        const record = store.records.find((r) => r.id === f.detection_id);
        return record
          ? [{ ...toFeedbackOut(f), original_filename: record.original_filename, verdict: record.verdict }]
          : [];
      });
  },

  getMe: async (): Promise<UserProfile> => {
    await delay(100);
    return toProfile(requireUser(load()));
  },

  updateMe: async (body: { display_name: string | null }): Promise<UserProfile> => {
    await delay();
    const store = load();
    const user = requireUser(store);
    if (body.display_name !== null && (body.display_name.length < 1 || body.display_name.length > 100)) {
      throw new ApiError(422, 'String should have at most 100 characters');
    }
    user.display_name = body.display_name;
    save(store);
    return toProfile(user);
  },

  changePassword: async (body: { current_password: string; new_password: string }): Promise<void> => {
    await delay();
    const store = load();
    const user = requireUser(store);
    if (body.new_password.length < 8 || body.new_password.length > 128) {
      throw new ApiError(422, 'String should have at least 8 characters');
    }
    if (body.new_password === body.current_password) {
      throw new ApiError(422, 'New password must be different from the current password');
    }
    if (user.password_hash !== (await hashPassword(body.current_password))) {
      throw new ApiError(400, 'Current password is incorrect');
    }
    user.password_hash = await hashPassword(body.new_password);
    save(store);
  },

  listDetections: async (f: AdminDetectionFilters): Promise<AdminDetectionList> => {
    await delay(150);
    const store = load();
    requireAdmin(store);
    if (f.min_prob !== undefined && f.max_prob !== undefined && f.min_prob > f.max_prob) {
      throw new ApiError(422, 'min_prob must not be greater than max_prob');
    }
    if (f.date_from && f.date_to && f.date_from > f.date_to) {
      throw new ApiError(422, 'date_from must not be after date_to');
    }
    const thaiDay = (iso: string) => new Date(new Date(iso).getTime() + 7 * 3600 * 1000).toISOString().slice(0, 10);
    const items = store.records
      .map((r) => toDetectionItem(store, r))
      .filter((d) => !f.verdict || d.verdict === f.verdict)
      .filter((d) => !f.date_from || thaiDay(d.created_at) >= f.date_from)
      .filter((d) => !f.date_to || thaiDay(d.created_at) <= f.date_to)
      .filter((d) => !f.q || d.original_filename.toLowerCase().includes(f.q.toLowerCase()))
      .filter((d) => !f.user_id || d.user_id === f.user_id)
      .filter((d) => !f.user_email || (d.user_email ?? '').includes(f.user_email.toLowerCase()))
      .filter((d) => f.guest === undefined || (d.user_id === null) === f.guest)
      .filter((d) => !f.model_version || d.model_version === f.model_version)
      .filter((d) => f.partial_spoof === undefined || d.possible_partial_spoof === f.partial_spoof)
      .filter((d) => !f.feedback || (f.feedback === 'none' ? d.feedback === null : d.feedback === f.feedback))
      .filter((d) => f.min_prob === undefined || d.mean_probability >= f.min_prob)
      .filter((d) => f.max_prob === undefined || d.mean_probability <= f.max_prob);
    const key = f.sort ?? 'created_at';
    const dir = f.order === 'asc' ? 1 : -1;
    items.sort((a, b) => (a[key] < b[key] ? -dir : a[key] > b[key] ? dir : 0));
    return { items: items.slice(f.offset, f.offset + f.limit), total: items.length, limit: f.limit, offset: f.offset };
  },

  getDetection: async (id: string): Promise<AdminDetectionDetail> => {
    await delay(150);
    const store = load();
    requireAdmin(store);
    const r = store.records.find((x) => x.id === id);
    if (!r) throw new ApiError(404, 'Detection not found');
    const fb = store.feedback.find((x) => x.detection_id === id);
    return {
      ...toDetectionItem(store, r),
      sample_rate: r.sample_rate ?? 16000,
      file_size_bytes: r.file_size_bytes ?? 0,
      audio_format: r.audio_format ?? 'wav',
      feedback_created_at: fb?.created_at ?? null,
      feedback_updated_at: fb?.updated_at ?? null,
      segments: r.segments,
    };
  },

  getThreshold: async (): Promise<Threshold | null> => {
    await delay(100);
    const store = load();
    requireAdmin(store);
    return store.thresholds[0] ?? null;
  },

  setThreshold: async (value: number, note?: string): Promise<ThresholdUpdateResponse> => {
    await delay();
    const store = load();
    requireAdmin(store);
    if (!(value >= 0 && value <= 1)) throw new ApiError(422, 'Input should be between 0 and 1');
    const previous = store.thresholds[0] ?? null;
    const current: Threshold = {
      id: uuid(),
      value,
      effective_from: now(),
      changed_by_admin_id: store.admin_id,
      note: note || null,
    };
    save({ ...store, thresholds: [current, ...store.thresholds] });
    return { previous_value: previous ? previous.value : null, current };
  },

  getStats: async (): Promise<StatsOverview> => {
    await delay(150);
    const store = load();
    requireAdmin(store);
    const spoof = store.records.filter((r) => r.verdict === 'spoof').length;
    const agrees = store.feedback.filter((f) => f.user_agrees).length;
    return {
      total_detections: store.records.length,
      total_spoof_verdicts: spoof,
      total_real_verdicts: store.records.length - spoof,
      total_users: store.users.length,
      feedback_agreement_rate: store.feedback.length ? agrees / store.feedback.length : null,
    };
  },

  listUsers: async (params: {
    q?: string;
    is_active?: boolean | null;
    limit: number;
    offset: number;
  }): Promise<AdminUserList> => {
    await delay(150);
    const store = load();
    requireAdmin(store);
    const q = params.q?.toLowerCase();
    const matched = store.users
      .filter((u) => !q || u.email.includes(q) || (u.display_name ?? '').toLowerCase().includes(q))
      .filter((u) => params.is_active === null || params.is_active === undefined || u.is_active === params.is_active)
      .sort((a, b) => b.created_at.localeCompare(a.created_at));
    return {
      items: matched.slice(params.offset, params.offset + params.limit).map((u) => toAdminUser(store, u)),
      total: matched.length,
      limit: params.limit,
      offset: params.offset,
    };
  },

  updateUser: async (id: string, body: { display_name?: string | null; is_active?: boolean }): Promise<AdminUser> => {
    await delay();
    const store = load();
    requireAdmin(store);
    const user = store.users.find((u) => u.id === id);
    if (!user) throw new ApiError(404, 'User not found');
    if ('display_name' in body) user.display_name = body.display_name ?? null;
    if (body.is_active !== undefined) user.is_active = body.is_active;
    save(store);
    return toAdminUser(store, user);
  },
};

function toAdminUser(store: DemoStore, u: DemoUser): AdminUser {
  return {
    id: u.id,
    email: u.email,
    display_name: u.display_name,
    created_at: u.created_at,
    last_login_at: u.last_login_at,
    is_active: u.is_active,
    detection_count: store.records.filter((r) => r.user_id === u.id).length,
  };
}

function toProfile(u: DemoUser): UserProfile {
  return { id: u.id, email: u.email, display_name: u.display_name, created_at: u.created_at };
}

function toDetectionItem(store: DemoStore, r: DemoRecord): AdminDetectionItem {
  const fb = store.feedback.find((f) => f.detection_id === r.id);
  return {
    id: r.id,
    created_at: r.created_at,
    original_filename: r.original_filename,
    duration_seconds: r.duration_seconds,
    num_segments: r.segments.length,
    mean_probability: r.mean_probability,
    max_probability: r.max_probability,
    threshold_used: r.threshold_used,
    verdict: r.verdict,
    possible_partial_spoof: r.possible_partial_spoof,
    model_version: r.model_version,
    processing_ms: r.processing_ms,
    user_id: r.user_id,
    user_email: store.users.find((u) => u.id === r.user_id)?.email ?? null,
    feedback: fb ? (fb.user_agrees ? 'agree' : 'disagree') : null,
  };
}
