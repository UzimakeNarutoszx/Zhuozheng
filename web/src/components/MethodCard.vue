<script setup>
import ImageMotion from './ImageMotion.vue'
defineProps({ method: Object })
const emit = defineEmits(['open'])
</script>
<template><button class="method-card" :class="`method-card--${method.id}`" @click="emit('open', method.id)"><ImageMotion :src="method.image" :alt="method.imageAlt" class-name="method-motion" :motion="false" :retryable="false" /><span class="method-index">{{ method.pinyin }}</span><strong>{{ method.name }}</strong><span>{{ method.summary }}</span><span class="card-arrow">进入观察 <span>↗</span></span></button></template>
