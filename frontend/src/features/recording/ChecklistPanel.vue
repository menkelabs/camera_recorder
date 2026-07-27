<script setup lang="ts">
import type { ChecklistResponse } from '../../api/types'
import styles from './ChecklistPanel.module.css'

interface Props {
  checklist: ChecklistResponse | null
}

defineProps<Props>()
</script>

<template>
  <div :class="styles.panel">
    <template v-if="!checklist">
      <h3>Pre-Record Checklist</h3>
      <p :class="styles.muted">Checking cameras...</p>
    </template>
    <template v-else>
      <div :class="styles.head">
        <h3>Pre-Record Checklist</h3>
        <span :class="checklist.ready ? styles.ready : styles.notReady">
          {{ checklist.ready ? 'Ready' : 'Not Ready' }}
        </span>
      </div>
      <ul :class="styles.list">
        <li
          v-for="item in checklist.items || []"
          :key="item.id"
          :class="item.ok ? styles.ok : item.required ? styles.bad : styles.warn"
        >
          <span :class="styles.mark">
            <template v-if="item.ok">&#10003;</template>
            <template v-else>&#10007;</template>
          </span>
          <span><strong>{{ item.label }}</strong> &mdash; {{ item.detail }}</span>
        </li>
      </ul>
      <p v-if="checklist.usb_warning" :class="styles.usb">{{ checklist.usb_warning }}</p>
    </template>
  </div>
</template>
