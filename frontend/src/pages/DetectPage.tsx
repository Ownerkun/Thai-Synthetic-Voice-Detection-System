import { useEffect, useMemo, useRef, useState, type DragEvent } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError, isCancelled } from '../api/client';
import type { BatchDetectionResult } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { Icon } from '../components/Icon';
import { Recorder } from '../components/Recorder';
import { useUi } from '../components/UiProvider';
import { audioDuration } from '../lib/audioInfo';
import { checkFile, MAX_FILES_PER_CHECK } from '../lib/audioRules';
import { BorderlineTag, ResultView, VerdictBadge } from '../components/ResultView';
import { dateTime, failureText, fileSize, pct, seconds, verdictEmoji } from '../lib/format';
import { addGuestResults, clearGuestResults, loadGuestResults, type LocalResult } from '../lib/guestResults';

const ACCEPT = '.wav,.flac,audio/wav,audio/x-wav,audio/flac';
const ANALYZED_SECONDS = 10; // backend วิเคราะห์แค่ 10 วินาทีแรก

// ไฟล์ตัวอย่าง (A1): ทีมวางไฟล์ไว้ใน public/samples/ แล้วระบุใน manifest.json
interface Sample {
  file: string;
  label: string;
  note?: string;
}
const SAMPLES_BASE = `${import.meta.env.BASE_URL}samples/`;

