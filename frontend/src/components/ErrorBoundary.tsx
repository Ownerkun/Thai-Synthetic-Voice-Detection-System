import { Component, type ErrorInfo, type ReactNode } from 'react';

interface State {
  failed: boolean;
}

/** กันหน้าขาวทั้งหน้าเมื่อ component ใดพัง แสดงทางออกให้ผู้ใช้แทน */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('UI crashed', error, info.componentStack);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="crash">
        <div className="card crash-card">
          <span className="empty-emoji" aria-hidden>
            🫠
          </span>
          <h1>มีบางอย่างผิดพลาด</h1>
          <p className="muted">หน้านี้แสดงผลไม่ได้ ลองกลับไปหน้าแรกหรือโหลดหน้าใหม่ ข้อมูลที่บันทึกไว้แล้วไม่หาย</p>
          <div className="row" style={{ justifyContent: 'center' }}>
            <a className="btn btn-primary" href={import.meta.env.BASE_URL}>
              กลับหน้าแรก
            </a>
            <button type="button" className="btn btn-ghost" onClick={() => window.location.reload()}>
              โหลดใหม่
            </button>
          </div>
        </div>
      </div>
    );
  }
}
