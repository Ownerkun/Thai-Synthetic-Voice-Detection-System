import type { CSSProperties, ReactNode } from 'react';
import type { SegmentResult, Verdict } from '../api/types';
import { pct, seconds, verdictEmoji, verdictLabel } from '../lib/format';
import { useSegmentPlayer } from '../lib/useSegmentPlayer';
import { Icon } from './Icon';
import { SegmentChart } from './SegmentChart';

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return (
    <span className={`badge ${verdict === 'spoof' ? 'badge-spoof' : 'badge-real'}`}>
      {verdictEmoji(verdict)} {verdictLabel(verdict)}
    </span>
  );
}

/** วงแหวนเปอร์เซ็นต์ (conic-gradient) */
export function Gauge({ value, verdict, size = 132 }: { value: number; verdict: Verdict; size?: number }) {
  const style = { '--p': Math.round(value * 100), '--size': `${size}px` } as CSSProperties;
  return (
    <div className={`gauge gauge-${verdict}`} style={style} role="img" aria-label={`โอกาสเป็นเสียง AI ${pct(value)}`}>
      <div className="gauge-inner">
        <strong>{pct(value, 0)}</strong>
        <span>โอกาสเป็น AI</span>
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
  /** ไฟล์เสียงต้นฉบับ (มีเฉพาะตอนเพิ่งตรวจ) ใช้เล่นเสียงรายช่วง */
  audio?: File | null;
  footer?: ReactNode;
}

export function ResultView(props: Props) {
  const spoof = props.verdict === 'spoof';
  const player = useSegmentPlayer(props.audio);
  // ผลรวมเป็นเสียงจริง แต่มีบางช่วงเกินเกณฑ์ และ backend ไม่ได้ติดป้าย "อาจตัดต่อ" → เตือนเพิ่ม (แสดงผลเท่านั้น ไม่เปลี่ยนคำตัดสิน)
  const flagged = props.segments.filter((s) => s.is_spoof);
  const hiddenRisk = !spoof && !props.possiblePartialSpoof && flagged.length > 0;
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
          </h2>
          <p className="muted">
            {spoof
              ? `คะแนนเฉลี่ยเกินเกณฑ์ ${pct(props.threshold, 0)} ระบบจึงตัดสินว่าเป็นเสียงสังเคราะห์`
              : `คะแนนเฉลี่ยต่ำกว่าเกณฑ์ ${pct(props.threshold, 0)} ระบบจึงตัดสินว่าเป็นเสียงจริง`}
          </p>
        </div>
      </div>

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
          <small>ความยาว</small>
          {seconds(props.durationSeconds)}
        </span>
        <span className="chip">
          <small>ใช้เวลา</small>
          {props.processingMs} ms
        </span>
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
        <SegmentChart
          segments={props.segments}
          threshold={props.threshold}
          playingIndex={player.playing}
          onPlay={
            player.available ? (s) => player.play(s.index, s.start_seconds, s.end_seconds) : undefined
          }
        />
        {player.available && <p className="segchart-hint">🎧 แตะแท่งกราฟเพื่อฟังเสียงเฉพาะช่วงนั้น</p>}
      </div>

      <div className="result-foot">
        <span className="muted small">โมเดล: {props.modelVersion}</span>
        {props.footer}
      </div>
    </section>
  );
}
