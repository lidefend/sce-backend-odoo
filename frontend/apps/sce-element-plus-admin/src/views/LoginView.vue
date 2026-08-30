<template>
  <div class="login-page">
    <div class="login-visual">
      <div class="visual-content"><div class="visual-mark">SC</div><h1>工程管理平台</h1><p>让项目经营、成本控制与现场执行在同一套系统里协同运转。</p><div class="visual-stats"><span><strong>统一</strong><small>业务入口</small></span><span><strong>实时</strong><small>项目数据</small></span><span><strong>可追溯</strong><small>审批流程</small></span></div></div>
    </div>
    <div class="login-panel">
      <div class="login-card">
        <div class="mobile-brand"><div class="brand-mark">SC</div><strong>工程管理平台</strong></div>
        <h2>欢迎登录</h2><p class="login-caption">使用您的平台账号继续</p>
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
          <el-form-item label="账号" prop="account"><el-input v-model="form.account" size="large" placeholder="请输入账号" :prefix-icon="User" /></el-form-item>
          <el-form-item label="密码" prop="password"><el-input v-model="form.password" size="large" type="password" show-password placeholder="请输入密码" :prefix-icon="Lock" /></el-form-item>
          <div class="login-options"><el-checkbox v-model="remember">记住我</el-checkbox><el-button link type="primary">忘记密码？</el-button></div>
          <el-button type="primary" size="large" native-type="submit" :loading="loading" class="submit-button">登录</el-button>
        </el-form>
        <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon class="login-error" />
        <p class="login-hint">开发环境可使用默认测试账号，登录后页面将由后端契约决定。</p>
      </div>
      <div class="login-footer">Smart Construction Platform · Odoo 17</div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { useSessionStore } from '@/stores/session'

const router = useRouter(); const route = useRoute(); const session = useSessionStore()
const formRef = ref<FormInstance>(); const loading = ref(false); const error = ref(''); const remember = ref(true)
const form = reactive({ account: 'sc_test_admin', password: '123456' })
const rules: FormRules = { account: [{ required: true, message: '请输入账号', trigger: 'blur' }], password: [{ required: true, message: '请输入密码', trigger: 'blur' }] }
async function submit() { await formRef.value?.validate(async (valid) => { if (!valid) return; loading.value = true; error.value = ''; try { await session.login(form.account, form.password); ElMessage.success('登录成功'); await router.replace(String(route.query.redirect || '/dashboard')) } catch (cause) { error.value = cause instanceof Error ? cause.message : '登录失败' } finally { loading.value = false } }) }
</script>
<style scoped>
.login-page { min-height: 100vh; display: grid; grid-template-columns: minmax(420px, 1fr) minmax(440px, 520px); background: #fff; }
.login-visual { background: linear-gradient(145deg,#1d4ed8,#2563eb 55%,#0ea5e9); color: #fff; padding: clamp(48px,8vw,110px); display:flex; align-items:center; }
.visual-content { max-width: 530px; }.visual-mark,.mobile-brand .brand-mark { width: 44px;height:44px;border-radius:8px;display:grid;place-items:center;background:rgba(255,255,255,.18);font-weight:700;letter-spacing:.05em; }.visual-content h1 { margin: 22px 0 14px; font-size: clamp(32px,4vw,52px); letter-spacing: 0; }.visual-content p { margin:0; max-width:430px; line-height:1.8; font-size:16px; color:rgba(255,255,255,.82); }.visual-stats { display:flex; gap:46px; margin-top:74px; }.visual-stats span { display:grid; gap:5px; }.visual-stats strong { font-size:21px; }.visual-stats small { color:rgba(255,255,255,.68); }
.login-panel { display:flex; flex-direction:column; justify-content:center; padding:50px clamp(30px,7vw,88px); }.login-card { width:100%; max-width:350px; margin:auto; }.login-card h2 { margin:0 0 8px; font-size:30px; }.login-caption { margin:0 0 32px; color:#909399; }.mobile-brand { display:none; }.login-options { display:flex; justify-content:space-between; align-items:center; margin:-3px 0 22px; }.submit-button { width:100%; }.login-error { margin-top:18px; }.login-hint { margin-top:28px; color:#a8abb2; font-size:12px; line-height:1.6; }.login-footer { color:#c0c4cc; text-align:center; font-size:12px; }
@media (max-width: 800px) { .login-page { display:block; background:#f5f7fa; }.login-visual { display:none; }.login-panel { min-height:100vh; padding:32px 24px; }.login-card { background:#fff; padding:30px 24px; border-radius:8px; box-shadow:0 8px 30px rgba(31,35,41,.06); }.mobile-brand { display:flex; align-items:center; gap:10px; margin-bottom:34px; color:#303133; }.mobile-brand .brand-mark { color:#fff; background:var(--el-color-primary); width:34px;height:34px; }.login-footer { margin-top:26px; } }
</style>
