import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import type { DetectionDetail, DetectionRecord, Feedback, FeedbackHistoryItem } from '../api/types';
import { Icon } from '../components/Icon';
import { ResultView, VerdictBadge } from '../components/ResultView';
import { dateTime, pct, seconds, verdictEmoji } from '../lib/format';

export function HistoryPage() {
  const [items, setItems] = useState<DetectionRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listHistory()
      .then(setItems)
      .catch((e) => setError(e instanceof ApiError ? e.message : 'โหลดประวัติไม่สำเร็จ'));
  }, []);

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>ประวัติการตรวจ</h1>
          <p className="muted">{items ? `ทั้งหมด ${items.length} รายการ` : 'เสียงที่คุณเคยเช็กไว้'}</p>
        </div>
        <Link to="/" className="btn btn-primary btn-small">
          <Icon name="sparkle" size={16} /> เช็กเสียงใหม่
        </Link>
      </div>

      {error && <div className="callout callout-danger">{error}</div>}
      {!items && !error && <p className="muted">กำลังโหลด…</p>}
      {items && items.length === 0 && (
        <div className="card empty">
          <span className="empty-emoji">🎧</span>
          ยังไม่มีประวัติเลย <Link to="/">ลองเช็กเสียงแรกกัน</Link>
        </div>
      )}
      {items && items.length > 0 && (
        <div className="list">
          {items.map((r) => (
            <Link key={r.id} to={`/history/${r.id}`} className="list-item">
              <span className={`list-emoji is-${r.verdict}`}>{verdictEmoji(r.verdict)}</span>
              <span className="list-main">
                <span className="file-name">{r.original_filename}</span>
                <span className="list-meta">
                  <VerdictBadge verdict={r.verdict} />
                  {r.possible_partial_spoof && <span className="tag">อาจตัดต่อ</span>}
                  <span>{dateTime(r.created_at)}</span>
                  <span>· {seconds(r.duration_seconds)}</span>
                </span>
              </span>
              <span className="list-side">
                {pct(r.mean_probability, 0)}
                <small>โอกาสเป็น AI</small>
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function HistoryDetailPage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
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
    } catch (e) {
      // 409 = เคยส่งไปแล้ว (เช่นจากอีกแท็บ) → แก้คำตอบแทน
      if (e instanceof ApiError && e.status === 409) {
        setFeedback(await api.updateFeedback(id, agrees).catch(() => null));
      } else {
        alert(e instanceof ApiError ? e.message : 'บันทึก feedback ไม่สำเร็จ');
      }
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!confirm('ลบรายการนี้ออกจากประวัติ? ลบแล้วกู้คืนไม่ได้นะ')) return;
    try {
      await api.deleteHistory(id);
      navigate('/history', { replace: true });
    } catch (e) {
      alert(e instanceof ApiError ? e.message : 'ลบไม่สำเร็จ');
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
  if (!record) return <p className="muted">กำลังโหลด…</p>;

  return (
    <div className="stack">
      <div className="row between">
        <Link to="/history" className="btn btn-ghost btn-small">
          <Icon name="back" size={16} /> ประวัติ
        </Link>
        <span className="muted small">เช็กเมื่อ {dateTime(record.created_at)}</span>
      </div>

      <ResultView
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

export function MyFeedbackPage() {
  const [items, setItems] = useState<FeedbackHistoryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listMyFeedback(200)
      .then(setItems)
      .catch((e) => setError(e instanceof ApiError ? e.message : 'โหลด feedback ไม่สำเร็จ'));
  }, []);

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Feedback ของฉัน</h1>
          <p className="muted">ผลที่คุณบอกเราว่าถูกหรือไม่ถูก</p>
        </div>
      </div>
      {error && <div className="callout callout-danger">{error}</div>}
      {!items && !error && <p className="muted">กำลังโหลด…</p>}
      {items && items.length === 0 && (
        <div className="card empty">
          <span className="empty-emoji">💬</span>
          ยังไม่เคยให้ feedback เลย ลองเปิดผลจาก<Link to="/history">ประวัติ</Link>แล้วกด 👍 หรือ 👎 ได้
        </div>
      )}
      {items && items.length > 0 && (
        <div className="list">
          {items.map((f) => (
            <Link key={f.id} to={`/history/${f.detection_id}`} className="list-item">
              <span className={`list-emoji ${f.user_agrees ? 'is-real' : 'is-spoof'}`}>{f.user_agrees ? '👍' : '👎'}</span>
              <span className="list-main">
                <span className="file-name">{f.original_filename}</span>
                <span className="list-meta">
                  ระบบบอกว่า <VerdictBadge verdict={f.verdict} />
                  <span>{dateTime(f.updated_at ?? f.created_at)}</span>
                </span>
              </span>
              <span className="list-side">
                {f.user_agrees ? 'ถูกต้อง' : 'ไม่ถูก'}
                <small>คำตอบของฉัน</small>
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
