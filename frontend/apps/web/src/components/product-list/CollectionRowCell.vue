<template>
  <ScIconButton
    v-if="kind === 'favorite'"
    data-semantic-component="CollectionRowCell"
    type="button"
    class="favorite-toggle"
    appearance="favorite-toggle"
    :class="{ active: favoriteActive }"
    :disabled="disabled"
    :label="label"
    @click.stop="$emit('toggle-favorite')"
  >
    <ScIcon class="favorite-star" :name="favoriteActive ? 'star' : 'star-outline'" :size="16" />
  </ScIconButton>
  <span v-else-if="kind === 'status'" data-semantic-component="CollectionRowCell" class="status-badge" :class="`tone-${tone}`">
    {{ text }}
  </span>
  <div v-else-if="kind === 'primary'" data-semantic-component="CollectionRowCell" class="cell-primary">
    <ScButton type="button" class="cell-primary-link" appearance="auth-link" variant="ghost" size="small" @click.stop="$emit('open-record')">
      {{ text }}
    </ScButton>
    <div v-if="secondaryText" class="secondary">{{ secondaryText }}</div>
  </div>
  <span v-else-if="kind === 'attachments'" data-semantic-component="CollectionRowCell" class="attachment-links">
    <a
      v-for="link in links"
      :key="`${link.name}-${link.url}`"
      href="#"
      target="_blank"
      rel="noopener"
      @click.prevent.stop="$emit('open-attachment', link)"
    >
      {{ link.name }}
    </a>
  </span>
  <ScButton
    v-else-if="kind === 'attachment-count'"
    data-semantic-component="CollectionRowCell"
    type="button"
    class="attachment-count-link"
    appearance="auth-link"
    variant="ghost"
    size="small"
    @click.prevent.stop="$emit('open-attachment-count')"
  >
    {{ text }}
  </ScButton>
  <span v-else data-semantic-component="CollectionRowCell">{{ text }}</span>
</template>

<script setup lang="ts">
import ScIcon from '../design-system/ScIcon.vue';
import ScButton from '../design-system/ScButton.vue';
import ScIconButton from '../design-system/ScIconButton.vue';

export type CollectionRowCellKind = 'favorite' | 'status' | 'primary' | 'attachments' | 'attachment-count' | 'text';
export type CollectionAttachmentLink = { name: string; url: string };

withDefaults(defineProps<{
  kind: CollectionRowCellKind;
  text: string;
  tone?: string;
  label?: string;
  favoriteActive?: boolean;
  disabled?: boolean;
  secondaryText?: string;
  links?: CollectionAttachmentLink[];
}>(), {
  tone: 'neutral',
  label: '',
  favoriteActive: false,
  disabled: false,
  secondaryText: '',
  links: () => [],
});

defineEmits<{
  'toggle-favorite': [];
  'open-record': [];
  'open-attachment': [link: CollectionAttachmentLink];
  'open-attachment-count': [];
}>();
</script>

<style scoped src="./CollectionRowCell.css"></style>
