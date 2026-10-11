import type { SegmentResult } from '../api/types';
import { pct } from '../lib/format';

interface Props {
  segments: SegmentResult[];
  threshold: number;
  /** ถ้ามี = แท่งกดได้ เพื่อฟังเสียงช่วงนั้น */
  onPlay?: (segment: SegmentResult) => void;
  playingIndex?: number | null;
}

/** แท่งคะแนนรายช่วงเวลา: ความกว้าง = ความยาวช่วง, ความสูง = ความน่าจะเป็นที่เป็นเสียงสังเคราะห์ */
export function SegmentChart({ segments, threshold, onPlay, playingIndex }: Props) {
  if (segments.length === 0) return null;
  const total = segments[segments.length - 1].end_seconds || 1;
  const grow = (s: SegmentResult) => Math.max(s.end_seconds - s.start_seconds, 0.01) / total;

  return (
    <figure className="segchart">
      <div className="segchart-plot" role={onPlay ? 'group' : 'img'} aria-label="คะแนนรายช่วงเวลา">
        <div className="segchart-threshold" style={{ bottom: `${threshold * 100}%` }}>
          <span>เกณฑ์ {pct(threshold, 0)}</span>
        </div>
        {segments.map((s) => {
          const label = `${s.start_seconds.toFixed(1)}–${s.end_seconds.toFixed(1)} วิ: ${pct(s.spoof_probability)}`;
          const bar = (
            <div
              className={`segchart-bar ${s.is_spoof ? 'is-spoof' : 'is-real'} ${playingIndex === s.index ? 'is-playing' : ''}`}
              style={{ height: `${Math.max(s.spoof_probability * 100, 2)}%` }}
            >
              <span className="segchart-value">{pct(s.spoof_probability, 0)}</span>
            </div>
          );
          return onPlay ? (
            <button
              key={s.index}
              type="button"
              className="segchart-col is-playable"
              style={{ flexGrow: grow(s) }}
              onClick={() => onPlay(s)}
              aria-label={`${playingIndex === s.index ? 'หยุด' : 'ฟัง'}ช่วง ${label}`}
              title={`แตะเพื่อฟัง · ${label}`}
            >
              {bar}
            </button>
          ) : (
            <div key={s.index} className="segchart-col" style={{ flexGrow: grow(s) }} title={label}>
              {bar}
            </div>
          );
        })}
      </div>
      <div className="segchart-axis">
        {segments.map((s) => (
          <span key={s.index} style={{ flexGrow: grow(s) }}>
            {playingIndex === s.index ? '🔊 ' : ''}
            {s.start_seconds.toFixed(0)}–{s.end_seconds.toFixed(0)} วิ
          </span>
        ))}
      </div>
      <figcaption className="segchart-legend">
        <span>
          <i className="dot is-spoof" /> ช่วงที่น่าสงสัย
        </span>
        <span>
          <i className="dot is-real" /> ช่วงปกติ
        </span>
      </figcaption>
    </figure>
  );
}
