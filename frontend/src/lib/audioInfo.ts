// อ่านข้อมูลเสียงในเบราว์เซอร์ (ไม่ส่งไปไหน)
// - ความยาวไฟล์อ่านจาก header ของ WAV/FLAC โดยตรง ไม่ต้องถอดรหัสทั้งไฟล์ (เร็วและไม่กินหน่วยความจำ)
// - ภาพคลื่นเสียงถอดรหัสเฉพาะตอนแสดงผล แล้วเก็บแค่จุดสูงสุดไว้

const HEADER_BYTES = 64 * 1024;

/** ความยาว (วินาที) จาก header ของ WAV แบบ PCM/RIFF */
export function parseWavDuration(buf: ArrayBuffer, fileSize = buf.byteLength): number | null {
  const v = new DataView(buf);
  const tag = (o: number) => String.fromCharCode(v.getUint8(o), v.getUint8(o + 1), v.getUint8(o + 2), v.getUint8(o + 3));
  if (buf.byteLength < 12 || tag(0) !== 'RIFF' || tag(8) !== 'WAVE') return null;
  let byteRate = 0;
  let offset = 12;
  while (offset + 8 <= buf.byteLength) {
    const id = tag(offset);
    const size = v.getUint32(offset + 4, true);
    if (id === 'fmt ' && offset + 20 <= buf.byteLength) byteRate = v.getUint32(offset + 16, true);
    if (id === 'data') {
      if (!byteRate) return null;
      // บางโปรแกรมเขียนขนาด data เป็น 0 หรือ 0xFFFFFFFF ตอนอัดสด → ใช้ขนาดไฟล์แทน
      const dataSize = size === 0 || size === 0xffffffff ? fileSize - offset - 8 : Math.min(size, fileSize - offset - 8);
      return dataSize / byteRate;
    }
    offset += 8 + size + (size % 2);
  }
  return null;
}

/** ความยาว (วินาที) จาก STREAMINFO ของ FLAC */
export function parseFlacDuration(buf: ArrayBuffer): number | null {
  const b = new Uint8Array(buf);
  if (b.length < 26 || String.fromCharCode(b[0], b[1], b[2], b[3]) !== 'fLaC') return null;
  // block แรกต้องเป็น STREAMINFO (type 0), ข้อมูลเริ่มที่ byte 8
  if ((b[4] & 0x7f) !== 0) return null;
  const sampleRate = (b[18] << 12) | (b[19] << 4) | (b[20] >> 4);
  const totalSamples = (b[21] & 0x0f) * 2 ** 32 + ((b[22] << 24) >>> 0) + (b[23] << 16) + (b[24] << 8) + b[25];
  if (!sampleRate || !totalSamples) return null;
  return totalSamples / sampleRate;
}

export async function audioDuration(file: File): Promise<number | null> {
  try {
    const head = await file.slice(0, HEADER_BYTES).arrayBuffer();
    return parseWavDuration(head, file.size) ?? parseFlacDuration(head);
  } catch {
    return null;
  }
}

/** จุดสูงสุดของคลื่นเสียง (0..1) แบ่งเป็น `buckets` ช่อง ในช่วง 0..maxSeconds */
export async function waveformPeaks(file: File, maxSeconds: number, buckets = 240): Promise<number[] | null> {
  const ctx = new AudioContext();
  try {
    const decoded = await ctx.decodeAudioData(await file.arrayBuffer());
    const data = decoded.getChannelData(0);
    const usable = Math.min(data.length, Math.floor(maxSeconds * decoded.sampleRate));
    const step = Math.max(1, Math.floor(usable / buckets));
    const peaks: number[] = [];
    for (let i = 0; i < buckets && i * step < usable; i++) {
      let max = 0;
      for (let j = i * step; j < Math.min(usable, (i + 1) * step); j++) max = Math.max(max, Math.abs(data[j]));
      peaks.push(max);
    }
    const top = Math.max(...peaks, 1e-6);
    return peaks.map((p) => p / top);
  } catch {
    return null;
  } finally {
    void ctx.close();
  }
}
