import { useCallback, useEffect, useRef, useState } from 'react';

// เล่นเสียงจากไฟล์ที่ผู้ใช้เพิ่งอัปโหลด/อัด (อยู่ในหน่วยความจำของเบราว์เซอร์เท่านั้น backend ไม่เก็บไฟล์เสียง)
// playing: null = ไม่ได้เล่น, -1 = เล่นทั้งไฟล์, 0..n = เล่นเฉพาะ segment นั้น
export function useSegmentPlayer(file: File | null | undefined) {
  const [url, setUrl] = useState<string | null>(null);
  const [playing, setPlaying] = useState<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const endRef = useRef<number | null>(null);

  useEffect(() => {
    if (!file) {
      setUrl(null);
      return;
    }
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  useEffect(() => {
    if (!url) return;
    const audio = new Audio(url);
    audioRef.current = audio;
    const onTime = () => {
      if (endRef.current !== null && audio.currentTime >= endRef.current) audio.pause();
    };
    const onStop = () => setPlaying(null);
    audio.addEventListener('timeupdate', onTime);
    audio.addEventListener('pause', onStop);
    audio.addEventListener('ended', onStop);
    return () => {
      audio.pause();
      audio.removeEventListener('timeupdate', onTime);
      audio.removeEventListener('pause', onStop);
      audio.removeEventListener('ended', onStop);
      audioRef.current = null;
      setPlaying(null);
    };
  }, [url]);

  /** กดซ้ำที่ช่วงเดิม = หยุด */
  const play = useCallback(
    (index: number, startSeconds: number, endSeconds: number | null) => {
      const audio = audioRef.current;
      if (!audio) return;
      if (playing === index) {
        audio.pause();
        return;
      }
      endRef.current = endSeconds;
      audio.currentTime = startSeconds;
      setPlaying(index);
      audio.play().catch(() => setPlaying(null));
    },
    [playing],
  );

  return { available: url !== null, playing, play };
}
