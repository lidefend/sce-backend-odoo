<template>
  <section
    v-if="enabled || pending.length"
    data-professional-collaboration-component="attachments"
    data-semantic-component="ProfessionalAttachmentManager"
    :data-state="uploading ? 'loading' : enabled ? 'ready' : 'fail-closed'"
    :data-attachment-readiness="enabled ? 'ready' : 'fail_closed'"
  >
    <section v-if="editable && enabled" class="native-attachment-tools" data-collaboration-capability="attachments">
      <ScFileField
        class="native-attachment-upload"
        :disabled="uploading"
        :choose-label="uploading ? uploadingLabel : uploadLabel"
        empty-label=""
        @change="emit('selected', $event)"
      />
      <ScInlineState v-if="error" class="validation-error native-chatter-message" state="error" :label="error" />
    </section>
    <ul v-if="pending.length" class="native-pending-attachments">
      <li v-for="item in pending" :key="item.key">
        <span>{{ item.name }}</span>
        <ScButton variant="ghost" size="small" class="native-attachment-download" :disabled="uploading" @click="emit('remove', item.key)">移除</ScButton>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import ScButton from '../../components/design-system/ScButton.vue';
import ScFileField from '../../components/design-system/ScFileField.vue';
import ScInlineState from '../../components/design-system/ScInlineState.vue';
export type PendingProfessionalAttachment = { key: string; name: string; size: number; file: File };
defineProps<{ editable: boolean; enabled: boolean; uploading: boolean; uploadLabel: string; uploadingLabel: string; error: string; pending: PendingProfessionalAttachment[] }>();
const emit = defineEmits<{ selected: [event: Event]; remove: [key: string] }>();
</script>

<style scoped src="./NativeCollaborationPanel.css"></style>
