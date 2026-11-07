/** Map a 0–1 playhead onto each swing's phase labels so both videos hit the same phase together. */

export const SWING_PHASES = [
  'Address',
  'Backswing',
  'Top',
  'Downswing',
  'Impact',
  'Follow-through',
] as const

interface PhaseSpan {
  name: string
  start: number
  end: number
}

function groupPhases(phases: string[]): PhaseSpan[] {
  const groups: PhaseSpan[] = []
  phases.forEach((name, index) => {
    const last = groups[groups.length - 1]
    if (last && last.name === name) last.end = index + 1
    else groups.push({ name, start: index, end: index + 1 })
  })
  return groups
}

export function frameIndexForPhase(phases: string[], progress: number): number {
  const count = phases.length
  if (count === 0) return 0
  const t = Math.min(1, Math.max(0, progress))
  if (t >= 1) return count - 1
  const groups = groupPhases(phases)
  const known = groups.filter((group) => (SWING_PHASES as readonly string[]).includes(group.name))
  const use = known.length ? known : groups
  const slot = t * use.length
  const index = Math.min(use.length - 1, Math.floor(slot))
  const span = use[index]
  const last = Math.max(span.start, span.end - 1)
  return Math.round(span.start + (slot - index) * (last - span.start))
}

export function phaseNameAt(phases: string[], progress: number): string {
  if (!phases.length) return ''
  return phases[frameIndexForPhase(phases, progress)] || ''
}

export function videoTimeForPhase(
  phases: string[],
  progress: number,
  duration: number,
  stride = 1,
  sourceFps = 0,
): number {
  if (!Number.isFinite(duration) || duration <= 0) return 0
  const index = frameIndexForPhase(phases, progress)
  if (sourceFps > 0 && stride > 0 && phases.length > 0) {
    return Math.min(duration, (index * stride) / sourceFps)
  }
  const denom = Math.max(phases.length - 1, 1)
  return Math.min(duration, (index / denom) * duration)
}
