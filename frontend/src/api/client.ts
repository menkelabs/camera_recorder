import type { AnalysisResults, StatusResponse } from './types'

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  if (!resp.ok) {
    let detail = resp.statusText
    try {
      const body = await resp.json()
      detail = body.error || detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return resp.json() as Promise<T>
}

export const api = {
  status: () => jsonFetch<StatusResponse>('/api/status'),
  analysisResults: () => jsonFetch<AnalysisResults>('/api/analysis/results'),
  setAnalysisFrame: (index: number) =>
    jsonFetch<AnalysisResults>('/api/analysis/frame', {
      method: 'POST',
      body: JSON.stringify({ index }),
    }),
  startRecording: () =>
    jsonFetch<{ success?: boolean; error?: string }>('/api/recording/start', {
      method: 'POST',
    }),
  stopRecording: () =>
    jsonFetch<{ success?: boolean; error?: string }>('/api/recording/stop', {
      method: 'POST',
    }),
  checklist: () => jsonFetch<{ ready: boolean; items: unknown[] }>('/api/checklist'),
}

export function analysisFrameUrl(cameraNum: 1 | 2, index: number, bust = 0): string {
  return `/api/analysis/frame/${cameraNum}?index=${index}&_=${bust}`
}
