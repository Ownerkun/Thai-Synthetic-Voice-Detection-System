import { useRef, useState, type DragEvent } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import type { BatchDetectionResult } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { Icon } from '../components/Icon';
import { Recorder } from '../components/Recorder';
import { ResultView, VerdictBadge } from '../components/ResultView';
import { dateTime, failureText, fileSize, pct, verdictEmoji } from '../lib/format';
import { addGuestResults, clearGuestResults, loadGuestResults, type LocalResult } from '../lib/guestResults';

const ACCEPT = '.wav,.flac,audio/wav,audio/x-wav,audio/flac';

export function DetectPage() {
  const { role } = useAuth();
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BatchDetectionResult | null>(null);
  const [selected, setSelected] = useState(0);
  const [audioFiles, setAudioFiles] = useState<(File | null)[]>([]);
  const [recent, setRecent] = useState<LocalResult[]>(loadGuestResults);
  const inputRef = useRef<HTMLInputElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  const addFiles = (list: FileList | File[]) => {
    const incoming = Array.from(list);
    if (incoming.length === 0) return;
    setFiles((prev) => [...prev, ...incoming]);
    setResult(null);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    addFiles(e.dataTransfer.files);
  };

  const submit = async () => {
    if (files.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const sent = files;
      const res = await api.predict(sent);
      setResult(res);
      setAudioFiles(matchFilesToResults(sent, res.results.map((r) => r.original_filename)));
      setSelected(0);
      setFiles([]);
      if (role !== 'user' && res.results.length > 0) setRecent(addGuestResults(res.results));
      scrollToResult();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'ตรวจเสียงไม่สำเร็จ ลองใหม่อีกครั้งนะ');
    } finally {
      setLoading(false);
    }
  };

  const scrollToResult = () =>
    requestAnimationFrame(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }));

  const openRecent = (item: LocalResult) => {
    setResult({ results: [item], failed_files: [] });
    setAudioFiles([null]); // ไฟล์เสียงไม่ได้ถูกเก็บไว้ ฟังซ้ำไม่ได้
    setSelected(0);
    scrollToResult();
  };

  const clearRecent = () => {
    if (!confirm('ล้างผลล่าสุดที่เก็บไว้ในเบราว์เซอร์นี้?')) return;
    clearGuestResults();
    setRecent([]);
  };

  const results = result?.results ?? [];
  const current = results[selected];

  return (
    <div className="stack">
      <section className="hero">
        <span className="eyebrow">
          <Icon name="sparkle" size={14} /> AI Voice Checker
        </span>
        <h1>
          เสียงนี้ <span className="grad-mint">คนจริง</span> หรือ <span className="grad-pink">AI</span> ?
        </h1>
        <p className="muted">อัปไฟล์หรืออัดเสียงสั้นๆ แล้วรู้ผลได้ในไม่กี่วินาที</p>
      </section>

      <section className="card stack">
        <div className="tiles">
          <div
            className={`tile tile-lavender ${dragging ? 'is-dragging' : ''}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && inputRef.current?.click()}
          >
            <span className="tile-icon">
              <Icon name="upload" size={26} />
            </span>
            <span className="tile-title">{dragging ? 'ปล่อยไฟล์ได้เลย!' : 'อัปโหลดไฟล์'}</span>
            <span className="tile-sub">ลากมาวาง หรือแตะเพื่อเลือก · .wav / .flac ไม่เกิน 20 MB</span>
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPT}
              multiple
              hidden
              onChange={(e) => {
                if (e.target.files) addFiles(e.target.files);
                e.target.value = '';
              }}
            />
          </div>

          <Recorder onRecorded={(file) => addFiles([file])} />
        </div>

        {files.length > 0 && (
          <ul className="file-chips">
            {files.map((file, i) => (
              <li key={`${file.name}-${i}`}>
                <Icon name="music" size={16} />
                <span className="file-name">{file.name}</span>
                <span className="muted small">{fileSize(file.size)}</span>
                <button
                  type="button"
                  className="btn-icon"
                  aria-label={`เอา ${file.name} ออก`}
                  onClick={() => setFiles((prev) => prev.filter((_, j) => j !== i))}
                >
                  <Icon name="close" size={16} />
                </button>
              </li>
            ))}
          </ul>
        )}

        <button className="btn btn-primary btn-big" disabled={files.length === 0 || loading} onClick={submit}>
          {loading ? (
            <>
              <span className="spinner" /> กำลังฟังอย่างตั้งใจ…
            </>
          ) : files.length === 0 ? (
            'เลือกไฟล์หรืออัดเสียงก่อนนะ'
          ) : (
            <>
              <Icon name="sparkle" size={18} /> เช็กเลย{files.length > 1 ? ` (${files.length} ไฟล์)` : ''}
            </>
          )}
        </button>

        {role !== 'user' && (
          <p className="hint">
            💡 <Link to="/register">สมัครฟรี</Link> หรือ <Link to="/login">เข้าสู่ระบบ</Link> เพื่อเก็บผลไว้ดูย้อนหลังและบอกเราได้ว่าผลถูกไหม
          </p>
        )}
        {error && <div className="callout callout-danger">{error}</div>}
      </section>

      <div ref={resultRef} className="stack scroll-anchor">
        {result && result.failed_files.length > 0 && (
          <section className="card stack-sm">
            <h3>😵 ไฟล์ที่ตรวจไม่ได้ ({result.failed_files.length})</h3>
            <ul className="failed-list">
              {result.failed_files.map((f, i) => (
                <li key={`${f.filename}-${i}`}>
                  <strong>{f.filename}</strong>
                  <span className="muted">{failureText(f.reason)}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {results.length > 1 && (
          <section className="card stack-sm">
            <h3>เทียบผล {results.length} ไฟล์</h3>
            <p className="muted small">แตะไฟล์เพื่อดูรายละเอียด</p>
            <div className="compare-list">
              {results.map((r, i) => (
                <button
                  key={r.id ?? i}
                  className={`compare-item ${i === selected ? 'is-selected' : ''}`}
                  onClick={() => setSelected(i)}
                >
                  <span className="file-name">{r.original_filename}</span>
                  <VerdictBadge verdict={r.verdict} />
                  {r.possible_partial_spoof && <span className="tag">อาจตัดต่อ</span>}
                  <span className="compare-pct">{pct(r.mean_probability, 0)}</span>
                </button>
              ))}
            </div>
          </section>
        )}

        {current && (
          <ResultView
            key={`${current.id ?? ''}-${selected}`}
            audio={audioFiles[selected]}
            filename={current.original_filename}
            verdict={current.verdict}
            meanProbability={current.mean_probability}
            maxProbability={current.max_probability}
            threshold={current.threshold_used}
            possiblePartialSpoof={current.possible_partial_spoof}
            durationSeconds={current.duration_seconds}
            modelVersion={current.model_version}
            processingMs={current.processing_ms}
            segments={current.segments}
            footer={
              current.saved_to_history && current.id ? (
                <Link className="btn btn-soft" to={`/history/${current.id}`}>
                  ผลนี้ถูกไหม? บอกเราหน่อย <Icon name="chevron" size={16} />
                </Link>
              ) : null
            }
          />
        )}
      </div>

      {role !== 'user' && recent.length > 0 && (
        <section className="card stack-sm">
          <div className="row between">
            <h3>🕘 ผลล่าสุดในเครื่องนี้</h3>
            <button className="btn btn-ghost btn-small" onClick={clearRecent}>
              ล้าง
            </button>
          </div>
          <p className="muted small" style={{ margin: 0 }}>
            เก็บแค่คะแนนไว้ในเบราว์เซอร์นี้ (20 รายการล่าสุด ไม่เก็บไฟล์เสียง) ·{' '}
            <Link to="/register">สมัครฟรี</Link> เพื่อเก็บถาวรและดูได้ทุกเครื่อง
          </p>
          <div className="list">
            {recent.map((r, i) => (
              <button key={`${r.id ?? r.original_filename}-${i}`} className="list-item" onClick={() => openRecent(r)}>
                <span className={`list-emoji is-${r.verdict}`}>{verdictEmoji(r.verdict)}</span>
                <span className="list-main">
                  <span className="file-name">{r.original_filename}</span>
                  <span className="list-meta">
                    <VerdictBadge verdict={r.verdict} />
                    {r.possible_partial_spoof && <span className="tag">อาจตัดต่อ</span>}
                    <span>{dateTime(r.saved_at)}</span>
                  </span>
                </span>
                <span className="list-side">
                  {pct(r.mean_probability, 0)}
                  <small>โอกาสเป็น AI</small>
                </span>
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

/** จับคู่ไฟล์ที่ส่งไปกับผลลัพธ์ (backend ตรวจตามลำดับและข้ามไฟล์ที่ไม่ผ่าน) เพื่อให้เล่นเสียงของผลแต่ละอันได้ */
function matchFilesToResults(sent: File[], resultNames: string[]): (File | null)[] {
  let cursor = 0;
  return resultNames.map((name) => {
    while (cursor < sent.length && sent[cursor].name !== name) cursor++;
    return cursor < sent.length ? sent[cursor++] : null;
  });
}
