import type { OnboardingResult, StartRequest } from "./types";

const RESULT_KEY = (id: string) => `onb:result:${id}`;
const REQUEST_KEY = (id: string) => `onb:request:${id}`;
const LAST_REQUEST_KEY = "onb:last-request";

function read<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function write(key: string, value: unknown) {
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage unavailable */
  }
}

export function saveResult(result: OnboardingResult, req?: StartRequest) {
  write(RESULT_KEY(result.onboarding_id), result);
  if (req) write(REQUEST_KEY(result.onboarding_id), req);
}

export const loadResult = (id: string) =>
  read<OnboardingResult>(RESULT_KEY(id));

export const loadRequest = (id: string) => read<StartRequest>(REQUEST_KEY(id));

export const saveLastRequest = (req: StartRequest) =>
  write(LAST_REQUEST_KEY, req);

export const loadLastRequest = () => read<StartRequest>(LAST_REQUEST_KEY);
