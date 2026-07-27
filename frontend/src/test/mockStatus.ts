import type { StatusResponse } from '../api/types'

export function mockStatus(overrides: Partial<StatusResponse> = {}): StatusResponse {
  return {
    cameras_available: true,
    camera1_available: true,
    camera2_available: true,
    is_recording: false,
    is_analyzing: false,
    fps: 120,
    width: 1280,
    height: 720,
    camera1_id: 0,
    camera2_id: 1,
    auto_detect_enabled: false,
    camera_labels: { camera1: 'Face-On', camera2: 'Down-the-Line' },
    ...overrides,
  }
}