export function DetectPage() {
  const { role } = useAuth();
  const { confirm, toast } = useUi();
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
  const abortRef = useRef<AbortController | null>(null);
  const [progress, setProgress] = useState(0);
  const [durations, setDurations] = useState<Map<File, number | null>>(new Map());
  const [samples, setSamples] = useState<Sample[]>([]);
  const [loadingSample, setLoadingSample] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${SAMPLES_BASE}manifest.json`)
      .then((r) => (r.ok ? r.json() : []))
      .then((list: unknown) => setSamples(Array.isArray(list) ? (list as Sample[]) : []))
      .catch(() => setSamples([]));
  }, []);

  // อ่านความยาวจาก header ของไฟล์ (A3) เพื่อบอกล่วงหน้าว่าจะถูกตัดที่ 10 วินาที
  useEffect(() => {
    const unknown = files.filter((f) => !durations.has(f));
    if (unknown.length === 0) return;
    let alive = true;
    Promise.all(unknown.map(async (f) => [f, await audioDuration(f)] as const)).then((pairs) => {
      if (!alive) return;
      setDurations((prev) => {
        const next = new Map(prev);
        for (const [f, d] of pairs) next.set(f, d);
        return next;
      });
    });
    return () => {
      alive = false;
    };
  }, [files, durations]);

  const addSample = async (sample: Sample) => {
    setLoadingSample(sample.file);
    try {
      const res = await fetch(`${SAMPLES_BASE}${sample.file}`);
      if (!res.ok) throw new Error(String(res.status));
      const blob = await res.blob();
      addFiles([new File([blob], sample.file, { type: blob.type || 'audio/wav' })]);
    } catch {
      toast('โหลดไฟล์ตัวอย่างไม่สำเร็จ', 'error');
    } finally {
      setLoadingSample(null);
    }
  };

  // เช็กไฟล์ตั้งแต่ตอนเลือก (F2): ไฟล์ที่ไม่ผ่านแสดงเหตุผลบนชิปทันที และจะไม่ถูกส่ง
  const checked = useMemo(() => {
    let accepted = 0;
    return files.map((file) => {
      const issue = checkFile(file) ?? (accepted >= MAX_FILES_PER_CHECK ? 'too_many_files' : null);
      if (!issue) accepted++;
      return { file, issue };
    });
  }, [files]);
  const sendable = checked.filter((c) => !c.issue).map((c) => c.file);
  const rejected = checked.length - sendable.length;

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
    if (sendable.length === 0) return;
    setLoading(true);
    setError(null);
    const controller = new AbortController();
    abortRef.current = controller;
    setProgress(0);
    try {
      const sent = sendable;
      const res = await api.predict(sent, controller.signal, setProgress);
      setResult(res);
      setAudioFiles(matchFilesToResults(sent, res.results.map((r) => r.original_filename)));
      setSelected(0);
      setFiles([]);
      if (role !== 'user' && res.results.length > 0) setRecent(addGuestResults(res.results));
      scrollToResult();
    } catch (e) {
      // ไฟล์ที่เลือกยังอยู่ กด "ลองอีกครั้ง" ได้เลย (F3)
      if (isCancelled(e)) toast('ยกเลิกการตรวจแล้ว', 'info');
      else setError(e instanceof ApiError ? e.message : 'ตรวจเสียงไม่สำเร็จ ลองอีกครั้ง');
    } finally {
      abortRef.current = null;
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

  const clearRecent = async () => {
    const ok = await confirm({
      title: 'ล้างผลล่าสุด?',
      message: `ผล ${recent.length} รายการที่เก็บไว้ในเบราว์เซอร์นี้จะหายไป`,
      confirmLabel: 'ล้างผลล่าสุด',
      danger: true,
    });
    if (!ok) return;
    clearGuestResults();
    setRecent([]);
    toast('ล้างผลล่าสุดแล้ว');
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

        {samples.length > 0 && (
          <div className="samples" role="group" aria-label="ไฟล์ตัวอย่าง">
            <span className="muted small">ลองไฟล์ตัวอย่าง:</span>
            {samples.map((sample) => (
              <button
                key={sample.file}
                type="button"
                className="fchip"
                title={sample.note}
                disabled={loadingSample !== null}
                onClick={() => addSample(sample)}
              >
                {loadingSample === sample.file ? 'กำลังโหลด…' : sample.label}
              </button>
            ))}
          </div>
        )}

        {files.length > 0 && (
          <ul className="file-chips">
            {checked.map(({ file, issue }, i) => (
              <li key={`${file.name}-${i}`} className={issue ? 'is-invalid' : ''}>
                <Icon name="music" size={16} />
                <span className="file-name">{file.name}</span>
                <span className="small chip-note">
                  {issue ? (
                    failureText(issue)
                  ) : (durations.get(file) ?? 0) > ANALYZED_SECONDS + 0.05 ? (
                    <span className="chip-long">
                      ยาว {seconds(durations.get(file) ?? 0)} → ใช้ {ANALYZED_SECONDS} วิแรก
                    </span>
                  ) : (
                    fileSize(file.size)
                  )}
                </span>
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
        {rejected > 0 && (
          <div className="row between wrap">
            <span className="muted small">
              ส่งตรวจได้ {sendable.length} ไฟล์ · ข้าม {rejected} ไฟล์ที่ไม่ผ่าน
            </span>
            <button
              type="button"
              className="btn btn-ghost btn-small"
              onClick={() => setFiles(checked.filter((c) => !c.issue).map((c) => c.file))}
            >
              เอาไฟล์ที่ไม่ผ่านออก
            </button>
          </div>
        )}

        <button
          className={`btn btn-primary btn-big ${files.length > 0 ? 'is-sticky' : ''}`}
          disabled={sendable.length === 0 || loading}
          onClick={submit}
        >
          {loading ? (
            <>
              <span className="spinner" /> กำลังฟังอย่างตั้งใจ…
            </>
          ) : files.length === 0 ? (
            'เลือกไฟล์หรืออัดเสียงก่อนนะ'
          ) : sendable.length === 0 ? (
            'ไม่มีไฟล์ที่ตรวจได้'
          ) : (
            <>
              <Icon name="sparkle" size={18} /> เช็กเลย{sendable.length > 1 ? ` (${sendable.length} ไฟล์)` : ''}
            </>
          )}
        </button>
        {loading && (
          <div className="upload-progress" role="status">
            <div className="row between small">
              <span>{progress < 1 ? `กำลังส่งไฟล์… ${Math.round(progress * 100)}%` : 'ส่งครบแล้ว กำลังวิเคราะห์เสียง…'}</span>
              <button type="button" className="btn btn-ghost btn-small" onClick={() => abortRef.current?.abort()}>
                ยกเลิก
              </button>
            </div>
            <div
              className={`progress-bar ${progress >= 1 ? 'is-busy' : ''}`}
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(progress * 100)}
            >
              <span style={{ width: `${Math.max(4, progress * 100)}%` }} />
            </div>
          </div>
        )}

        {role !== 'user' && (
          <p className="hint">
            💡 <Link to="/register">สมัครฟรี</Link> หรือ <Link to="/login">เข้าสู่ระบบ</Link> เพื่อเก็บผลไว้ดูย้อนหลังและบอกเราได้ว่าผลถูกไหม
          </p>
        )}
        {error && (
          <div className="callout callout-danger error-card" role="alert">
            <span>{error}</span>
            {sendable.length > 0 && (
              <button type="button" className="btn btn-primary btn-small" onClick={submit}>
                ลองอีกครั้ง
              </button>
            )}
          </div>
        )}
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
                  <BorderlineTag mean={r.mean_probability} threshold={r.threshold_used} />
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
            checkedAt={'saved_at' in current ? String(current.saved_at) : null}
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
                    <BorderlineTag mean={r.mean_probability} threshold={r.threshold_used} />
                    <span>{dateTime(r.saved_at)}</span>
                  </span>
                </span>
                <span className="list-side">
                  {pct(r.mean_probability, 0)}
                  <small>คะแนนน่าสงสัย</small>
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
