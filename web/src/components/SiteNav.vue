<script setup>
import { assetUrl } from '../utils/assets.js'
defineProps({ current: String })
const emit = defineEmits(['navigate'])
const items = [{ id: 'home', label: '游园' }, { id: 'methods', label: '手法' }, { id: 'studio', label: '创作' }, { id: 'community', label: '园友' }, { id: 'ask', label: '梅梅问答' }, { id: 'mine', label: '我的' }]
</script>
<template><header class="site-nav"><button class="brand" @click="emit('navigate', 'home')"><img class="brand-icon" :src="assetUrl('/garden-mark-64.png')" alt=""><span>邂逅拙政巧景，若见江南芳华</span></button><nav aria-label="主导航"><button v-for="item in items" :key="item.id" :class="{ active: current === item.id || (current === 'login' && item.id === 'mine') }" :aria-current="current === item.id ? 'page' : undefined" @click="emit('navigate', item.id)">{{ item.label }}</button></nav></header></template>
<style scoped>
.site-nav nav { min-width:0; flex-wrap:wrap; }
@media (max-width:700px) { .site-nav { height:auto; min-height:76px; padding:14px 20px 10px; flex-direction:column; align-items:flex-start; gap:8px; } .site-nav nav { width:100%; justify-content:space-between; gap:2px; } .site-nav nav button { padding:8px 5px; white-space:nowrap; } .brand { font-size:13px; } }
</style>
