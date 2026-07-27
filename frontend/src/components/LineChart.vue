<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import styles from './LineChart.module.css'

interface ChartSeries {
  label: string
  color: string
  /** Values aligned to the same x indices; nulls create gaps. */
  values: Array<number | null | undefined>
  dashed?: boolean
}

interface Props {
  series: ChartSeries[]
  labels?: string[]
  height?: number
  yLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  labels: () => [],
  height: 260,
  yLabel: undefined,
})

const canvasRef = ref<HTMLCanvasElement | null>(null)

function draw() {
  const canvas = canvasRef.value
  if (!canvas) return
  const parent = canvas.parentElement
  const width = parent?.clientWidth || 640
  const dpr = window.devicePixelRatio || 1
  canvas.width = Math.floor(width * dpr)
  canvas.height = Math.floor(props.height * dpr)
  canvas.style.width = `${width}px`
  canvas.style.height = `${props.height}px`

  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

  const pad = { top: 16, right: 12, bottom: 36, left: 48 }
  const plotW = width - pad.left - pad.right
  const plotH = props.height - pad.top - pad.bottom

  ctx.clearRect(0, 0, width, props.height)
  ctx.fillStyle = '#161b22'
  ctx.fillRect(0, 0, width, props.height)

  const all = props.series.flatMap((s) =>
    s.values.filter((v): v is number => v != null && Number.isFinite(v)),
  )
  if (all.length === 0 || plotW <= 0) {
    ctx.fillStyle = '#8b949e'
    ctx.font = '13px sans-serif'
    ctx.fillText('No data yet', pad.left, props.height / 2)
    return
  }

  let minY = Math.min(...all)
  let maxY = Math.max(...all)
  if (minY === maxY) {
    minY -= 1
    maxY += 1
  }
  const padY = (maxY - minY) * 0.08
  minY -= padY
  maxY += padY

  const n = Math.max(...props.series.map((s) => s.values.length), 1)
  const xAt = (i: number) => pad.left + (n <= 1 ? plotW / 2 : (i / (n - 1)) * plotW)
  const yAt = (v: number) => pad.top + ((maxY - v) / (maxY - minY)) * plotH

  ctx.strokeStyle = '#30363d'
  ctx.lineWidth = 1
  ctx.setLineDash([])
  for (let g = 0; g <= 4; g += 1) {
    const y = pad.top + (plotH * g) / 4
    ctx.beginPath()
    ctx.moveTo(pad.left, y)
    ctx.lineTo(pad.left + plotW, y)
    ctx.stroke()
    const val = maxY - ((maxY - minY) * g) / 4
    ctx.fillStyle = '#8b949e'
    ctx.font = '11px monospace'
    ctx.textAlign = 'right'
    ctx.fillText(val.toFixed(1), pad.left - 6, y + 4)
  }

  for (const s of props.series) {
    ctx.strokeStyle = s.color
    ctx.lineWidth = 2
    ctx.setLineDash(s.dashed ? [6, 4] : [])
    ctx.beginPath()
    let started = false
    s.values.forEach((v, i) => {
      if (v == null || !Number.isFinite(v)) {
        started = false
        return
      }
      const x = xAt(i)
      const y = yAt(v)
      if (!started) {
        ctx.moveTo(x, y)
        started = true
      } else {
        ctx.lineTo(x, y)
      }
    })
    ctx.stroke()

    ctx.setLineDash([])
    s.values.forEach((v, i) => {
      if (v == null || !Number.isFinite(v)) return
      ctx.fillStyle = s.color
      ctx.beginPath()
      ctx.arc(xAt(i), yAt(v), 3, 0, Math.PI * 2)
      ctx.fill()
    })
  }

  ctx.fillStyle = '#8b949e'
  ctx.font = '10px sans-serif'
  ctx.textAlign = 'center'
  const step = Math.max(1, Math.ceil(n / 6))
  for (let i = 0; i < n; i += step) {
    const label = props.labels[i] || String(i + 1)
    ctx.fillText(label.slice(5) || label, xAt(i), props.height - 12)
  }

  if (props.yLabel) {
    ctx.save()
    ctx.translate(12, pad.top + plotH / 2)
    ctx.rotate(-Math.PI / 2)
    ctx.textAlign = 'center'
    ctx.fillText(props.yLabel, 0, 0)
    ctx.restore()
  }
}

function scheduleDraw() {
  void nextTick(draw)
}

watch(() => props, scheduleDraw, { deep: true })

onMounted(() => {
  scheduleDraw()
  window.addEventListener('resize', scheduleDraw)
})

onUnmounted(() => {
  window.removeEventListener('resize', scheduleDraw)
})
</script>

<template>
  <div :class="styles.wrap">
    <canvas ref="canvasRef" />
    <div :class="styles.legend">
      <span v-for="item in series" :key="item.label" :class="styles.item">
        <i :style="{ background: item.color, borderStyle: item.dashed ? 'dashed' : 'solid' }" />
        {{ item.label }}
      </span>
    </div>
  </div>
</template>
