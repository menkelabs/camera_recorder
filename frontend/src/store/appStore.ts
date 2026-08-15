import { defineStore } from 'pinia'
import type { StatusResponse, TabId } from '../api/types'

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

export const useAppStore = defineStore('app', {
  state: () => ({
    tab: 'recording' as TabId,
    status: null as StatusResponse | null,
    statusError: null as string | null,
    streamSession: 0,
    comparePrefill: null as { a?: string; b?: string } | null,
    analysisPrefill: null as string | null,
  }),
  actions: {
    setTab(tab: TabId) {
      this.tab = tab
    },
    setComparePrefill(prefill: { a?: string; b?: string } | null) {
      this.comparePrefill = prefill
    },
    setAnalysisPrefill(timestamp: string | null) {
      this.analysisPrefill = timestamp
    },
    setStatus(status: StatusResponse) {
      this.status = status
      this.statusError = null
    },
    setStatusError(msg: string | null) {
      this.statusError = msg
    },
    bumpStreamSession() {
      this.streamSession += 1
    },
  },
})
