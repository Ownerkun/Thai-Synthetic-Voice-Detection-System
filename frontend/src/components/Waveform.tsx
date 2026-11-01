import { useEffect, useRef, useState, type KeyboardEvent, type MouseEvent } from 'react';
import type { SegmentResult } from '../api/types';
import { waveformPeaks } from '../lib/audioInfo';

interface Props {
  file: File;
  segments: SegmentResult[];
  /** ความยาวที่ระบบวิเคราะห์ (วินาที) ภาพคลื่นแสดงเฉพาะช่วงนี้ */
  duration: number;
  playingIndex: number | null;
  onPlay: (segment: SegmentResult) => void;
}

const HEIGHT = 64;

/** ภาพคลื่นเสียง (A5) ระบายสีตามช่วงที่ระบบให้คะแนน แตะเพื่อฟังช่วงนั้น */
export function Waveform({ file, segments, duration, playingIndex, onPlay }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [peaks, setPeaks] = useState<number[] | null>(null);

  useEffect(() => {
    let alive = true;
    setPeaks(null);
    waveformPeaks(file, duration).then((p) => alive && setPeaks(p));
    return () => {
      alive = false;
    };
  }, [file, duration]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !peaks || peaks.length === 0) return;
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth || 600;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(HEIGHT * dpr);
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, HEIGHT);

    const css = getComputedStyle(document.documentElement);
    const spoof = css.getPropertyValue('--spoof-bar').trim() || '#ff9bc0';
    const real = css.getPropertyValue('--real-bar').trim() || '#7ddcb4';
    const highlight = css.getPropertyValue('--primary-soft').trim() || '#efe9ff';

    const segAt = (t: number) => segments.find((s) => t >= s.start_seconds && t < s.end_seconds) ?? segments[segments.length - 1];

    // ไฮไลต์ช่วงที่กำลังเล่น
    const playing = segments.find((s) => s.index === playingIndex);
    if (playing) {
      ctx.fillStyle = highlight;
      const x0 = (playing.start_seconds / duration) * width;
      const x1 = (Math.min(playing.end_seconds, duration) / duration) * width;
      ctx.fillRect(x0, 0, x1 - x0, HEIGHT);
    }

    const barW = width / peaks.length;
    peaks.forEach((p, i) => {
      const t = ((i + 0.5) / peaks.length) * duration;
      ctx.fillStyle = segAt(t)?.is_spoof ? spoof : real;
      const h = Math.max(2, p * (HEIGHT - 6));
      ctx.fillRect(i * barW, (HEIGHT - h) / 2, Math.max(1, barW - 1), h);
    });
  }, [peaks, segments, duration, playingIndex]);

  const pick = (ratio: number) => {
    const t = ratio * duration;
    const seg = segments.find((s) => t >= s.start_seconds && t < s.end_seconds) ?? segments[segments.length - 1];
    if (seg) onPlay(seg);
  };

  const onClick = (e: MouseEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    pick((e.clientX - rect.left) / rect.width);
  };

  const onKey = (e: KeyboardEvent<HTMLCanvasElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      pick(0);
    }
  };

  if (peaks === null) return <div className="waveform waveform-loading" aria-hidden />;
  if (peaks.length === 0) return null;
  return (
    <canvas
      ref={canvasRef}
      className="waveform"
      style={{ height: HEIGHT }}
      role="button"
      tabIndex={0}
      aria-label="ภาพคลื่นเสียง แตะเพื่อฟังช่วงที่แตะ"
      title="แตะเพื่อฟังช่วงนั้น"
      onClick={onClick}
      onKeyDown={onKey}
    />
  );
}
