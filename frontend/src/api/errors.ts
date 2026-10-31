export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

/** status พิเศษที่ไม่ได้มาจาก HTTP */
export const STATUS_NETWORK = 0;
export const STATUS_TIMEOUT = 408;
export const STATUS_CANCELLED = -1;

export const isCancelled = (e: unknown) => e instanceof ApiError && e.status === STATUS_CANCELLED;
