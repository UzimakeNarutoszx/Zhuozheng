<script setup>
import { computed } from 'vue'

const props = defineProps({ method: { type: Object, required: true } })
const notes = {
  frame: { title: '一扇窗，收住一园景。', steps: ['停步窗前', '窗洞取景', '远景入画'], caption: '窗的边界让目光有所取舍，也让窗外的景色成为画面。' },
  borrow: { title: '目光所至，越过园墙。', steps: ['园内停留', '越过边界', '借入远景'], caption: '园墙收住脚步，远处的树影与天空却可以继续延伸空间。' },
  opposition: { title: '隔水相望，彼此成景。', steps: ['此岸观景', '隔水呼应', '彼岸成景'], caption: '在此岸看彼岸，换一个位置，观看与被观看的关系也随之转换。' },
  leak: { title: '景不尽露，意在其间。', steps: ['靠近花墙', '透过漏窗', '窥见片景'], caption: '花格保留了遮挡，景物从疏密相间的开口中透露出来。' },
  screen: { title: '转过一重遮挡，景色才展开。', steps: ['入口收紧', '绕过遮挡', '豁然开朗'], caption: '先让视线停在近处，再随着行走，将后方的景色逐渐打开。' }
}
const note = computed(() => notes[props.method.id] || notes.frame)
</script>

<template>
  <figure class="composition-study">
    <div class="study-heading"><h3>{{ note.title }}</h3><span>构景示意 · 非实测</span></div>
    <svg class="study-drawing" viewBox="0 0 800 290" role="img" :aria-label="`${method.name}：${note.steps.join('，')}。${note.caption}`">
      <defs>
        <g id="study-pavilion" fill="none" stroke="currentColor" stroke-linejoin="round">
          <path d="M-65 0 Q-35-5 0-39 Q35-5 65 0 L45 6 H-45 Z" fill="var(--paper)" />
          <path d="M-43 7 V66 M43 7 V66 M-30 8 V64 M30 8 V64 M-49 66 H49 M-56 73 H56 M-29 51 H29 M0-39 V-48" />
        </g>
        <g id="study-tree" fill="none" stroke="currentColor" stroke-linecap="round">
          <path d="M0 75 Q7 25-4-29 M2 32 L-23 10 M3 17 L24-8" />
          <path d="M-25 18 C-68 15-58-20-35-26 C-49-56-12-70 7-51 C27-68 54-45 45-26 C78-7 42 29 20 15" />
        </g>
      </defs>
      <g class="study-landscape" stroke-width="1.6">
        <path class="water-wash" d="M38 219 Q180 190 333 212 T762 203 L762 263 Q560 250 400 266 T38 251Z" />
        <g fill="none" stroke="currentColor" opacity=".28">
          <path d="M45 218 Q175 196 297 215 M459 217 Q610 230 754 204 M108 244 Q260 230 365 244 M447 250 Q557 237 698 247" />
          <path d="M470 119 Q525 57 568 100 Q613 49 664 92 Q708 60 763 112" opacity=".55" />
        </g>
        <use href="#study-tree" transform="translate(689 137) scale(.82)" opacity=".5" />
        <use href="#study-pavilion" transform="translate(609 136) scale(.85)" />
        <path d="M534 202 Q603 194 679 204 L743 199" fill="none" stroke="currentColor" opacity=".5" />
        <template v-if="method.id === 'opposition'">
          <use href="#study-pavilion" transform="translate(167 130)" />
          <use href="#study-tree" transform="translate(79 132) scale(.65)" opacity=".45" />
          <path class="sight-line" d="M220 163 H558" />
          <path class="sight-arrow" d="M230 159 L220 163 L230 167 M548 159 L558 163 L548 167" />
        </template>
        <template v-else-if="method.id === 'frame' || method.id === 'leak'">
          <path class="wall-wash" d="M268 40 H453 V238 H268 Z M432 138 A72 72 0 1 0 288 138 A72 72 0 1 0 432 138" fill-rule="evenodd" />
          <g fill="none" stroke="currentColor" opacity=".65">
            <path d="M268 40 V238 M453 40 V238" />
            <circle cx="360" cy="138" r="72" />
            <circle cx="360" cy="138" r="78" opacity=".3" />
          </g>
          <g v-if="method.id === 'leak'" fill="none" stroke="currentColor" opacity=".55">
            <path d="M309 87 L411 189 M288 138 L360 210 M360 66 L432 138 M309 189 L411 87 M288 138 L360 66 M360 210 L432 138" />
          </g>
          <path class="sight-line" d="M137 163 L301 150 M420 143 L568 163" />
          <circle class="viewpoint" cx="128" cy="164" r="4" />
        </template>
        <template v-else-if="method.id === 'borrow'">
          <path class="wall-wash" d="M300 172 L448 192 V239 L300 219Z" />
          <path d="M300 172 L448 192 V239 M300 172 V219 M295 167 L453 188" fill="none" stroke="currentColor" opacity=".6" />
          <path class="sight-line" d="M137 181 L572 115" />
          <circle class="viewpoint" cx="128" cy="182" r="4" />
        </template>
        <template v-else>
          <path class="wall-wash" d="M302 72 L393 91 V219 L302 200Z" />
          <path d="M302 72 L393 91 V219 L302 200Z M296 65 L400 86" fill="none" stroke="currentColor" opacity=".6" />
          <path class="sight-line" d="M136 171 L295 151 M422 188 L568 162" />
          <path d="M191 216 Q241 254 355 247 T447 210" fill="none" stroke="var(--gold)" stroke-width="1.5" />
          <path class="sight-arrow" d="M441 215 L447 210 L448 219" />
          <circle class="viewpoint" cx="128" cy="172" r="4" />
        </template>
      </g>
    </svg>
    <ol class="study-stages"><li v-for="step in note.steps" :key="step">{{ step }}</li></ol>
    <figcaption>{{ note.caption }}</figcaption>
  </figure>
