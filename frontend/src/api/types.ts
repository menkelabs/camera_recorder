export type TabId =
  | 'camera1'
  | 'camera2'
  | 'recording'
  | 'recordings'
  | 'analysis'
  | 'compare'
  | 'progress'
  | 'settings'

export interface SessionStatus {
  enabled: boolean
  phase: string
  count: number
}

export interface AutoDetectStatus {
  state?: string
  delta?: number | null
  motion_threshold?: number
  current_turn?: number | null
  [key: string]: unknown
}

export interface MetronomeSettings {
  enabled: boolean
  bpm: number
  ratio?: string
}

export interface PracticeSettings {
  version?: number
  reference_timestamp?: string | null
  camera_roles?: { camera1?: string; camera2?: string }
  metronome?: MetronomeSettings
  session?: { enabled?: boolean; auto_detect?: boolean; auto_advance?: boolean }
  camera_labels?: { camera1?: string; camera2?: string }
}

export interface StatusResponse {
  cameras_available: boolean
  camera1_available?: boolean
  camera2_available?: boolean
  is_recording: boolean
  is_analyzing: boolean
  fps: number
  width?: number
  height?: number
  camera1_id?: number
  camera2_id?: number
  status_message?: string
  analysis_progress?: string
  analysis_error?: string
  auto_detect_enabled?: boolean
  auto_detect_status?: AutoDetectStatus
  session?: SessionStatus
  camera_labels?: { camera1?: string; camera2?: string }
  practice?: PracticeSettings
  recording_duration?: number
  recording_files?: string[]
}

export interface ChecklistItem {
  id: string
  label: string
  ok: boolean
  detail: string
  required?: boolean
}

export interface ChecklistResponse {
  ready: boolean
  items: ChecklistItem[]
  usb_warning?: string | null
  camera_labels?: { camera1?: string; camera2?: string }
  width?: number
  height?: number
  fps?: number
  error?: string
}

export interface CameraProp {
  value: number
  min: number
  max: number
  default: number
  step: number
}

export type CameraProperties = Record<string, CameraProp> & {
  _info?: { width: number; height: number; fps: number }
  error?: string
}

export interface AnalysisResults {
  is_analyzing: boolean
  progress?: string
  analysis_error?: string
  frame_index: number
  max_frames: number
  has_frames: boolean
  camera1: CameraAnalysisBlock | null
  camera2: CameraAnalysisBlock | null
  score?: AnalysisScore | null
}

export interface CameraAnalysisBlock {
  summary: Record<string, number | null | undefined>
  detection_rate: number
  current: Record<string, number | string | null | undefined>
  timeseries: Record<string, Array<number | string | null | undefined>>
}

export interface AnalysisScore {
  score?: number | null
  grade?: string | null
  strengths?: string[]
  focus?: string[]
  breakdown?: Record<string, unknown>
}

export const PROP_ORDER = [
  'brightness',
  'contrast',
  'saturation',
  'exposure',
  'gain',
  'focus',
  'white_balance',
  'sharpness',
  'gamma',
] as const
