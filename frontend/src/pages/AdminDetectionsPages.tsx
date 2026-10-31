import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link, NavLink, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import type { AdminDetectionDetail, AdminDetectionFilters, AdminDetectionList, FeedbackFilter, Verdict } from '../api/types';
import { Icon } from '../components/Icon';
import { ResultView, VerdictBadge } from '../components/ResultView';
import { dateTime, fileSize, pct, seconds } from '../lib/format';

const PAGE_SIZE = 20;

/** แท็บย่อยของหน้าผู้ดูแล */
export function AdminTabs() {
  return (
    <nav className="seg-tabs" aria-label="เมนูผู้ดูแล">
      <NavLink to="/admin" end>
        <Icon name="chart" size={16} /> ภาพรวม
      </NavLink>
      <NavLink to="/admin/detections">
        <Icon name="wave" size={16} /> ผลตรวจทั้งหมด
      </NavLink>
    </nav>
  );
}

const SORTS: { value: string; label: string }[] = [
  { value: 'created_at:desc', label: 'ใหม่สุดก่อน' },
  { value: 'created_at:asc', label: 'เก่าสุดก่อน' },
  { value: 'mean_probability:desc', label: 'คะแนน AI สูงสุด' },
  { value: 'mean_probability:asc', label: 'คะแนน AI ต่ำสุด' },
  { value: 'processing_ms:desc', label: 'ประมวลผลนานสุด' },
];

// ตัวกรองทั้งหมดเก็บใน URL (?verdict=spoof&page=2) → กดย้อนกลับ/แชร์ลิงก์แล้วได้ผลเดิม
function filtersFromParams(p: URLSearchParams): AdminDetectionFilters {
  const page = Math.max(1, Number(p.get('page')) || 1);
  const [sort, order] = (p.get('sort') ?? 'created_at:desc').split(':') as [AdminDetectionFilters['sort'], 'asc' | 'desc'];
  const bool = (key: string) => (p.get(key) === 'true' ? true : p.get(key) === 'false' ? false : undefined);
  const prob = (key: string) => (p.get(key) ? Number(p.get(key)) / 100 : undefined);
  return {
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
    sort,
    order,
    verdict: (p.get('verdict') as Verdict) || undefined,
    feedback: (p.get('feedback') as FeedbackFilter) || undefined,
    guest: bool('guest'),
    partial_spoof: bool('partial'),
    q: p.get('q') || undefined,
    user_email: p.get('email') || undefined,
    user_id: p.get('user_id') || undefined,
    date_from: p.get('from') || undefined,
    date_to: p.get('to') || undefined,
    min_prob: prob('min'),
    max_prob: prob('max'),
  };
}

