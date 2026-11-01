import { useEffect, useMemo, useState } from 'react';
import { Link, NavLink, useNavigate, useParams } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import type { DetectionDetail, DetectionRecord, Feedback, FeedbackHistoryItem } from '../api/types';
import { ChipGroup, FilterSummary, inPeriod, SearchBox, useUrlFilters } from '../components/Filters';
import { Icon } from '../components/Icon';
import { ResultView, VerdictBadge } from '../components/ResultView';
import { SkeletonCard, SkeletonList } from '../components/Skeleton';
import { useUi } from '../components/UiProvider';
import { dateTime, pct, seconds, verdictEmoji } from '../lib/format';

// backend /history และ /feedback รับแค่ limit (สูงสุด 200) ไม่มีตัวกรอง จึงกรองในหน้าเว็บจาก 200 รายการล่าสุด
const FETCH_LIMIT = 200;

const VERDICT_OPTIONS = [
  { value: 'spoof', label: '🤖 เสียง AI' },
  { value: 'real', label: '🙋 เสียงจริง' },
];
const HISTORY_SORTS: Record<string, { label: string; compare: (a: DetectionRecord, b: DetectionRecord) => number }> = {
  '': { label: 'ใหม่สุดก่อน', compare: (a, b) => b.created_at.localeCompare(a.created_at) },
  old: { label: 'เก่าสุดก่อน', compare: (a, b) => a.created_at.localeCompare(b.created_at) },
  high: { label: 'คะแนน AI สูงสุด', compare: (a, b) => b.mean_probability - a.mean_probability },
  low: { label: 'คะแนน AI ต่ำสุด', compare: (a, b) => a.mean_probability - b.mean_probability },
};
const HISTORY_KEYS = ['q', 'verdict', 'vote', 'period', 'partial', 'sort'] as const;

/** สลับระหว่างประวัติทั้งหมด กับผลที่เคยโหวต (แทนเมนู Feedback แยก ทำให้เมนูล่างเหลือ 4 ปุ่ม) */
function HistoryTabs() {
  return (
    <nav className="seg-tabs" aria-label="มุมมองประวัติ">
      <NavLink to="/history">
        <Icon name="clock" size={16} /> ประวัติทั้งหมด
      </NavLink>
      <NavLink to="/feedback">
        <Icon name="heart" size={16} /> ผลที่ฉันโหวต
      </NavLink>
    </nav>
  );
}

