/**
 * TinyModel sidecar availability probe (copy to HSP ai/ for transmitter Step 1).
 */

import { tinymodelBaseUrl } from "./tinymodel-client";

export type AvailabilitySnapshot = {
  tinymodel: boolean;
  openai?: boolean;
  ub?: boolean;
  swap_coffee?: boolean;
};

const DEFAULT_TIMEOUT_MS = 5000;
const DEFAULT_CACHE_MS = 45_000;
const FAILURE_THRESHOLD = 3;

export async function probeTinyModelHealth(
  baseUrl = tinymodelBaseUrl(),
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<boolean> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${baseUrl.replace(/\/$/, "")}/healthz`, {
      signal: controller.signal,
    });
    if (!res.ok) return false;
    const body = (await res.json()) as { status?: string };
    return body.status === "ok";
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

/** Circuit-breaker style cache for transmitter availability checks. */
export class TinyModelHealthCache {
  private available = true;
  private consecutiveFailures = 0;
  private lastProbeAt = 0;

  constructor(
    private readonly baseUrl = tinymodelBaseUrl(),
    private readonly cacheMs = DEFAULT_CACHE_MS,
    private readonly timeoutMs = DEFAULT_TIMEOUT_MS,
  ) {}

  async isAvailable(force = false): Promise<boolean> {
    const now = Date.now();
    if (!force && now - this.lastProbeAt < this.cacheMs) {
      return this.available;
    }
    this.lastProbeAt = now;
    const ok = await probeTinyModelHealth(this.baseUrl, this.timeoutMs);
    if (ok) {
      this.consecutiveFailures = 0;
      this.available = true;
    } else {
      this.consecutiveFailures += 1;
      if (this.consecutiveFailures >= FAILURE_THRESHOLD) {
        this.available = false;
      }
    }
    return this.available;
  }

  snapshot(): Pick<AvailabilitySnapshot, "tinymodel"> {
    return { tinymodel: this.available };
  }
}
