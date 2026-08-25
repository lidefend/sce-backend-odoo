<template>
  <section
    v-if="enabled || pending.length"
    data-professional-collaboration-component="attachments"
    :data-attachment-readiness="enabled ? 'ready' : 'fail_closed'"
  >
    <section v-if="editable && enabled" class="native-attachment-tools" data-collaboration-capability="attachments">
      <label class="chip-btn native-attachment-upload">
        {{ uploading ? uploadingLabel : uploadLabel }}
        <input type="file" :disabled="uploading" @change="emit('selected', $event)" />
      </label>
      <p v-if="error" class="validation-error native-chatter-message">{{ error }}</p>
    </section>
    <ul v-if="pending.length" class="native-pending-attachments">
      <li v-for="item in pending" :key="item.key">
        <span>{{ item.name }}</span>
        <button class="ghost native-attachment-download" type="button" :disabled="uploading" @click="emit('remove', item.key)">移除</button>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
export type PendingProfessionalAttachment = { key: string; name: string; size: number; file: File };
defineProps<{ editable: boolean; enabled: boolean; uploading: boolean; uploadLabel: string; uploadingLabel: string; error: string; pending: PendingProfessionalAttachment[] }>();
const emit = defineEmits<{ selected: [event: Event]; remove: [key: string] }>();
</script>

<style scoped src="./NativeCollaborationPanel.css"></style>