export function HistoryPage() {
  const [items, setItems] = useState<DetectionRecord[] | null>(null);
  const [votes, setVotes] = useState<Map<string, boolean>>(new Map());
  const [error, setError] = useState<string | null>(null);
  const { values: f, set, reset, active } = useUrlFilters(HISTORY_KEYS);

  useEffect(() => {
    api
      .listHistory(FETCH_LIMIT)
      .then(setItems)
      .catch((e) => setError(e instanceof ApiError ? e.message : 'โหลดประวัติไม่สำเร็จ'));
    // ดึงคำตอบ 👍/👎 มาด้วย เพื่อกรอง "ยังไม่ได้โหวต" (ถ้าโหลดไม่ได้ ก็แค่กรองตามคำตอบไม่ได้)
    api
      .listMyFeedback(FETCH_LIMIT)
      .then((list) => setVotes(new Map(list.map((fb) => [fb.detection_id, fb.user_agrees]))))
      .catch(() => setVotes(new Map()));
  }, []);

  const shown = useMemo(() => {
    if (!items) return [];
    const q = f.q.trim().toLowerCase();
    return items
      .filter((r) => !q || r.original_filename.toLowerCase().includes(q))
      .filter((r) => !f.verdict || r.verdict === f.verdict)
      .filter((r) => !f.partial || r.possible_partial_spoof)
      .filter((r) => inPeriod(r.created_at, f.period))
      .filter((r) => {
        if (!f.vote) return true;
        const vote = votes.get(r.id);
        if (f.vote === 'none') return vote === undefined;
        return vote === (f.vote === 'agree');
      })
      .sort((HISTORY_SORTS[f.sort] ?? HISTORY_SORTS['']).compare);
  }, [items, votes, f.q, f.verdict, f.partial, f.period, f.vote, f.sort]);

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>ประวัติการตรวจ</h1>
          <p className="muted">เสียงที่คุณเคยเช็กไว้ตอน login</p>
        </div>
        <Link to="/" className="btn btn-primary btn-small">
          <Icon name="sparkle" size={16} /> เช็กเสียงใหม่
        </Link>
      </div>
      <HistoryTabs />

      {error && <div className="callout callout-danger">{error}</div>}
      {!items && !error && <SkeletonList />}
      {items && items.length === 0 && (
        <div className="card empty">
          <span className="empty-emoji">🎧</span>
          ยังไม่มีประวัติเลย <Link to="/">ลองเช็กเสียงแรกกัน</Link>
        </div>
      )}
      {items && items.length > 0 && (
        <>
          <section className="card filter-panel">
            <div className="row wrap">
              <SearchBox value={f.q} onChange={(v) => set('q', v)} placeholder="ค้นหาชื่อไฟล์" />
              <label className="row small sort-select">
                <span className="muted">เรียง</span>
                <select value={f.sort} onChange={(e) => set('sort', e.target.value)}>
                  {Object.entries(HISTORY_SORTS).map(([value, option]) => (
                    <option key={value} value={value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <ChipGroup label="ผลตรวจ" options={VERDICT_OPTIONS} value={f.verdict} onChange={(v) => set('verdict', v)} />
            <ChipGroup
              label="คำตอบของฉัน"
              options={[
                { value: 'agree', label: '👍 ถูกต้อง' },
                { value: 'disagree', label: '👎 ไม่ถูกต้อง' },
                { value: 'none', label: 'ยังไม่ได้โหวต' },
              ]}
              value={f.vote}
              onChange={(v) => set('vote', v)}
            />
            <ChipGroup
              label="ช่วงเวลา"
              options={[
                { value: '7', label: '7 วันล่าสุด' },
                { value: '30', label: '30 วันล่าสุด' },
              ]}
              value={f.period}
              onChange={(v) => set('period', v)}
            />
            <ChipGroup
              label="อื่นๆ"
              options={[{ value: '1', label: 'เฉพาะที่อาจตัดต่อ' }]}
              value={f.partial}
              onChange={(v) => set('partial', v)}
            />
          </section>

          <FilterSummary
            shown={shown.length}
            total={items.length}
            active={active}
            onReset={reset}
            note={items.length >= FETCH_LIMIT ? `ค้นใน ${FETCH_LIMIT} รายการล่าสุด` : undefined}
          />

          {shown.length === 0 ? (
            <div className="card empty">
              <span className="empty-emoji">🔍</span>
              ไม่พบรายการที่ตรงกับตัวกรอง
            </div>
          ) : (
            <div className="list">
              {shown.map((r) => {
                const vote = votes.get(r.id);
                return (
                  <Link key={r.id} to={`/history/${r.id}`} className="list-item">
                    <span className={`list-emoji is-${r.verdict}`}>{verdictEmoji(r.verdict)}</span>
                    <span className="list-main">
                      <span className="file-name">{r.original_filename}</span>
                      <span className="list-meta">
                        <VerdictBadge verdict={r.verdict} />
                        {r.possible_partial_spoof && <span className="tag">อาจตัดต่อ</span>}
                        {vote !== undefined && <span title="คำตอบของฉัน">{vote ? '👍 ถูกต้อง' : '👎 ไม่ถูกต้อง'}</span>}
                        <span>{dateTime(r.created_at)}</span>
                        <span>· {seconds(r.duration_seconds)}</span>
                      </span>
                    </span>
                    <span className="list-side">
                      {pct(r.mean_probability, 0)}
                      <small>คะแนนน่าสงสัย</small>
                    </span>
                  </Link>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function HistoryDetailPage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const { confirm, toast } = useUi();
  const [record, setRecord] = useState<DetectionDetail | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .getHistory(id)
      .then(setRecord)
      .catch((e) =>
        setError(e instanceof ApiError && e.status === 404 ? 'ไม่พบรายการนี้' : 'โหลดรายละเอียดไม่สำเร็จ'),
      );
    // 404 = ยังไม่เคยให้ feedback (ไม่ใช่ error)
    api
      .getFeedback(id)
      .then(setFeedback)
      .catch(() => setFeedback(null));
  }, [id]);

  const giveFeedback = async (agrees: boolean) => {
    setSaving(true);
    try {
      const next = feedback ? await api.updateFeedback(id, agrees) : await api.submitFeedback(id, agrees);
      setFeedback(next);
      toast(agrees ? 'บันทึกแล้ว: ผลนี้ถูกต้อง 👍' : 'บันทึกแล้ว: ผลนี้ไม่ถูกต้อง 👎');
    } catch (e) {
      // 409 = เคยส่งไปแล้ว (เช่นจากอีกแท็บ) → แก้คำตอบแทน
      if (e instanceof ApiError && e.status === 409) {
        try {
          setFeedback(await api.updateFeedback(id, agrees));
          toast('บันทึกคำตอบแล้ว');
        } catch (err) {
          toast(err instanceof ApiError ? err.message : 'บันทึก feedback ไม่สำเร็จ', 'error');
        }
      } else {
        toast(e instanceof ApiError ? e.message : 'บันทึก feedback ไม่สำเร็จ', 'error');
      }
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    const ok = await confirm({
      title: 'ลบรายการนี้?',
      message: `ผลตรวจ ${record?.original_filename ?? ''} และคำตอบ 👍/👎 ของรายการนี้จะถูกลบถาวร กู้คืนไม่ได้`,
      confirmLabel: 'ลบรายการ',
      danger: true,
    });
    if (!ok) return;
    try {
      await api.deleteHistory(id);
      toast('ลบรายการแล้ว');
      navigate('/history', { replace: true });
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'ลบไม่สำเร็จ', 'error');
    }
  };

  if (error) {
    return (
      <div className="stack">
        <div className="callout callout-danger">{error}</div>
        <Link to="/history">← กลับไปหน้าประวัติ</Link>
      </div>
    );
  }
  if (!record) return <SkeletonCard lines={5} />;

  return (
    <div className="stack">
      <div className="row between">
        <Link to="/history" className="btn btn-ghost btn-small">
          <Icon name="back" size={16} /> ประวัติ
        </Link>
        <span className="muted small">เช็กเมื่อ {dateTime(record.created_at)}</span>
      </div>

      <ResultView
        checkedAt={record.created_at}
        filename={record.original_filename}
        verdict={record.verdict}
        meanProbability={record.mean_probability}
        maxProbability={record.max_probability}
        threshold={record.threshold_used}
        possiblePartialSpoof={record.possible_partial_spoof}
        durationSeconds={record.duration_seconds}
        modelVersion={record.model_version}
        processingMs={record.processing_ms}
        segments={record.segments}
      />

      <section className="card stack-sm">
        <h3>ผลนี้ถูกไหม?</h3>
        <p className="muted small" style={{ margin: 0 }}>
          คำตอบของคุณช่วยให้ทีมปรับโมเดลให้แม่นขึ้น เปลี่ยนใจได้ตลอด
        </p>
        <div className="vote">
          <button
            className={`vote-btn is-yes ${feedback?.user_agrees === true ? 'is-active' : ''}`}
            disabled={saving}
            onClick={() => giveFeedback(true)}
            aria-pressed={feedback?.user_agrees === true}
          >
            <span>👍</span>
            <span>ถูกต้อง</span>
          </button>
          <button
            className={`vote-btn is-no ${feedback?.user_agrees === false ? 'is-active' : ''}`}
            disabled={saving}
            onClick={() => giveFeedback(false)}
            aria-pressed={feedback?.user_agrees === false}
          >
            <span>👎</span>
            <span>ไม่ถูกต้อง</span>
          </button>
        </div>
        {feedback && (
          <span className="muted small">
            <Icon name="check" size={14} /> บันทึกแล้ว {dateTime(feedback.updated_at ?? feedback.created_at)}
          </span>
        )}
      </section>

      <div>
        <button className="btn btn-danger-soft btn-small" onClick={remove}>
          <Icon name="trash" size={16} /> ลบรายการนี้
        </button>
      </div>
    </div>
  );
}

const FEEDBACK_KEYS = ['q', 'answer', 'verdict', 'sort'] as const;

export function MyFeedbackPage() {
  const [items, setItems] = useState<FeedbackHistoryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { values: f, set, reset, active } = useUrlFilters(FEEDBACK_KEYS);

  useEffect(() => {
    api
      .listMyFeedback(FETCH_LIMIT)
      .then(setItems)
      .catch((e) => setError(e instanceof ApiError ? e.message : 'โหลด feedback ไม่สำเร็จ'));
  }, []);

  const shown = useMemo(() => {
    if (!items) return [];
    const q = f.q.trim().toLowerCase();
    const when = (x: FeedbackHistoryItem) => x.updated_at ?? x.created_at;
    return items
      .filter((x) => !q || x.original_filename.toLowerCase().includes(q))
      .filter((x) => !f.answer || x.user_agrees === (f.answer === 'agree'))
      .filter((x) => !f.verdict || x.verdict === f.verdict)
      .sort((a, b) => (f.sort === 'old' ? when(a).localeCompare(when(b)) : when(b).localeCompare(when(a))));
  }, [items, f.q, f.answer, f.verdict, f.sort]);

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>ผลที่ฉันโหวต</h1>
          <p className="muted">ผลที่คุณบอกเราว่าถูกหรือไม่ถูก</p>
        </div>
      </div>
      <HistoryTabs />
      {error && <div className="callout callout-danger">{error}</div>}
      {!items && !error && <SkeletonList />}
      {items && items.length === 0 && (
        <div className="card empty">
          <span className="empty-emoji">💬</span>
          ยังไม่เคยให้ feedback เลย ลองเปิดผลจาก<Link to="/history">ประวัติ</Link>แล้วกด 👍 หรือ 👎 ได้
        </div>
      )}
      {items && items.length > 0 && (
        <>
          <section className="card filter-panel">
            <div className="row wrap">
              <SearchBox value={f.q} onChange={(v) => set('q', v)} placeholder="ค้นหาชื่อไฟล์" />
              <label className="row small sort-select">
                <span className="muted">เรียง</span>
                <select value={f.sort} onChange={(e) => set('sort', e.target.value)}>
                  <option value="">ตอบล่าสุดก่อน</option>
                  <option value="old">ตอบเก่าสุดก่อน</option>
                </select>
              </label>
            </div>
            <ChipGroup
              label="คำตอบของฉัน"
              options={[
                { value: 'agree', label: '👍 ถูกต้อง' },
                { value: 'disagree', label: '👎 ไม่ถูกต้อง' },
              ]}
              value={f.answer}
              onChange={(v) => set('answer', v)}
            />
            <ChipGroup label="ระบบบอกว่า" options={VERDICT_OPTIONS} value={f.verdict} onChange={(v) => set('verdict', v)} />
          </section>

          <FilterSummary shown={shown.length} total={items.length} active={active} onReset={reset} />

          {shown.length === 0 ? (
            <div className="card empty">
              <span className="empty-emoji">🔍</span>
              ไม่พบรายการที่ตรงกับตัวกรอง
            </div>
          ) : (
            <div className="list">
              {shown.map((x) => (
                <Link key={x.id} to={`/history/${x.detection_id}`} className="list-item">
                  <span className={`list-emoji ${x.user_agrees ? 'is-real' : 'is-spoof'}`}>{x.user_agrees ? '👍' : '👎'}</span>
                  <span className="list-main">
                    <span className="file-name">{x.original_filename}</span>
                    <span className="list-meta">
                      ระบบบอกว่า <VerdictBadge verdict={x.verdict} />
                      <span>{dateTime(x.updated_at ?? x.created_at)}</span>
                    </span>
                  </span>
                  <span className="list-side">
                    {x.user_agrees ? 'ถูกต้อง' : 'ไม่ถูก'}
                    <small>คำตอบของฉัน</small>
                  </span>
                </Link>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
