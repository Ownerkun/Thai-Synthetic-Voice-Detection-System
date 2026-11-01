import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';

// กล่องยืนยันและ toast ของแอปเอง ใช้แทน window.confirm()/alert()
// (เบราว์เซอร์ในแอปอย่าง LINE/Facebook บางตัวบล็อกกล่องของเบราว์เซอร์ ทำให้ confirm() คืน false ทันที)

export interface ConfirmOptions {
  title: string;
  message?: ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  danger?: boolean;
}

type ToastKind = 'ok' | 'error' | 'info';

interface UiApi {
  confirm: (options: ConfirmOptions) => Promise<boolean>;
  toast: (text: string, kind?: ToastKind) => void;
}

const UiContext = createContext<UiApi | null>(null);

interface OpenDialog extends ConfirmOptions {
  resolve: (ok: boolean) => void;
}

export function UiProvider({ children }: { children: ReactNode }) {
  const [dialog, setDialog] = useState<OpenDialog | null>(null);
  const [toasts, setToasts] = useState<{ id: number; text: string; kind: ToastKind }[]>([]);
  const nextId = useRef(0);

  const confirm = useCallback(
    (options: ConfirmOptions) => new Promise<boolean>((resolve) => setDialog({ ...options, resolve })),
    [],
  );

  const toast = useCallback((text: string, kind: ToastKind = 'ok') => {
    const id = ++nextId.current;
    setToasts((list) => [...list, { id, text, kind }]);
    window.setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), 4000);
  }, []);

  const close = useCallback(
    (ok: boolean) => {
      dialog?.resolve(ok);
      setDialog(null);
    },
    [dialog],
  );

  useEffect(() => {
    if (!dialog) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [dialog, close]);

  return (
    <UiContext.Provider value={{ confirm, toast }}>
      {children}

      {dialog && (
        <div className="dialog-backdrop" onClick={() => close(false)}>
          <div
            className="dialog"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="dialog-title"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 id="dialog-title">{dialog.title}</h3>
            {dialog.message && <div className="dialog-body muted">{dialog.message}</div>}
            <div className="dialog-actions">
              {/* ปุ่มยกเลิกได้โฟกัสก่อน กด Enter พลาดจะไม่ลบ/ระงับอะไร */}
              <button type="button" className="btn btn-ghost" autoFocus onClick={() => close(false)}>
                {dialog.cancelLabel ?? 'ยกเลิก'}
              </button>
              <button
                type="button"
                className={`btn ${dialog.danger ? 'btn-danger' : 'btn-primary'}`}
                onClick={() => close(true)}
              >
                {dialog.confirmLabel}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="toasts" aria-live="polite" role="status">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.kind}`}>
            {t.text}
          </div>
        ))}
      </div>
    </UiContext.Provider>
  );
}

export function useUi(): UiApi {
  const ctx = useContext(UiContext);
  if (!ctx) throw new Error('useUi must be used inside UiProvider');
  return ctx;
}
