<template>
  <section
    v-if="enabled"
    class="native-follower-manager"
    data-professional-collaboration-component="followers"
    data-semantic-component="ProfessionalFollowerManager"
    :data-state="loading ? 'loading' : error ? 'error' : 'ready'"
  >
    <div class="native-follower-header">
      <span class="native-follower-title">{{ label }}（{{ count }}）</span>
      <ScButton
        v-if="canFollow"
        size="small"
        :disabled="loading"
        :loading="loading"
        @click="emit('update', 'follow')"
      >{{ followLabel }}</ScButton>
      <ScButton
        v-else-if="canUnfollow"
        variant="ghost"
        size="small"
        :disabled="loading"
        :loading="loading"
        @click="emit('update', 'unfollow')"
      >{{ unfollowLabel }}</ScButton>
    </div>
    <ScInlineState v-if="error" state="error" :label="error" />
    <ScList v-else-if="items.length" class="native-follower-list" :items="items.map((item) => ({ ...item, key: String(item.partner_id) }))">
      <template #item="{ item }">
        <span class="native-follower-name">{{ item.name }}</span>
        <span v-if="item.is_current_user" class="native-follower-current">我</span>
      </template>
    </ScList>
    <ScInlineState v-else-if="!loading" state="empty" label="暂无关注者" />
  </section>
</template>

<script setup lang="ts">
import type { CollaborationFollower } from '../../api/chatter';
import ScButton from '../../components/design-system/ScButton.vue';
import ScInlineState from '../../components/design-system/ScInlineState.vue';
import ScList from '../../components/design-system/ScList.vue';

defineProps<{
  enabled: boolean;
  label: string;
  items: CollaborationFollower[];
  count: number;
  loading: boolean;
  error: string;
  canFollow: boolean;
  canUnfollow: boolean;
  followLabel: string;
  unfollowLabel: string;
}>();

const emit = defineEmits<{ update: [action: 'follow' | 'unfollow'] }>();
</script>

<style scoped src="./NativeCollaborationPanel.css"></style>
