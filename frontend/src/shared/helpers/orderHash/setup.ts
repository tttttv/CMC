const DEFAULT_TIME = 60 * 60; // 1 hour
type Milliseconds = number | undefined;
export const setupOrderHash = (hash: string, liveTime?: Milliseconds) =>
  (document.cookie = `order_hash=${hash}; max-age=${liveTime ? liveTime : DEFAULT_TIME}`);
