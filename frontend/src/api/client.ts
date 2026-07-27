import type {
  AnalysisResults,
  AnalysisScore,
  CameraProperties,
  ChecklistResponse,
  PracticeSettings,
  SessionStatus,
  StatusResponse,
} from './types'

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  const data = (await resp.json().catch(() => ({}))) as T & { error?: string }
  if (!resp.ok) {
    throw new Error(data.error || resp.statusText)
  }
  return data
}

export const api = {
  status: () => jsonFetch<StatusResponse>('/api/status'),

  cameraProperties: (cam: 1 | 2) =>
    jsonFetch<CameraProperties>(`/api/camera/${cam}/properties`),
  setCameraProperty: (cam: 1 | 2, name: string, value: number) =>
    jsonFetch<{ success: boolean }>(`/api/camera/${cam}/property`, {
      method: 'POST',
      body: JSON.stringify({ name, value }),
    }),
  resetCamera: (cam: 1 | 2) =>
    jsonFetch<{ success: boolean }>(`/api/camera/${cam}/reset`, { method: 'POST' }),
  saveSettings: () =>
    jsonFetch<{ success?: boolean; filename?: string; error?: string }>(
      '/api/settings/save',
      { method: 'POST' },
    ),
  reinitCameras: (body?: { camera1_id?: number; camera2_id?: number }) =>
    jsonFetch<Record<string, unknown>>('/api/cameras/reinit', {
      method: 'POST',
      body: JSON.stringify(body || {}),
    }),
  detectCameras: () =>
    jsonFetch<{
      available_indices: number[]
      camera1_id: number
      camera2_id: number
      camera1_available: boolean
      camera2_available: boolean
    }>('/api/cameras/detect', { method: 'POST' }),

  checklist: () => jsonFetch<ChecklistResponse>('/api/checklist'),
  startRecording: () =>
    jsonFetch<{ success?: boolean; error?: string; checklist?: ChecklistResponse }>(
      '/api/recording/start',
      { method: 'POST' },
    ),
  stopRecording: () =>
    jsonFetch<{ success?: boolean; error?: string; duration?: number }>(
      '/api/recording/stop',
      { method: 'POST' },
    ),

  toggleAutoDetect: () =>
    jsonFetch<{
      enabled: boolean
      status?: Record<string, unknown>
      error?: string
      checklist?: ChecklistResponse
    }>('/api/auto-detect/toggle', { method: 'POST' }),

  sessionStatus: () => jsonFetch<SessionStatus>('/api/session'),
  setSessionEnabled: (enabled: boolean) =>
    jsonFetch<SessionStatus & { error?: string; checklist?: ChecklistResponse }>(
      '/api/session',
      { method: 'POST', body: JSON.stringify({ enabled }) },
    ),
  sessionNext: () =>
    jsonFetch<SessionStatus & { error?: string }>('/api/session/next', {
      method: 'POST',
    }),

  practiceSettings: () => jsonFetch<PracticeSettings>('/api/practice/settings'),
  updatePracticeSettings: (patch: Partial<PracticeSettings>) =>
    jsonFetch<PracticeSettings>('/api/practice/settings', {
      method: 'POST',
      body: JSON.stringify(patch),
    }),

  analysisResults: () => jsonFetch<AnalysisResults>('/api/analysis/results'),
  setAnalysisFrame: (index: number) =>
    jsonFetch<AnalysisResults>('/api/analysis/frame', {
      method: 'POST',
      body: JSON.stringify({ index }),
    }),
  analysisScore: () => jsonFetch<AnalysisScore>('/api/analysis/score'),
}

export function analysisFrameUrl(cameraNum: 1 | 2, index: number, bust = 0): string {
  return `/api/analysis/frame/${cameraNum}?index=${index}&_=${bust}`
}

export function formatPropValue(name: string, val: number): string {
  if (name === 'exposure') return Number(val).toFixed(1)
  if (name === 'white_balance') return `${Math.round(val)}K`
  return String(Math.round(val))
}
