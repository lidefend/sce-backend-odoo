<template>
  <div class="activation-hint">
    <t-alert theme="info" message="系统账号由组织管理员创建。已有激活码时，请进入账号激活流程设置正式密码。" />
    <router-link to="/activate-account">
      <t-button block theme="primary">前往激活账号</t-button>
    </router-link>
  </div>
</template>
<script setup lang="ts">
defineEmits(['register-success']);
</script>
<style scoped>
.activation-hint {
  display: grid;
  gap: 18px;
}
</style>
