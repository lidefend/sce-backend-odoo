<template>
  <nav
    ref="navRef"
    class="form-section-navigation"
    aria-label="表单章节"
    :aria-describedby="hintId"
    data-form-section-navigation
    data-semantic-component="FormSectionNavigation"
    :data-overflow-before="hasMoreBefore || undefined"
    :data-overflow-after="hasMoreAfter || undefined"
  >
    <span :id="hintId" class="sc-visually-hidden">章节入口可横向滚动；当前章节会保持选中状态。</span>
    <div ref="trackRef" class="form-section-navigation__track" @scroll.passive="updateOverflow">
      <ScButton
        v-for="item in items"
        :key="item.key"
        type="button"
        variant="ghost"
        size="small"
        appearance="section-tab"
        :aria-current="activeKey === item.key ? 'location' : undefined"
        :data-section-link="item.key"
        :data-section-target="item.selector"
        @click="activate(item)"
      >{{ item.label }}</ScButton>
    </div>
    <span v-if="hasMoreBefore" class="form-section-navigation__cue form-section-navigation__cue--before" aria-hidden="true">‹</span>
    <span v-if="hasMoreAfter" class="form-section-navigation__cue form-section-navigation__cue--after" aria-hidden="true">滑动 ›</span>
  </nav>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue';
import ScButton from '../../components/design-system/ScButton.vue';

type SectionNavigationItem = { key: string; label: string; selector: string };

const props = defineProps<{ items: SectionNavigationItem[]; rootSelector: string }>();
const navRef = ref<HTMLElement | null>(null);
const trackRef = ref<HTMLElement | null>(null);
const activeKey = ref('');
const hasMoreBefore = ref(false);
const hasMoreAfter = ref(false);
const hintId = `form-section-navigation-${useId()}`;
let scrollOwner: HTMLElement | Window | null = null;
let resizeObserver: ResizeObserver | null = null;
let activeFrame = 0;
let activationReleaseTimer = 0;
let activatedKey = '';

function rootElement() {
  return navRef.value?.closest<HTMLElement>(props.rootSelector) || null;
}

function targetFor(item: SectionNavigationItem) {
  const matches = [...(rootElement()?.querySelectorAll<HTMLElement>(item.selector) || [])];
  return matches.find((candidate) => !matches.some((other) => other !== candidate && candidate.contains(other))) || matches[0] || null;
}

function visibleTarget(item: SectionNavigationItem) {
  const target = targetFor(item);
  return target && target.getClientRects().length ? target : null;
}

function updateOverflow() {
  const track = trackRef.value;
  if (!track) return;
  hasMoreBefore.value = track.scrollLeft > 2;
  hasMoreAfter.value = track.scrollLeft + track.clientWidth < track.scrollWidth - 2;
}

function centerActiveLink() {
  const track = trackRef.value;
  if (!track) return;
  const active = [...track.querySelectorAll<HTMLElement>('[data-section-link]')]
    .find((item) => item.dataset.sectionLink === activeKey.value);
  if (!active) return;
  const left = Math.max(0, active.offsetLeft - (track.clientWidth - active.offsetWidth) / 2);
  track.scrollTo({ left, behavior: 'auto' });
  updateOverflow();
}

function updateActiveSection() {
  activeFrame = 0;
  const visible = props.items.map((item) => ({ item, target: visibleTarget(item) })).filter((entry) => entry.target);
  if (!visible.length) return;
  const navBottom = navRef.value?.getBoundingClientRect().bottom || 0;
  const ownerTop = scrollOwner instanceof HTMLElement ? scrollOwner.getBoundingClientRect().top : 0;
  const anchor = Math.max(navBottom, ownerTop) + 12;
  const ownerAtBottom = scrollOwner instanceof HTMLElement
    ? scrollOwner.scrollTop + scrollOwner.clientHeight >= scrollOwner.scrollHeight - 2
    : window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2;
  const active = ownerAtBottom
    ? visible[visible.length - 1]
    : visible.reduce((current, entry) => ((entry.target?.getBoundingClientRect().top || 0) <= anchor ? entry : current), visible[0]);
  if (activeKey.value !== active.item.key) {
    activeKey.value = active.item.key;
    centerActiveLink();
  }
}

function queueActiveSection() {
  if (activatedKey) return;
  if (activeFrame) return;
  activeFrame = window.requestAnimationFrame(updateActiveSection);
}

function activate(item: SectionNavigationItem) {
  const target = visibleTarget(item);
  if (!target) return;
  activatedKey = item.key;
  if (activationReleaseTimer) window.clearTimeout(activationReleaseTimer);
  activeKey.value = item.key;
  target.setAttribute('tabindex', '-1');
  target.focus({ preventScroll: true });
  target.scrollIntoView({ behavior: 'auto', block: 'start' });
  centerActiveLink();
  activationReleaseTimer = window.setTimeout(() => {
    activatedKey = '';
    activationReleaseTimer = 0;
    queueActiveSection();
  }, 350);
}

function bindNavigation() {
  if (scrollOwner) scrollOwner.removeEventListener('scroll', queueActiveSection);
  scrollOwner = navRef.value?.closest<HTMLElement>('.router-host') || window;
  scrollOwner.addEventListener('scroll', queueActiveSection, { passive: true });
  activeKey.value = props.items.find(visibleTarget)?.key || '';
  void nextTick(() => {
    updateOverflow();
    updateActiveSection();
  });
}

onMounted(() => {
  resizeObserver = new ResizeObserver(() => {
    updateOverflow();
    queueActiveSection();
  });
  if (trackRef.value) resizeObserver.observe(trackRef.value);
  bindNavigation();
});
watch(() => props.items.map((item) => `${item.key}:${item.selector}`).join('|'), bindNavigation);
onBeforeUnmount(() => {
  if (scrollOwner) scrollOwner.removeEventListener('scroll', queueActiveSection);
  if (activeFrame) window.cancelAnimationFrame(activeFrame);
  if (activationReleaseTimer) window.clearTimeout(activationReleaseTimer);
  resizeObserver?.disconnect();
});
</script>

<style scoped>
.form-section-navigation {
  position: sticky;
  z-index: 18;
  top: var(--sc-form-command-bar-height, 72px);
  min-width: 0;
  overflow: hidden;
  border-bottom: 1px solid var(--sc-app-border);
  background: var(--sc-app-panel);
  isolation: isolate;
}
.form-section-navigation__track {
  display: flex;
  gap: 4px;
  min-width: 0;
  padding: 6px 52px 6px 0;
  overflow-x: auto;
  scrollbar-width: thin;
}
.form-section-navigation__track :deep(.sc-btn) { flex: 0 0 auto; }
.form-section-navigation__cue {
  position: absolute;
  z-index: 2;
  top: 50%;
  transform: translateY(-50%);
  color: var(--sc-app-text-secondary);
  font-size: 11px;
  font-weight: 600;
  line-height: 28px;
  pointer-events: none;
}
.form-section-navigation__cue--before {
  left: 0;
  padding: 0 12px 0 5px;
  background: linear-gradient(90deg, var(--sc-app-panel) 58%, transparent);
}
.form-section-navigation__cue--after {
  right: 0;
  padding: 0 5px 0 18px;
  background: linear-gradient(90deg, transparent, var(--sc-app-panel) 28%);
  white-space: nowrap;
}
@media (max-width: 560px) {
  .form-section-navigation__track { padding-block: 5px; }
}
</style>
