<template>
  <ScAside
    v-if="visible"
    :id="surfaceId"
    ref="surface"
    v-bind="$attrs"
    data-semantic-component="ProductMobileNavigationDrawer"
    :role="mobile ? 'dialog' : undefined"
    :aria-modal="mobile ? 'true' : undefined"
    :tabindex="mobile ? -1 : undefined"
    @keydown="onKeydown"
  >
    <slot />
  </ScAside>
  <ScButton
    v-if="mobile && visible"
    class="mobile-sidebar-backdrop"
    type="button"
    variant="ghost"
    aria-label="关闭导航遮罩"
    @click="emit('close')"
  />
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useModalLifecycle } from '../../composables/useModalLifecycle';
import ScButton from '../design-system/ScButton.vue';
import ScAside from '../design-system/ScAside.vue';

defineOptions({ inheritAttrs: false });

const props = withDefaults(defineProps<{
  visible: boolean;
  mobile: boolean;
  surfaceId?: string;
}>(), {
  surfaceId: 'primary-sidebar',
});

const emit = defineEmits<{ (event: 'close'): void }>();
const surface = ref<HTMLElement | null>(null);
const { onKeydown } = useModalLifecycle({
  open: () => props.mobile && props.visible,
  surface,
  close: () => emit('close'),
});
</script>
