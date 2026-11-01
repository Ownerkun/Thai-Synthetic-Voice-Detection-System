import type { FailureReason } from '../api/types';

// กติกาเดียวกับ backend (app/core/config.py: allowed_audio_extensions, max_upload_size_bytes)
// เช็กตั้งแต่ตอนเลือกไฟล์ ไฟล์ที่ไม่ผ่านจะไม่ถูกส่ง ไม่ต้องรออัปโหลดแล้วค่อยโดนปฏิเสธ
export const ALLOWED_EXTENSIONS = ['.wav', '.flac'];
export const MAX_FILE_BYTES = 20 * 1024 * 1024;
export const MAX_FILES_PER_CHECK = 10;

export function checkFile(file: File): FailureReason | null {
  const dot = file.name.lastIndexOf('.');
  const ext = dot >= 0 ? file.name.slice(dot).toLowerCase() : '';
  if (!ALLOWED_EXTENSIONS.includes(ext)) return 'unsupported_format';
  if (file.size <= 0) return 'empty_audio';
  if (file.size > MAX_FILE_BYTES) return 'file_too_large';
  return null;
}