export function AdminDetectionsPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const filters = useMemo(() => filtersFromParams(params), [params]);
  const [data, setData] = useState<AdminDetectionList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // ช่องพิมพ์ใช้ค่าร่างก่อน แล้วค่อยใส่ URL ตอนกดค้นหา (ไม่ยิง API ทุกตัวอักษร)
  const [draft, setDraft] = useState({ q: '', email: '', from: '', to: '', min: '', max: '' });
  useEffect(() => {
    setDraft({
      q: params.get('q') ?? '',
      email: params.get('email') ?? '',
      from: params.get('from') ?? '',
      to: params.get('to') ?? '',
      min: params.get('min') ?? '',
      max: params.get('max') ?? '',
    });
  }, [params]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .listDetections(filters)
      .then(setData)
      .catch((e) => {
        setData(null);
        setError(filterErrorText(e));
      })
      .finally(() => setLoading(false));
  }, [filters]);

  const update = (changes: Record<string, string | null>, keepPage = false) => {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value === null || value === '') next.delete(key);
      else next.set(key, value);
    }
    if (!keepPage) next.delete('page');
    setParams(next);
  };

  const applyDraft = (e: FormEvent) => {
    e.preventDefault();
    update(draft);
  };

  const userLabel = params.get('user_label');
  const page = Math.floor(filters.offset / PAGE_SIZE) + 1;
  const total = data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const hasFilters = [...params.keys()].some((k) => k !== 'page' && k !== 'sort');

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>ผลตรวจทั้งหมด</h1>
          <p className="muted">ทุกครั้งที่มีการตรวจเสียง ทั้งผู้ใช้ที่ login และไม่ได้ login</p>
        </div>
      </div>
      <AdminTabs />

      <form className="card stack-sm" onSubmit={applyDraft}>
        <div className="filter-grid">
          <label className="field">
            <span>ชื่อไฟล์</span>
            <input value={draft.q} maxLength={100} placeholder="ค้นหาชื่อไฟล์" onChange={(e) => setDraft({ ...draft, q: e.target.value })} />
          </label>
          <label className="field">
            <span>อีเมลผู้ตรวจ</span>
            <input value={draft.email} maxLength={255} placeholder="บางส่วนก็ได้" onChange={(e) => setDraft({ ...draft, email: e.target.value })} />
          </label>
          <label className="field">
            <span>ผลตรวจ</span>
            <select value={params.get('verdict') ?? ''} onChange={(e) => update({ verdict: e.target.value })}>
              <option value="">ทั้งหมด</option>
              <option value="spoof">🤖 เสียง AI</option>
              <option value="real">🙋 เสียงจริง</option>
            </select>
          </label>
          <label className="field">
            <span>Feedback</span>
            <select value={params.get('feedback') ?? ''} onChange={(e) => update({ feedback: e.target.value })}>
              <option value="">ทั้งหมด</option>
              <option value="agree">👍 ผู้ใช้เห็นด้วย</option>
              <option value="disagree">👎 ผู้ใช้ไม่เห็นด้วย</option>
              <option value="none">ยังไม่มี feedback</option>
            </select>
          </label>
          <label className="field">
            <span>ผู้ตรวจ</span>
            <select value={params.get('guest') ?? ''} onChange={(e) => update({ guest: e.target.value })}>
              <option value="">ทุกคน</option>
              <option value="false">ผู้ใช้ที่ login</option>
              <option value="true">ไม่ได้ login (guest)</option>
            </select>
          </label>
          <label className="field">
            <span>อาจตัดต่อ</span>
            <select value={params.get('partial') ?? ''} onChange={(e) => update({ partial: e.target.value })}>
              <option value="">ทั้งหมด</option>
              <option value="true">เฉพาะที่อาจตัดต่อ</option>
              <option value="false">ไม่สงสัยว่าตัดต่อ</option>
            </select>
          </label>
          <label className="field">
            <span>ตั้งแต่วันที่</span>
            <input type="date" value={draft.from} onChange={(e) => setDraft({ ...draft, from: e.target.value })} />
          </label>
          <label className="field">
            <span>ถึงวันที่</span>
            <input type="date" value={draft.to} onChange={(e) => setDraft({ ...draft, to: e.target.value })} />
          </label>
          <label className="field">
            <span>คะแนน AI ขั้นต่ำ (%)</span>
            <input type="number" min={0} max={100} value={draft.min} onChange={(e) => setDraft({ ...draft, min: e.target.value })} />
          </label>
          <label className="field">
            <span>คะแนน AI สูงสุด (%)</span>
            <input type="number" min={0} max={100} value={draft.max} onChange={(e) => setDraft({ ...draft, max: e.target.value })} />
          </label>
        </div>
        <div className="row between wrap">
          <div className="row wrap">
            <button className="btn btn-primary btn-small">
              <Icon name="sparkle" size={14} /> ค้นหา
            </button>
            {hasFilters && (
              <button type="button" className="btn btn-ghost btn-small" onClick={() => setParams(new URLSearchParams())}>
                ล้างตัวกรอง
              </button>
            )}
          </div>
          <label className="row small">
            <span className="muted">เรียง</span>
            <select value={params.get('sort') ?? 'created_at:desc'} onChange={(e) => update({ sort: e.target.value })}>
              {SORTS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        {params.get('user_id') && (
          <div>
            <span className="filter-chip">
              เฉพาะผู้ใช้: {userLabel ?? params.get('user_id')}
              <button type="button" aria-label="เอาตัวกรองผู้ใช้ออก" onClick={() => update({ user_id: null, user_label: null })}>
                <Icon name="close" size={14} />
              </button>
            </span>
          </div>
        )}
      </form>

      {error && <div className="callout callout-danger">{error}</div>}

      {!error && (
        <section className="card stack-sm">
          <div className="row between">
            <h3>{data ? `พบ ${total.toLocaleString('th-TH')} รายการ` : 'กำลังโหลด…'}</h3>
            {loading && data && <span className="spinner muted" aria-label="กำลังโหลด" />}
          </div>
          {data && data.items.length === 0 ? (
            <div className="empty">
              <span className="empty-emoji">🔍</span>
              ไม่พบผลตรวจที่ตรงกับตัวกรอง
            </div>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>เวลา</th>
                    <th>ไฟล์</th>
                    <th>ผู้ตรวจ</th>
                    <th>ผล</th>
                    <th className="num">คะแนน AI</th>
                    <th>Feedback</th>
                    <th className="num">ใช้เวลา</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.items.map((d) => (
                    <tr
                      key={d.id}
                      className="clickable"
                      onClick={() => navigate(`/admin/detections/${d.id}`, { state: { from: location.search } })}
                    >
                      <td>{dateTime(d.created_at)}</td>
                      <td className="cell-file" title={d.original_filename}>
                        {d.original_filename}
                      </td>
                      <td>{d.user_email ?? <span className="muted">ไม่ได้ login</span>}</td>
                      <td>
                        <VerdictBadge verdict={d.verdict} />
                        {d.possible_partial_spoof && <span className="tag">อาจตัดต่อ</span>}
                      </td>
                      <td className="num">{pct(d.mean_probability)}</td>
                      <td>{d.feedback === 'agree' ? '👍' : d.feedback === 'disagree' ? '👎' : <span className="muted">–</span>}</td>
                      <td className="num">{d.processing_ms} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="row between">
            <span className="muted small">
              หน้า {page} / {pages}
            </span>
            <div className="row">
              <button
                className="btn btn-soft btn-small"
                disabled={page <= 1}
                onClick={() => update({ page: String(page - 1) }, true)}
              >
                ก่อนหน้า
              </button>
              <button
                className="btn btn-soft btn-small"
                disabled={page >= pages}
                onClick={() => update({ page: String(page + 1) }, true)}
              >
                ถัดไป
              </button>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

function filterErrorText(e: unknown): string {
  if (!(e instanceof ApiError)) return 'โหลดผลตรวจไม่สำเร็จ';
  if (e.message.includes('min_prob')) return 'คะแนน AI ขั้นต่ำต้องไม่มากกว่าคะแนนสูงสุด';
  if (e.message.includes('date_from')) return 'วันที่เริ่มต้องไม่อยู่หลังวันที่สิ้นสุด';
  if (e.status === 422) return `ตัวกรองไม่ถูกต้อง: ${e.message}`;
  return e.message;
}

export function AdminDetectionDetailPage() {
  const { id = '' } = useParams();
  const location = useLocation();
  const backSearch = (location.state as { from?: string } | null)?.from ?? '';
  const [detail, setDetail] = useState<AdminDetectionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getDetection(id)
      .then(setDetail)
      .catch((e) => setError(e instanceof ApiError && e.status === 404 ? 'ไม่พบผลตรวจนี้' : 'โหลดรายละเอียดไม่สำเร็จ'));
  }, [id]);

  const back = (
    <Link to={`/admin/detections${backSearch}`} className="btn btn-ghost btn-small">
      <Icon name="back" size={16} /> ผลตรวจทั้งหมด
    </Link>
  );

  if (error) {
    return (
      <div className="stack">
        {back}
        <div className="callout callout-danger">{error}</div>
      </div>
    );
  }
  if (!detail) return <p className="muted">กำลังโหลด…</p>;

  const userFilter = detail.user_id
    ? `/admin/detections?user_id=${detail.user_id}&user_label=${encodeURIComponent(detail.user_email ?? '')}`
    : '/admin/detections?guest=true';

  return (
    <div className="stack">
      <div className="row between">
        {back}
        <span className="muted small">ตรวจเมื่อ {dateTime(detail.created_at)}</span>
      </div>

      <ResultView
        filename={detail.original_filename}
        verdict={detail.verdict}
        meanProbability={detail.mean_probability}
        maxProbability={detail.max_probability}
        threshold={detail.threshold_used}
        possiblePartialSpoof={detail.possible_partial_spoof}
        durationSeconds={detail.duration_seconds}
        modelVersion={detail.model_version}
        processingMs={detail.processing_ms}
        segments={detail.segments}
      />

      <section className="card stack-sm">
        <h3>ข้อมูลสำหรับผู้ดูแล</h3>
        <dl className="meta-grid">
          <div>
            <dt>ผู้ตรวจ</dt>
            <dd>
              <Link to={userFilter}>{detail.user_email ?? 'ไม่ได้ login (guest)'}</Link>
            </dd>
          </div>
          <div>
            <dt>Feedback จากผู้ใช้</dt>
            <dd>
              {detail.feedback === 'agree' ? (
                '👍 เห็นด้วยกับผล'
              ) : detail.feedback === 'disagree' ? (
                '👎 ไม่เห็นด้วยกับผล'
              ) : (
                <span className="muted">ยังไม่มี</span>
              )}
              {detail.feedback_created_at && (
                <small className="muted">
                  {' '}
                  · {dateTime(detail.feedback_updated_at ?? detail.feedback_created_at)}
                  {detail.feedback_updated_at ? ' (แก้ไข)' : ''}
                </small>
              )}
            </dd>
          </div>
          <div>
            <dt>ไฟล์</dt>
            <dd>
              .{detail.audio_format} · {fileSize(detail.file_size_bytes)}
            </dd>
          </div>
          <div>
            <dt>เสียงที่วิเคราะห์</dt>
            <dd>
              {seconds(detail.duration_seconds)} · {detail.num_segments} ช่วง · {detail.sample_rate.toLocaleString('th-TH')} Hz
            </dd>
          </div>
          <div>
            <dt>รหัสผลตรวจ</dt>
            <dd className="mono">{detail.id}</dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
