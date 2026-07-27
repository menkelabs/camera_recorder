import { create } from 'zustand'
import type { StatusResponse, TabId } from '../api/types'

interface AppState {
  tab: TabId
  status: StatusResponse | null
  statusError: string | null
  streamSession: number
  setTab: (tab: TabId) => void
  setStatus: (status: StatusResponse) => void
  setStatusError: (msg: string | null) => void
  bumpStreamSession: () => void
}

export const useAppStore = create<AppState>((set) => ({
  tab: 'recording',
  status: null,
  statusError: null,
  streamSession: 0,
  setTab: (tab) => set({ tab }),
  setStatus: (status) => set({ status, statusError: null }),
  setStatusError: (statusError) => set({ statusError }),
  bumpStreamSession: () => set((s) => ({ streamSession: s.streamSession + 1 })),
}))

export const TABS: { id: TabId; label: string; shortcut: string }[] = [
  { id: 'camera1', label: 'Camera 1', shortcut: '1' },
  { id: 'camera2', label: 'Camera 2', shortcut: '2' },
  { id: 'recording', label: 'Recording', shortcut: '3' },
  { id: 'recordings', label: 'Recordings', shortcut: '4' },
  { id: 'analysis', label: 'Analysis', shortcut: '5' },
  { id: 'compare', label: 'Compare', shortcut: '6' },
  { id: 'progress', label: 'Progress', shortcut: '7' },
  { id: 'settings', label: 'Settings', shortcut: '8' },
]
