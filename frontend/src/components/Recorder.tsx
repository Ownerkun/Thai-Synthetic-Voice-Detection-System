import { useEffect, useRef, useState } from 'react';
import { blobToWavFile } from '../lib/wav';
import { Icon } from './Icon';

const MAX_SECONDS = 10; // backend วิเคราะห์แค่ 10 วินาทีแรก

export function Recorder({ onRecorded }: { onRecorded: (file: File) => void }) {
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const timerRef = useRef<number | null>(null);

  const stopTimer = () => {
    if (timerRef.current !== null) window.clearInterval(timerRef.current);
    timerRef.current = null;
  };

  useEffect(
    () => () => {
      stopTimer();
      recorderRef.current?.stream.getTracks().forEach((t) => t.stop());
    },
    [],
  );

  const start = async () => {
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setError('เบราว์เซอร์นี้อัดเสียงไม่ได้ ลองอัปโหลดไฟล์แทนนะ');
      return;
    }
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setError('ยังไม่ได้อนุญาตให้ใช้ไมค์ ลองกดอนุญาตแล้วอัดใหม่');
      return;
    }

    const recorder = new MediaRecorder(stream);
    const chunks: Blob[] = [];
    recorder.ondataavailable = (e) => e.data.size > 0 && chunks.push(e.data);
    recorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      stopTimer();
      setRecording(false);
      try {
        const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
        const file = await blobToWavFile(new Blob(chunks, { type: recorder.mimeType }), `recording-${stamp}.wav`);
        onRecorded(file);
      } catch {
        setError('แปลงเสียงที่อัดไม่สำเร็จ ลองอัดใหม่อีกครั้ง');
      }
    };

    recorderRef.current = recorder;
    recorder.start();
    setRecording(true);
    setElapsed(0);
    const startedAt = Date.now();
    timerRef.current = window.setInterval(() => {
      const secs = (Date.now() - startedAt) / 1000;
      setElapsed(Math.min(secs, MAX_SECONDS));
      if (secs >= MAX_SECONDS && recorder.state === 'recording') recorder.stop();
    }, 100);
  };

  const stop = () => {
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop();
  };

  return (
    <button
      type="button"
      className={`tile tile-mint ${recording ? 'is-recording' : ''}`}
      onClick={recording ? stop : start}
      aria-pressed={recording}
    >
      <span className="tile-icon mic-icon">
        <Icon name={recording ? 'stop' : 'mic'} size={26} />
      </span>
      <span className="tile-title">{recording ? `กำลังอัด… ${elapsed.toFixed(1)} วิ` : 'อัดเสียง'}</span>
      <span className="tile-sub">{recording ? 'แตะอีกครั้งเพื่อหยุด' : 'พูดใส่ไมค์ได้สูงสุด 10 วินาที'}</span>
      {recording && (
        <span className="rec-progress">
          <span style={{ width: `${(elapsed / MAX_SECONDS) * 100}%` }} />
        </span>
      )}
      {error && <span className="tile-error">{error}</span>}
    </button>
  );
}
