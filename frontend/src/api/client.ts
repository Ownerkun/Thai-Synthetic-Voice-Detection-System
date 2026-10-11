import type {
  AdminUser,
  AdminUserList,
  BatchDetectionResult,
  DetectionDetail,
  DetectionRecord,
  Feedback,
  FeedbackHistoryItem,
  Health,
  StatsOverview,
  Threshold,
  ThresholdUpdateResponse,
  TokenResponse,
} from './types';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

let getToken: () => string | null = () => null;
let onUnauthorized: () => void = () => {};

/** AuthContext เรียกตอนเริ่มแอป เพื่อให้ client รู้ token ปัจจุบัน และ logout อัตโนมัติเมื่อ token ใช้ไม่ได้ */
export function configureApi(options: { getToken: () => string | null; onUnauthorized: () => void }) {
  getToken = options.getToken;
  onUnauthorized = options.onUnauthorized;
}

interface RequestOptions {
  method?: string;
  json?: unknown;
  form?: FormData;
  query?: Record<string, string | number | boolean | undefined | null>;
}

// 422 ของ FastAPI: detail เป็น array [{loc, msg, type}]; error อื่นเป็น string
function detailToMessage(detail: unknown, status: number): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (d && typeof d === 'object' && 'msg' in d ? String(d.msg) : String(d)))
      .join(', ');
  }
  return `เกิดข้อผิดพลาด (HTTP ${status})`;
}

async function request<T>(path: string, { method = 'GET', json, form, query }: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (json !== undefined) headers['Content-Type'] = 'application/json';

  let url = BASE_URL + path;
  if (query) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
    }
    const qs = params.toString();
    if (qs) url += `?${qs}`;
  }

  let res: Response;
  try {
    res = await fetch(url, {
      method,
      headers,
      body: form ?? (json !== undefined ? JSON.stringify(json) : undefined),
    });
  } catch {
    throw new ApiError(0, 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ ตรวจสอบว่า backend รันอยู่');
  }

  if (res.status === 204) return undefined as T;
  const data: unknown = await res.json().catch(() => null);

  if (!res.ok) {
    // token หมดอายุ / บัญชีถูกระงับ → ล้าง session (ยกเว้นตอนยังไม่ได้ login เช่นกรอกรหัสผิด)
    if (res.status === 401 && token) onUnauthorized();
    const detail = data && typeof data === 'object' && 'detail' in data ? data.detail : undefined;
    throw new ApiError(res.status, detailToMessage(detail, res.status));
  }
  return data as T;
}

export const api = {
  health: () => request<Health>('/health'),

  register: (body: { email: string; password: string; display_name?: string | null }) =>
    request<TokenResponse>('/auth/register', { method: 'POST', json: body }),
  login: (body: { email: string; password: string }) =>
    request<TokenResponse>('/auth/login', { method: 'POST', json: body }),
  adminLogin: (body: { username: string; password: string }) =>
    request<TokenResponse>('/auth/admin/login', { method: 'POST', json: body }),

  predict: (files: File[]) => {
    const form = new FormData();
    for (const file of files) form.append('files', file, file.name);
    return request<BatchDetectionResult>('/predict', { method: 'POST', form });
  },

  listHistory: (limit = 200) => request<DetectionRecord[]>('/history', { query: { limit } }),
  getHistory: (id: string) => request<DetectionDetail>(`/history/${id}`),
  deleteHistory: (id: string) => request<void>(`/history/${id}`, { method: 'DELETE' }),

  getFeedback: (id: string) => request<Feedback>(`/history/${id}/feedback`),
  submitFeedback: (id: string, userAgrees: boolean) =>
    request<Feedback>(`/history/${id}/feedback`, { method: 'POST', json: { user_agrees: userAgrees } }),
  updateFeedback: (id: string, userAgrees: boolean) =>
    request<Feedback>(`/history/${id}/feedback`, { method: 'PUT', json: { user_agrees: userAgrees } }),
  listMyFeedback: (limit = 50, offset = 0) =>
    request<FeedbackHistoryItem[]>('/feedback', { query: { limit, offset } }),

  getThreshold: () => request<Threshold | null>('/admin/threshold'),
  setThreshold: (value: number, note?: string) =>
    request<ThresholdUpdateResponse>('/admin/threshold', { method: 'POST', json: { value, note: note || null } }),
  getStats: () => request<StatsOverview>('/admin/stats'),
  listUsers: (params: { q?: string; is_active?: boolean | null; limit: number; offset: number }) =>
    request<AdminUserList>('/admin/users', { query: params }),
  updateUser: (id: string, body: { display_name?: string | null; is_active?: boolean }) =>
    request<AdminUser>(`/admin/users/${id}`, { method: 'PATCH', json: body }),
};
