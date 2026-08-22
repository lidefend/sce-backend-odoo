<template>
  <div class="profile-page">
    <section class="profile-header">
      <t-avatar size="72px">{{ avatarText }}</t-avatar>
      <div class="profile-header__identity">
        <h1>{{ accountName }}</h1>
        <p>{{ user.roleLabel || '内部用户' }}</p>
      </div>
      <t-tag theme="success" variant="light">当前已登录</t-tag>
    </section>

    <section class="profile-section">
      <div class="section-heading">
        <h2>账号信息</h2>
        <p>信息来自当前登录会话和系统初始化接口</p>
      </div>
      <t-descriptions :column="3" bordered>
        <t-descriptions-item label="姓名">{{ accountName }}</t-descriptions-item>
        <t-descriptions-item label="登录账号">{{ account?.login || '—' }}</t-descriptions-item>
        <t-descriptions-item label="用户 ID">{{ account?.id || '—' }}</t-descriptions-item>
        <t-descriptions-item label="所属公司">{{ companyName }}</t-descriptions-item>
        <t-descriptions-item label="语言">{{ account?.lang || '—' }}</t-descriptions-item>
        <t-descriptions-item label="时区">{{ account?.tz || '—' }}</t-descriptions-item>
        <t-descriptions-item label="邮箱">{{ account?.email || '—' }}</t-descriptions-item>
        <t-descriptions-item label="角色">{{ user.roleLabel || '—' }}</t-descriptions-item>
        <t-descriptions-item label="权限组数量">{{ roleGroups.length }}</t-descriptions-item>
      </t-descriptions>
    </section>

    <section class="profile-section">
      <div class="section-heading">
        <h2>当前业务范围</h2>
        <p>顶部切换器修改后，这里同步显示当前生效的数据范围</p>
      </div>
      <div class="scope-grid">
        <div class="scope-item">
          <span>公司</span><strong>{{ companyName }}</strong>
        </div>
        <div class="scope-item">
          <span>项目</span><strong>{{ projectName }}</strong>
        </div>
        <div class="scope-item">
          <span>经营方式</span><strong>{{ operationName }}</strong>
        </div>
      </div>
    </section>

    <section class="profile-section">
      <div class="section-heading">
        <h2>权限组</h2>
        <p>当前账号由后端返回的真实权限组</p>
      </div>
      <div v-if="roleGroups.length" class="role-list">
        <t-tag v-for="role in roleGroups" :key="role" variant="light">{{ role }}</t-tag>
      </div>
      <t-empty v-else description="当前账号未返回权限组" />
    </section>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue';

import { useUserStore } from '@/store';

type Dict = Record<string, any>;
const user = useUserStore();
const account = computed(() => user.account);
const context = computed(() => (user.recordContext || {}) as Dict);
const accountName = computed(() => account.value?.name || user.userInfo.name || account.value?.login || '当前用户');
const avatarText = computed(() => accountName.value.slice(0, 1).toUpperCase());
const companyName = computed(
  () =>
    context.value.company_name ||
    account.value?.company?.display_name ||
    account.value?.company?.name ||
    account.value?.company_name ||
    '全部公司',
);
const projectName = computed(
  () =>
    context.value.selected?.name || context.value.selected?.display_name || context.value.selected?.code || '全部项目',
);
const operationName = computed(
  () => context.value.operation_strategy_label || context.value.operation_strategy || '全部经营方式',
);
const roleGroups = computed(() => account.value?.groups_xmlids || user.userInfo.roles || []);
</script>
<style scoped>
.profile-page {
  display: grid;
  gap: 16px;
}

.profile-header,
.profile-section {
  padding: 24px;
  background: var(--td-bg-color-container);
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 6px;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 18px;
}

.profile-header__identity {
  flex: 1;
  min-width: 0;
}

.profile-header__identity h1,
.section-heading h2 {
  margin: 0;
  letter-spacing: 0;
}

.profile-header__identity h1 {
  font-size: 24px;
}

.profile-header__identity p,
.section-heading p {
  margin: 6px 0 0;
  color: var(--td-text-color-secondary);
  font-size: 13px;
}

.section-heading {
  margin-bottom: 20px;
}

.section-heading h2 {
  font-size: 18px;
}

.scope-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.scope-item {
  min-width: 0;
  padding: 16px;
  background: var(--td-bg-color-secondarycontainer);
  border-radius: 4px;
}

.scope-item span {
  display: block;
  margin-bottom: 8px;
  color: var(--td-text-color-secondary);
  font-size: 13px;
}

.scope-item strong {
  overflow-wrap: anywhere;
  font-size: 16px;
  font-weight: 500;
}

.role-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

@media (width <= 768px) {
  .profile-header {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .scope-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  :deep(.t-descriptions__body) {
    overflow-x: auto;
  }
}
</style>
