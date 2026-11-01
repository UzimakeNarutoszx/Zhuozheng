<script setup>
import ImageMotion from './ImageMotion.vue'
defineProps({ item: Object })
const emit = defineEmits(['open'])
</script>
<template><article class="case-card"><ImageMotion :src="item.image" :alt="item.title" class-name="case-image" :motion="false" /><div><span class="eyebrow">CASE STUDY</span><h3>{{ item.title }}</h3><p>{{ item.caption }}</p><button class="text-link" @click="emit('open', item.methodId)">查看手法 <span>↗</span></button></div></article></template>
<style scoped>.case-card > .case-image { padding:0; aspect-ratio:1.2; }</style>
