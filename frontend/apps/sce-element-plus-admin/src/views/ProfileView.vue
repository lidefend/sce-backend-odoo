<template>
  <div class="profile-page">
    <div class="page-heading">
      <div>
        <el-breadcrumb>
          <el-breadcrumb-item @click="router.push('/dashboard')">工作台</el-breadcrumb-item>
          <el-breadcrumb-item>个人资料</el-breadcrumb-item>
        </el-breadcrumb>
        <div class="heading-title">
          <h1>个人资料</h1>
          <el-tag v-if="session.isAdmin" type="success" effect="light">管理员</el-tag>
        </div>
        <p>查看当前账号的身份与业务访问范围。</p>
      </div>
      <el-button :icon="ArrowLeft" @click="router.back()">返回</el-button>
    </div>

    <el-alert v-if="session.initError" :title="session.initError" type="warning" show-icon :closable="false" />

    <div class="profile-grid">
      <el-card shadow="never" class="profile-card profile-card--identity">
        <div class="identity-header">
          <el-avatar :size="72" class="profile-avatar">{{ initials }}</el-avatar>
          <div>
            <h2>{{ session.displayName }}</h2>
            <p>{{ user?.login || '未设置账号' }}</p>
          </div>
        </div>
        <div class="identity-tags">
          <el-tag v-if="user?.company_name" effect="plain">{{ user.company_name }}</el-tag>
          <el-tag :type="session.isAdmin ? 'success' : 'info'" effect="plain">{{ session.isAdmin ? '平台管理员' : '普通用户' }}</el-tag>
        </div>
        <el-divider />
        <div class="profile-note"><el-icon><InfoFilled /></el-icon><span>账号权限和公司范围由平台统一管理。如需变更，请联系系统管理员。</span></div>
      </el-card>

      <el-card shadow="never" class="profile-card">
        <template #header><span class="card-title">基本信息</span></template>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="登录账号">{{ user?.login || '—' }}</el-descriptions-item>
          <el-descriptions-item label="显示姓名">{{ user?.name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="电子邮箱">{{ user?.email || '—' }}</el-descriptions-item>
          <el-descriptions-item label="当前公司">{{ user?.company_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="用户编号">{{ user?.id || '—' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never" class="profile-card">
        <template #header><span class="card-title">角色与访问范围</span></template>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="账号角色">{{ roleLabel }}</el-descriptions-item>
          <el-descriptions-item label="管理员权限"><el-tag :type="session.isAdmin ? 'success' : 'info'" size="small">{{ session.isAdmin ? '是' : '否' }}</el-tag></el-descriptions-item>
          <el-descriptions-item label="可用公司"><div v-if="companies.length" class="tag-list"><el-tag v-for="company in companies" :key="company.id" size="small" effect="plain">{{ company.name }}</el-tag></div><span v-else>当前公司</span></el-descriptions-item>
          <el-descriptions-item label="可见菜单">{{ session.navigation.length }} 个一级菜单</el-descriptions-item>
        </el-descriptions>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, InfoFilled } from '@element-plus/icons-vue'
import { useSessionStore } from '@/stores/session'

const router = useRouter()
const session = useSessionStore()
const user = computed(() => session.user)
const initials = computed(() => session.displayName.trim().slice(0, 1).toUpperCase() || 'U')
const roleLabel = computed(() => String(session.roleSurface.role_label || session.roleSurface.primary_role_label || session.roleSurface.primary_role_code || (session.isAdmin ? '平台管理员' : '业务用户')))
const companies = computed(() => {
  const source = session.recordContext.company_options || session.user?.allowed_company_ids || []
  if (!Array.isArray(source)) return []
  return source.map((item: any) => typeof item === 'object' ? { id: String(item.company_id || item.id), name: String(item.company_name || item.name || item.display_name || item.company_id || item.id) } : { id: String(item), name: `公司 ${item}` })
})
</script>

<style scoped>
.profile-page { display: grid; gap: 18px; max-width: 1180px; margin: 0 auto; }
.page-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; }
.page-heading h1 { margin: 14px 0 6px; font-size: 25px; }
.page-heading p { margin: 0; color: var(--el-text-color-secondary); }
.heading-title { display: flex; align-items: center; gap: 10px; }
.profile-grid { display: grid; grid-template-columns: minmax(260px, .8fr) minmax(360px, 1.2fr); gap: 16px; }
.profile-card { border: 0; }
.profile-card--identity { grid-row: span 2; }
.identity-header { display: flex; align-items: center; gap: 16px; }
.profile-avatar { color: #fff; background: var(--el-color-primary); font-size: 28px; }
.identity-header h2 { margin: 0 0 6px; font-size: 22px; }
.identity-header p { margin: 0; color: var(--el-text-color-secondary); }
.identity-tags, .tag-list { display: flex; flex-wrap: wrap; gap: 7px; }
.identity-tags { margin-top: 20px; }
.card-title { font-weight: 600; }
.profile-note { display: flex; align-items: flex-start; gap: 8px; color: var(--el-text-color-secondary); font-size: 13px; line-height: 1.6; }
.profile-note .el-icon { flex: none; margin-top: 3px; color: var(--el-color-primary); }
@media (max-width: 800px) { .page-heading { align-items: flex-start; flex-direction: column; } .profile-grid { grid-template-columns: 1fr; } .profile-card--identity { grid-row: auto; } }
</style>