</template>

<style scoped>
.composition-study { margin:32px 0 26px; padding:30px 34px 24px; background:rgba(23,58,54,.025); color:var(--ink); }
.study-heading { display:flex; align-items:baseline; justify-content:space-between; gap:20px; }
.study-heading h3 { margin:0; font-size:clamp(19px,2.3vw,26px); font-weight:400; line-height:1.6; text-wrap:balance; }
.study-heading > span { flex-shrink:0; color:var(--ink-soft); font:10px/1.5 system-ui,sans-serif; letter-spacing:.04em; opacity:.7; }
.study-drawing { display:block; width:100%; height:auto; margin:14px 0 0; }
.water-wash { fill:var(--water); opacity:.22; }
.wall-wash { fill:var(--paper-deep); }
.sight-line { fill:none; stroke:var(--gold); stroke-width:1.5; stroke-dasharray:5 7; }
.sight-arrow { fill:none; stroke:var(--gold); stroke-width:1.5; }
.viewpoint { fill:var(--clay); }
.study-stages { display:grid; grid-template-columns:repeat(3,1fr); padding:0 0 22px; margin:0; list-style:none; border-bottom:1px solid rgba(23,58,54,.1); }
.study-stages li { text-align:center; color:var(--ink-soft); font-size:13px; letter-spacing:.08em; }
.composition-study figcaption { max-width:38em; margin:18px 0 0; color:var(--ink-soft); font-size:14px; line-height:1.85; text-wrap:pretty; }
@media(max-width:560px) {
  .composition-study { padding:22px 16px 20px; margin-top:24px; }
  .study-heading { display:block; }
  .study-heading > span { display:block; margin-top:6px; }
  .study-drawing { margin:20px -8px 12px; width:calc(100% + 16px); }
  .study-stages { padding-bottom:18px; }
  .study-stages li { font-size:12px; letter-spacing:0; }
  .composition-study figcaption { font-size:13px; }
}
</style>
