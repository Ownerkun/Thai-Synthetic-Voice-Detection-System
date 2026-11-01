import { useState, type CSSProperties, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import type { SegmentResult, Verdict } from '../api/types';
import { downloadBlob } from '../lib/csv';
import { pct, seconds, verdictEmoji, verdictLabel } from '../lib/format';
import { flaggedSegments, isBorderline, modelLabel } from '../lib/result';
import { drawResultImage } from '../lib/resultImage';
import { useSegmentPlayer } from '../lib/useSegmentPlayer';
import { Icon } from './Icon';
import { SegmentChart } from './SegmentChart';
import { useUi } from './UiProvider';
import { Waveform } from './Waveform';

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return (
    <span className={`badge ${verdict === 'spoof' ? 'badge-spoof' : 'badge-real'}`}>
      {verdictEmoji(verdict)} {verdictLabel(verdict)}
    </span>
  );
}

/** ป้าย "ก้ำกึ่ง" (A4) เมื่อคะแนนเฉลี่ยใกล้เกณฑ์ */
export function BorderlineTag({ mean, threshold }: { mean: number; threshold: number }) {
  if (!isBorderline(mean, threshold)) return null;
  return (
    <span className="tag tag-mid" title="คะแนนใกล้เกณฑ์มาก ผลไม่ชัดเจน">
      ⚖️ ก้ำกึ่ง
    </span>
  );
}

/** วงแหวนคะแนน (conic-gradient) */
export function Gauge({ value, verdict, size = 132 }: { value: number; verdict: Verdict; size?: number }) {
  const style = { '--p': Math.round(value * 100), '--size': `${size}px` } as CSSProperties;
  return (
    <div className={`gauge gauge-${verdict}`} style={style} role="img" aria-label={`คะแนนความน่าสงสัยว่าเป็นเสียง AI ${pct(value)}`}>
      <div className="gauge-inner">
        <strong>{pct(value, 0)}</strong>
        <span>คะแนนน่าสงสัย</span>
      </div>
    </div>
  );
}

interface Props {
  filename: string;
  verdict: Verdict;
  meanProbability: number;
  maxProbability: number;
  threshold: number;
  possiblePartialSpoof: boolean;
  durationSeconds: number;
  modelVersion: string;
  processingMs: number;
  segments: SegmentResult[];
  /** ไฟล์เสียงต้นฉบับ (มีเฉพาะตอนเพิ่งตรวจ) ใช้เล่นเสียงรายช่วงและวาดคลื่นเสียง */
  audio?: File | null;
  /** เวลาที่ตรวจ ใช้ในรูปที่บันทึก */
  checkedAt?: string | null;
  /** เวลาประมวลผลมีประโยชน์กับผู้ดูแลเท่านั้น */
  showTiming?: boolean;
  footer?: ReactNode;
}

