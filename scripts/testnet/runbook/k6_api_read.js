import http from 'k6/http';
import { check, sleep } from 'k6';

const base = __ENV.API_BASE_URL;
if (!base) {
  throw new Error('API_BASE_URL is required');
}

const profile = __ENV.PROFILE || 'baseline';
const isPeak = profile === 'peak';

const p95Default = isPeak ? 1000 : 500;
const p99Default = isPeak ? 3000 : 2000;
const errDefault = isPeak ? 0.01 : 0.001;

const p95 = __ENV.P95_MS ? parseInt(__ENV.P95_MS, 10) : p95Default;
const p99 = __ENV.P99_MS ? parseInt(__ENV.P99_MS, 10) : p99Default;
const errRate = __ENV.ERROR_RATE ? parseFloat(__ENV.ERROR_RATE) : errDefault;

export const options = {
  vus: __ENV.VUS ? parseInt(__ENV.VUS, 10) : isPeak ? 15 : 5,
  duration: __ENV.DURATION || (isPeak ? '5m' : '2m'),
  rps: __ENV.RPS ? parseInt(__ENV.RPS, 10) : undefined,
  thresholds: {
    http_req_failed: [`rate<${errRate}`],
    http_req_duration: [`p(95)<${p95}`, `p(99)<${p99}`],
  },
};

export default function () {
  const health = http.get(`${base}/health`);
  check(health, { 'health 200': (r) => r.status === 200 });

  const stats = http.get(`${base}/stats`);
  check(stats, { 'stats 200': (r) => r.status === 200 });

  const blocks = http.get(`${base}/blocks`);
  check(blocks, { 'blocks 200': (r) => r.status === 200 });

  const peers = http.get(`${base}/peers`);
  check(peers, { 'peers 200': (r) => r.status === 200 });

  sleep(1);
}

export function handleSummary(data) {
  if (__ENV.CALIBRATE !== '1') {
    return {};
  }
  const p95Val = Math.round(data.metrics.http_req_duration['p(95)']);
  const p99Val = Math.round(data.metrics.http_req_duration['p(99)']);
  const suggestedP95 = Math.round(p95Val * 2);
  const suggestedP99 = Math.round(p99Val * 3.5);
  const err = data.metrics.http_req_failed ? data.metrics.http_req_failed.rate : 0;
  const suggestedErr = Math.max(0.001, Math.min(0.01, err * 2 || 0.001));
  const out = [
    '',
    'Calibration summary:',
    `Observed p95=${p95Val}ms p99=${p99Val}ms error_rate=${(err * 100).toFixed(2)}%`,
    `Suggested thresholds: P95_MS=${suggestedP95} P99_MS=${suggestedP99} ERROR_RATE=${suggestedErr}`,
    '',
  ].join('\n');
  return { stdout: out };
}
