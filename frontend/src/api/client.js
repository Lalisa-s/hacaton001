import { createApi } from './api.js';

// H5 development uses the Vite /api proxy. A phone uses the same page origin,
// so localhost always remains on the dev computer, never on the phone.
const configuredUrl = import.meta.env.VITE_API_BASE_URL;
const origin = typeof window !== 'undefined' ? window.location.origin : '';
const baseUrl = configuredUrl || `${origin}/api/v1`;

const DEMO_KEY = 'family-banking-demo-user';
export function getDemoUserId() {
  const id = uni.getStorageSync(DEMO_KEY);
  return [10, 20, 11].includes(id) ? id : 10;
}
export function setDemoUserId(id) {
  if (![10, 20, 11].includes(id)) throw new TypeError('Неизвестный демо-профиль.');
  uni.setStorageSync(DEMO_KEY, id);
}

// Explicit demo actor selection; this header is not authentication.
export const api = createApi({ baseUrl, request: (options) => uni.request({
  ...options,
  header: { ...options.header, 'X-Demo-User-Id': String(getDemoUserId()) },
}) });
