<template><image :src="source" :style="{ width: `${size}px`, height: `${size}px`, flexShrink: 0, display: 'block' }" mode="aspectFit" aria-hidden="true" /></template>
<script setup>
import { computed } from 'vue';
const props = defineProps({ name: { type: String, default: 'home' }, size: { type: Number, default: 20 }, color: { type: String, default: '#3c538e' } });
const paths = {
  home: '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
  pig: '<path d="M5 9C6 5 16 4 19 9h2v5h-3l-2 4h-2v-2H9v2H7l-2-5H3V9z"/><path d="M10 8h4M15 5l2-2v4"/><circle cx="17" cy="10" r=".5"/>',
  history: '<path d="M3 10a9 9 0 1 1 2 8M3 4v6h6M12 7v5l3 2"/>',
  family: '<circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6M18 15a5 5 0 0 1 3 5v1"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  refresh: '<path d="M20 7A9 9 0 0 0 4 7l-1 3m0-6v6h6M4 17a9 9 0 0 0 16 0l1-3m0 6v-6h-6"/>',
  wallet: '<rect x="3" y="5" width="18" height="15" rx="3"/><path d="M3 9h18M16 13h5v4h-5a2 2 0 0 1 0-4zM5 5V3h13"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  spark: '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z"/>',
  edit: '<path d="m15 4 5 5M4 20l5-1L21 7a2 2 0 0 0-4-4L5 15z"/>',
};
const source = computed(() => `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="${props.color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${paths[props.name] || paths.home}</svg>`)}`);
</script>