export function ResultView(props: Props) {
  const { toast } = useUi();
  const [saving, setSaving] = useState(false);
  const spoof = props.verdict === 'spoof';
  const player = useSegmentPlayer(props.audio);
  const flagged = flaggedSegments(props.segments);
  const borderline = isBorderline(props.meanProbability, props.threshold);
  // ผลรวมเป็นเสียงจริง แต่มีบางช่วงเกินเกณฑ์ และ backend ไม่ได้ติดป้าย "อาจตัดต่อ" → เตือนเพิ่ม (แสดงผลเท่านั้น ไม่เปลี่ยนคำตัดสิน)
  const hiddenRisk = !spoof && !props.possiblePartialSpoof && flagged.length > 0;

  const saveImage = async () => {
    setSaving(true);
    try {
      const blob = await drawResultImage({ ...props, checkedAt: props.checkedAt });
      const base = props.filename.replace(/\.[^.]+$/, '') || 'result';
      downloadBlob(blob, `ผลตรวจ-${base}.png`);
      toast('บันทึกรูปผลตรวจแล้ว');
    } catch {
      toast('สร้างรูปไม่สำเร็จ ลองอีกครั้ง', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className={`card result result-${props.verdict}`}>
      <div className="result-hero">
        <Gauge value={props.meanProbability} verdict={props.verdict} />
        <div className="result-text">
          <div className="file-pill">
            <Icon name="music" size={14} />
            {props.filename}
          </div>
          <h2>
            {verdictEmoji(props.verdict)} {spoof ? 'น่าจะเป็นเสียง AI' : 'น่าจะเป็นเสียงคนจริง'}
            {borderline && <span className="tag tag-mid verdict-tag">⚖️ ก้ำกึ่ง</span>}
          </h2>
          <p className="muted">
            {spoof
              ? `คะแนนเฉลี่ยเกินเกณฑ์ ${pct(props.threshold, 0)} ระบบจึงตัดสินว่าเป็นเสียงสังเคราะห์`
              : `คะแนนเฉลี่ยต่ำกว่าเกณฑ์ ${pct(props.threshold, 0)} ระบบจึงตัดสินว่าเป็นเสียงจริง`}
          </p>
          <Link to="/about#read" className="info-link">
            <Icon name="info" size={14} /> คะแนนนี้คืออะไร
          </Link>
        </div>
      </div>

      {borderline && (
        <div className="callout callout-mid">
          <span aria-hidden>⚖️</span>
          <span>
            ก้ำกึ่ง: คะแนนเฉลี่ยห่างจากเกณฑ์แค่ {Math.abs((props.meanProbability - props.threshold) * 100).toFixed(1)} จุด
            ผลนี้ไม่ชัดเจน ควรฟังประกอบและใช้หลักฐานอื่นร่วมด้วย
          </span>
        </div>
      )}

      {props.possiblePartialSpoof && (
        <div className="callout callout-warn">
          <span aria-hidden>👀</span>
          <span>บางช่วงคะแนนสูง บางช่วงต่ำมาก เสียงนี้อาจถูกตัดต่อมาบางส่วน ดูกราฟรายช่วงด้านล่างได้เลย</span>
        </div>
      )}

      {hiddenRisk && (
        <div className="callout callout-warn">
          <span aria-hidden>🔎</span>
          <span>
            ค่าเฉลี่ยต่ำกว่าเกณฑ์ แต่มี {flagged.length} ช่วงที่คะแนนเกินเกณฑ์ (สูงสุด {pct(props.maxProbability)}) ลองดูแท่งสีชมพูในกราฟด้านล่าง
          </span>
        </div>
      )}

      <div className="chips">
        <span className="chip">
          <small>สูงสุดรายช่วง</small>
          {pct(props.maxProbability)}
        </span>
        <span className="chip">
          <small>เกณฑ์ตัดสิน</small>
          {pct(props.threshold, 0)}
        </span>
        <span className="chip">
          <small>ความยาวที่วิเคราะห์</small>
          {seconds(props.durationSeconds)}
        </span>
        {props.showTiming ? (
          <span className="chip">
            <small>ใช้เวลาประมวลผล</small>
            {props.processingMs} ms
          </span>
        ) : (
          <span className="chip">
            <small>ช่วงที่เกินเกณฑ์</small>
            {flagged.length} / {props.segments.length}
          </span>
        )}
      </div>

      <div className="subcard">
        <div className="subcard-head">
          <div className="subcard-title">
            <Icon name="chart" size={16} /> คะแนนรายช่วงเวลา
          </div>
          {player.available && (
            <button
              type="button"
              className={`btn btn-soft btn-small ${player.playing === -1 ? 'is-active' : ''}`}
              onClick={() => player.play(-1, 0, null)}
            >
              <Icon name={player.playing === -1 ? 'pause' : 'play'} size={14} />
              {player.playing === -1 ? 'หยุด' : 'ฟังทั้งไฟล์'}
            </button>
          )}
        </div>
        {props.audio && (
          <Waveform
            file={props.audio}
            segments={props.segments}
            duration={props.durationSeconds}
            playingIndex={player.playing}
            onPlay={(s) => player.play(s.index, s.start_seconds, s.end_seconds)}
          />
        )}
        <SegmentChart
          segments={props.segments}
          threshold={props.threshold}
          playingIndex={player.playing}
          onPlay={player.available ? (s) => player.play(s.index, s.start_seconds, s.end_seconds) : undefined}
        />
        {player.available && <p className="segchart-hint">🎧 แตะแท่งกราฟหรือภาพคลื่นเสียงเพื่อฟังเฉพาะช่วงนั้น</p>}
      </div>

      <div className="result-foot">
        <span className="muted small" title={props.modelVersion}>
          โมเดล: {modelLabel(props.modelVersion)}
        </span>
        <div className="row wrap">
          <button type="button" className="btn btn-ghost btn-small" onClick={saveImage} disabled={saving}>
            <Icon name="image" size={16} /> {saving ? 'กำลังสร้างรูป…' : 'บันทึกผลเป็นรูป'}
          </button>
          {props.footer}
        </div>
      </div>
    </section>
  );
}
