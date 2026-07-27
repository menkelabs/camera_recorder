import type {
  AnalysisListItem,
  AnalysisResults,
  AnalysisScore,
  ArchiveConfig,
  ArchiveStatus,
  CameraProperties,
  ChecklistResponse,
  CompareResponse,
  PracticeSettings,
  ProgressResponse,
  RecordingsResponse,
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

  listRecordings: () => jsonFetch<RecordingsResponse>('/api/recordings'),
  deleteRecording: (ts: string) =>
    jsonFetch<{ deleted?: boolean; error?: string }>(`/api/recordings/${ts}`, {
      method: 'DELETE',
    }),
  bulkDeleteRecordings: (timestamps: string[]) =>
    jsonFetch<{ deleted_count: number }>('/api/recordings', {
      method: 'DELETE',
      body: JSON.stringify({ timestamps }),
    }),
  cleanupRecordings: (max_age_days: number) =>
    jsonFetch<{ deleted_count: number; cutoff_date: string }>(
      '/api/recordings/cleanup',
      { method: 'POST', body: JSON.stringify({ max_age_days }) },
    ),
  updateRecordingMeta: (
    ts: string,
    patch: { favorite?: boolean; notes?: string; tags?: string[] },
  ) =>
    jsonFetch<{ favorite: boolean; notes: string; tags: string[] }>(
      `/api/recordings/${ts}/meta`,
      { method: 'POST', body: JSON.stringify(patch) },
    ),
  setReference: (timestamp: string | null) =>
    jsonFetch<PracticeSettings>('/api/reference', {
      method: 'POST',
      body: JSON.stringify({ timestamp }),
    }),
  getReference: () =>
    jsonFetch<{
      reference_timestamp: string | null
      date?: string | null
      has_analysis?: boolean
    }>('/api/reference'),

  listAnalyses: () =>
    jsonFetch<{ analyses: AnalysisListItem[]; count: number; reference_timestamp?: string | null }>(
      '/api/analyses',
    ),
  compare: (a: string, b: string) =>
    jsonFetch<CompareResponse>(`/api/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`),
  progress: () => jsonFetch<ProgressResponse>('/api/progress'),

  archiveConfig: () => jsonFetch<ArchiveConfig>('/api/archive/config'),
  setArchiveConfig: (archive_path: string) =>
    jsonFetch<{ success: boolean; archive_path: string }>('/api/archive/config', {
      method: 'POST',
      body: JSON.stringify({ archive_path }),
    }),
  archiveStatus: () => jsonFetch<ArchiveStatus>('/api/archive/status'),
  archiveRun: (timestamps?: string[]) =>
    jsonFetch<{ archived_count?: number; results?: unknown[]; error?: string }>(
      '/api/archive/run',
      {
        method: 'POST',
        body: JSON.stringify(timestamps ? { timestamps } : {}),
      },
    ),
}

export function analysisFrameUrl(cameraNum: 1 | 2, index: number, bust = 0): string {
  return `/api/analysis/frame/${cameraNum}?index=${index}&_=${bust}`
}

export function formatPropValue(name: string, val: number): string {
  if (name === 'exposure') return Number(val).toFixed(1)
  if (name === 'white_balance') return `${Math.round(val)}K`
  return String(Math.round(val))
}
