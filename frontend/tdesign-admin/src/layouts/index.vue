<template>
  <div>
    <template v-if="setting.layout.value === 'side'">
      <t-layout key="side" :class="mainLayoutCls">
        <t-aside><layout-side-nav /></t-aside>
        <t-layout>
          <t-header><layout-header /></t-header>
          <t-content><layout-content /></t-content>
        </t-layout>
      </t-layout>
    </template>

    <template v-else>
      <t-layout key="no-side">
        <t-header><layout-header /> </t-header>
        <t-layout :class="mainLayoutCls">
          <layout-side-nav />
          <layout-content />
        </t-layout>
      </t-layout>
    </template>
    <setting-com />
  </div>
</template>
<script setup lang="ts">
import '@/style/layout.less';

import { storeToRefs } from 'pinia';
import { computed, watch } from 'vue';
import { useRoute } from 'vue-router';

import { prefix } from '@/config/global';
import { useSettingStore, useTabsRouterStore, useUserStore } from '@/store';
import { businessContextSnapshot, businessTabKey } from '@/utils/route/tabIdentity';

import LayoutContent from './components/LayoutContent.vue';
import LayoutHeader from './components/LayoutHeader.vue';
import LayoutSideNav from './components/LayoutSideNav.vue';
import SettingCom from './setting.vue';

const route = useRoute();
const settingStore = useSettingStore();
const tabsRouterStore = useTabsRouterStore();
const userStore = useUserStore();
const setting = storeToRefs(settingStore);

const mainLayoutCls = computed(() => [
  {
    't-layout--with-sider': settingStore.showSidebar,
  },
]);

const appendNewRoute = () => {
  const {
    path,
    query,
    meta: { title },
    name,
  } = route;
  const titleObj = typeof title === 'string' ? { zh_CN: title, en_US: title } : title;
  tabsRouterStore.appendTabRouterList({
    path,
    query,
    tabKey: businessTabKey(path, query, userStore.businessContext),
    businessContext: businessContextSnapshot(userStore.businessContext),
    title: titleObj,
    name,
    isAlive: true,
    meta: route.meta,
  });
};

// Register the current business tab before TDesign Tabs renders. A late
// registration can make it select an older persisted tab and drop query context.
appendNewRoute();

watch(
  () => route.fullPath,
  () => {
    appendNewRoute();
    document.querySelector(`.${prefix}-layout`)?.scrollTo({ top: 0, behavior: 'smooth' });
  },
);
</script>
<style lang="less" scoped></style>
