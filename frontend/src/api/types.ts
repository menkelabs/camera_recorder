export type TabId =
  | 'camera1'
  | 'camera2'
  | 'recording'
  | 'recordings'
  | 'analysis'
  | 'compare'
  | 'progress'
  | 'settings'

export interface StatusResponse {
  cameras_available: boolean
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
  session_enabled?: boolean
  session_phase?: string
  session_count?: number
  camera_labels?: { camera1?: string; camera2?: string }
  recording_duration?: number
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
}

export interface CameraAnalysisBlock {
  summary: Record<string, number | null | undefined>
  detection_rate: number
  current: Record<string, number | string | null | undefined>
  timeseries: Record<string, Array<number | string | null | undefined>>
}
