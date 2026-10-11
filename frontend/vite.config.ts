import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// ตอน dev: เรียก API ผ่าน /api แล้ว Vite proxy ต่อไปที่ backend (ค่าเริ่มต้น http://localhost:8000)
// ทำให้ไม่ต้องพึ่ง CORS และไม่ต้องแก้อะไรฝั่ง backend
const backend = process.env.BACKEND_URL ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: backend,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
