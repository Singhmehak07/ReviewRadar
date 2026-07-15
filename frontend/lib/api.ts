import type { BatchResponse, ReviewResult } from "./types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "https://reviewradar-dxhb.onrender.com").replace(/\/$/, "");

async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs: number = 90000): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(id);
    return response;
  } catch (err: any) {
    clearTimeout(id);
    if (err.name === "AbortError") {
      throw new Error(`The request timed out after ${timeoutMs / 1000} seconds.`);
    }
    throw err;
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    if (payload?.detail) {
      if (Array.isArray(payload.detail)) {
        const messages = payload.detail
          .map((err: any) => err.msg || JSON.stringify(err))
          .filter(Boolean);
        if (messages.length > 0) {
          throw new Error(messages.join(", "));
        }
      } else if (typeof payload.detail === "string") {
        throw new Error(payload.detail);
      }
    }
    const message = payload?.message || "The request could not be completed.";
    throw new Error(typeof message === "string" ? message : "The request could not be completed.");
  }
  return payload as T;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetchWithTimeout(`${API_URL}/`, { method: "GET" }, 10000);
    if (!response.ok) return false;
    const data = await response.json().catch(() => null);
    return data?.status === "ok";
  } catch {
    return false;
  }
}

export async function analyzeSingle(text: string, rating?: number): Promise<ReviewResult> {
  const response = await fetchWithTimeout(`${API_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, rating: rating || null }),
  });
  return parseResponse<ReviewResult>(response);
}

export async function analyzeBatch(reviews: string[]): Promise<BatchResponse> {
  const response = await fetchWithTimeout(`${API_URL}/analyze-batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviews }),
  });
  return parseResponse<BatchResponse>(response);
}

export async function analyzeCsv(file: File): Promise<BatchResponse> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetchWithTimeout(`${API_URL}/analyze-csv`, { method: "POST", body });
  return parseResponse<BatchResponse>(response);
}

