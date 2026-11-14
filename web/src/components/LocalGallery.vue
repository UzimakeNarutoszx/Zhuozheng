<script setup>
import { computed, ref } from 'vue'
import { removeWork } from '../utils/local-work.js'
const props = defineProps({ works: Array })
const emit = defineEmits(['changed', 'edit'])
const items = computed(() => props.works || [])
const errorMessage = ref('')
function remove(id) {
  if (!window.confirm('确定删除这幅作品吗？删除后无法恢复。')) return
  try { emit('changed', removeWork(id)); errorMessage.value = '' } catch { errorMessage.value = '删除失败，请检查浏览器存储空间后重试' }
}
</script>
<template><p v-if="errorMessage" class="gallery-error" role="alert">{{ errorMessage }}</p><div v-if="items.length" class="local-gallery"><article v-for="work in items" :key="work.id" class="work-card"><img :src="work.thumbDataUrl || work.imageDataUrl" :alt="work.title" loading="lazy" decoding="async"><div><span class="eyebrow">LOCAL WORK</span><h3>{{ work.title }}</h3><p>{{ work.note || '一幅来自你的观察。' }}</p><div class="work-actions"><button class="text-link" @click="emit('edit', work)">继续编辑</button><button class="danger-link" @click="remove(work.id)">删除</button></div></div></article></div><div v-else class="empty-state"><span class="empty-mark">○</span><h3>还没有保存的作品</h3><p>去创作页上传一张照片，给它加上一扇取景窗。</p></div></template>
