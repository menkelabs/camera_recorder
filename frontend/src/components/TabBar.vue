<script setup lang="ts">
import { TABS, useAppStore } from '../store/appStore'
import styles from './TabBar.module.css'

const appStore = useAppStore()
</script>

<template>
  <nav :class="styles.bar" role="tablist" aria-label="Main">
    <button
      v-for="tab in TABS"
      :key="tab.id"
      type="button"
      role="tab"
      :aria-label="`${tab.shortcut} ${tab.label}`"
      :aria-selected="appStore.tab === tab.id"
      :class="appStore.tab === tab.id ? styles.active : undefined"
      @click="appStore.setTab(tab.id)"
    >
      <span :class="styles.key">{{ tab.shortcut }}</span>
      {{ tab.label }}
    </button>
  </nav>
</template>
