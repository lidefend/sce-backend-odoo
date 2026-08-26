<template>
  <ScPage class="page" data-semantic-component="NotFoundView" data-state="error">
    <ScPageHeader :title="pageIdentity.title.value" />
    <ScErrorState
      :title="pageIdentity.title.value"
      description="该页面或记录不存在，可能已被删除或链接已经失效。"
    >
      <template #actions><ScButton @click="returnSafely">返回安全页面</ScButton></template>
    </ScErrorState>
  </ScPage>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import ScButton from '../components/design-system/ScButton.vue';
import ScErrorState from '../components/design-system/ScErrorState.vue';
import ScPage from '../components/design-system/ScPage.vue';
import ScPageHeader from '../components/design-system/ScPageHeader.vue';
import { usePageIdentityRuntime } from '../app/pageIdentityRuntime';

const router = useRouter();
const pageIdentity = usePageIdentityRuntime();

function returnSafely(): void {
  void router.push('/');
}
</script>
