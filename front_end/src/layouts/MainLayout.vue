<template>
  <el-container class="layout-container">
    <!-- Sidebar (Desktop only) -->
    <el-aside :width="sidebarWidth" class="sidebar sidebar-desktop">
      <div class="sidebar-header">
        <div class="logo" @click="router.push('/')">
          <div class="logo-icon">
            <svg width="28" height="28" viewBox="0 0 40 40" fill="none">
              <rect width="40" height="40" rx="10" fill="url(#logo-grad)"/>
              <path d="M16 22L19 25L24 18" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
              <defs><linearGradient id="logo-grad" x1="0" y1="0" x2="40" y2="40"><stop stop-color="#5B7FFF"/><stop offset="1" stop-color="#3B5FFF"/></linearGradient></defs>
            </svg>
          </div>
          <transition name="fade"><span v-show="!isCollapsed" class="logo-text">个人记账本</span></transition>
        </div>
        <button class="collapse-btn" @click="toggleCollapse">
          <el-icon :class="{ rotated: isCollapsed }"><Fold /></el-icon>
        </button>
      </div>
      <el-menu :default-active="activeMenu" router :collapse="isCollapsed" :collapse-transition="false" class="sidebar-menu">
        <el-menu-item index="/records"><el-icon><List /></el-icon><template #title>账单记录</template></el-menu-item>
        <el-menu-item index="/categories"><el-icon><Collection /></el-icon><template #title>分类管理</template></el-menu-item>
        <el-menu-item index="/statistics"><el-icon><DataLine /></el-icon><template #title>数据统计</template></el-menu-item>
      </el-menu>
      <div class="sidebar-footer">
        <el-dropdown trigger="click" @command="handleCommand" placement="top-start">
          <div class="user-avatar">
            <div class="avatar-circle">{{ avatarText }}</div>
            <transition name="fade"><div v-show="!isCollapsed" class="avatar-info"><span class="avatar-name">{{ userStore.userInfo?.username || '用户' }}</span><span class="avatar-role">个人用户</span></div></transition>
            <transition name="fade"><el-icon v-show="!isCollapsed" class="arrow-icon"><ArrowDown /></el-icon></transition>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile"><el-icon><User /></el-icon>个人信息</el-dropdown-item>
              <el-dropdown-item command="password"><el-icon><Key /></el-icon>修改密码</el-dropdown-item>
              <el-dropdown-item divided command="logout"><el-icon><SwitchButton /></el-icon>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-aside>

    <!-- Main Area -->
    <el-container class="main-area">
      <el-header class="top-header">
        <div class="header-left">
          <el-breadcrumb separator="/" class="desktop-only-breadcrumb">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentPageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
          <span class="mobile-title mobile-only">{{ currentPageTitle }}</span>
        </div>
        <div class="header-right">
          <el-tooltip content="刷新" placement="bottom">
            <el-button circle class="action-btn" @click="refreshCurrent"><el-icon><Refresh /></el-icon></el-button>
          </el-tooltip>
          <el-dropdown trigger="click" @command="handleCommand" class="mobile-only user-mobile-dropdown">
            <el-button circle class="action-btn"><el-icon><MoreFilled /></el-icon></el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile"><el-icon><User /></el-icon>个人信息</el-dropdown-item>
                <el-dropdown-item command="password"><el-icon><Key /></el-icon>修改密码</el-dropdown-item>
                <el-dropdown-item divided command="logout"><el-icon><SwitchButton /></el-icon>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main-content"><router-view /></el-main>
    </el-container>

    <!-- Bottom Tab Bar (Mobile) -->
    <div class="bottom-tab-bar mobile-only">
      <div v-for="tab in tabs" :key="tab.path" :class="['tab-item', { active: activeMenu === tab.path }]" @click="router.push(tab.path)">
        <el-icon class="tab-icon"><component :is="tab.icon" /></el-icon>
        <span class="tab-label">{{ tab.label }}</span>
      </div>
    </div>

    <!-- Dialogs -->
    <el-dialog v-model="profileDialog" title="个人信息" width="90%" max-width="480px" top="10vh" destroy-on-close>
      <el-form label-width="70px" size="large">
        <el-form-item label="用户名"><el-input :model-value="userStore.userInfo?.username" disabled /></el-form-item>
        <el-form-item label="创建时间"><el-input :model-value="userStore.userInfo?.createTime" disabled /></el-form-item>
      </el-form>
      <template #footer><el-button @click="profileDialog = false">关闭</el-button></template>
    </el-dialog>
    <el-dialog v-model="passwordDialog" title="修改密码" width="90%" max-width="480px" top="10vh" destroy-on-close>
      <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="70px" size="large">
        <el-form-item label="原密码" prop="oldPassword"><el-input v-model="passwordForm.oldPassword" type="password" show-password placeholder="请输入原密码" /></el-form-item>
        <el-form-item label="新密码" prop="newPassword"><el-input v-model="passwordForm.newPassword" type="password" show-password placeholder="请输入新密码" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialog = false">取消</el-button>
        <el-button type="primary" :loading="passwordLoading" @click="handleChangePassword">确定</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { userApi } from '@/api'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  Fold, List, Collection, DataLine,
  ArrowDown, User, Key, SwitchButton, Refresh, MoreFilled
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isCollapsed = ref(false)
const profileDialog = ref(false)
const passwordDialog = ref(false)
const passwordLoading = ref(false)
const passwordFormRef = ref<FormInstance>()
const isMobile = ref(window.innerWidth < 768)

const sidebarWidth = computed(() => isCollapsed.value ? '64px' : '240px')
const activeMenu = computed(() => route.path)

const tabs = [
  { path: '/records', label: '账单', icon: 'List' },
  { path: '/categories', label: '分类', icon: 'Collection' },
  { path: '/statistics', label: '统计', icon: 'DataLine' }
]

const pageTitleMap: Record<string, string> = {
  '/records': '账单记录',
  '/categories': '分类管理',
  '/statistics': '数据统计'
}

const currentPageTitle = computed(() => pageTitleMap[route.path] || '')

const avatarText = computed(() => (userStore.userInfo?.username || '用').charAt(0).toUpperCase())

const passwordForm = ref({ oldPassword: '', newPassword: '' })

const passwordRules: FormRules = {
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 6, max: 20, message: '密码长度在6-20位之间', trigger: 'blur' }]
}

const toggleCollapse = () => { isCollapsed.value = !isCollapsed.value }

const handleCommand = (command: string) => {
  if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning', roundButton: true
    }).then(() => { userStore.logout(); router.push('/login') }).catch(() => {})
  } else if (command === 'profile') { profileDialog.value = true }
  else if (command === 'password') { passwordDialog.value = true }
}

const handleChangePassword = async () => {
  if (!passwordFormRef.value) return
  await passwordFormRef.value.validate(async (valid) => {
    if (!valid) return
    passwordLoading.value = true
    try {
      await userApi.updatePassword(passwordForm.value)
      ElMessage.success('密码修改成功，请重新登录')
      passwordDialog.value = false
      userStore.logout()
      router.push('/login')
    } catch {} finally { passwordLoading.value = false }
  })
}

const refreshCurrent = () => {
  const comp = route.matched[route.matched.length - 1]?.instances?.default
  if (comp && typeof (comp as any).refreshData === 'function') (comp as any).refreshData()
  else router.go(0)
}

const onResize = () => { isMobile.value = window.innerWidth < 768 }

onMounted(() => {
  if (userStore.token && !userStore.userInfo) userStore.fetchUserInfo()
  window.addEventListener('resize', onResize)
})
onUnmounted(() => { window.removeEventListener('resize', onResize) })
watch(passwordDialog, (val) => { if (!val) passwordForm.value = { oldPassword: '', newPassword: '' } })
</script>

<style scoped>
.layout-container { height: 100vh; overflow: hidden; }

/* Sidebar */
.sidebar {
  background: var(--bg-sidebar); display: flex; flex-direction: column;
  transition: width 0.3s; overflow: hidden; position: relative; z-index: 10;
  border-right: 1px solid rgba(255,255,255,.05);
}
.sidebar-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 14px; border-bottom: 1px solid rgba(255,255,255,.06); flex-shrink: 0; }
.logo { display: flex; align-items: center; gap: 10px; cursor: pointer; }
.logo-icon { flex-shrink: 0; }
.logo-icon svg { filter: drop-shadow(0 2px 6px rgba(91,127,255,.3)); }
.logo-text { font-size: 17px; font-weight: 700; color: #fff; background: linear-gradient(135deg,#fff 0%,#A5B4FC 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.collapse-btn { flex-shrink: 0; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border: none; background: rgba(255,255,255,.06); color: rgba(255,255,255,.5); border-radius: 6px; cursor: pointer; }
.collapse-btn .el-icon { transition: transform .3s; }
.collapse-btn .rotated { transform: rotate(180deg); }

.sidebar-menu { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 12px 8px; background: transparent !important; border-right: none !important; }
.sidebar-menu:not(.el-menu--collapse) { width: 240px; }
.sidebar-menu.el-menu--collapse { width: 64px; }
:deep(.sidebar-menu .el-menu-item) { height: 44px !important; line-height: 44px !important; border-radius: 8px !important; margin-bottom: 2px !important; color: rgba(255,255,255,.6) !important; background: transparent !important; }
:deep(.sidebar-menu .el-menu-item:hover) { background: rgba(255,255,255,.06) !important; color: rgba(255,255,255,.9) !important; }
:deep(.sidebar-menu .el-menu-item.is-active) { background: linear-gradient(135deg,rgba(91,127,255,.2),rgba(59,95,255,.1)) !important; color: var(--primary-light) !important; box-shadow: inset 3px 0 0 var(--primary); }

.sidebar-footer { flex-shrink: 0; padding: 12px; border-top: 1px solid rgba(255,255,255,.06); }
.user-avatar { display: flex; align-items: center; gap: 10px; cursor: pointer; padding: 8px; border-radius: 8px; }
.user-avatar:hover { background: rgba(255,255,255,.06); }
.avatar-circle { flex-shrink: 0; width: 36px; height: 36px; border-radius: 10px; background: var(--primary-gradient); display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 700; font-size: 15px; box-shadow: 0 2px 8px rgba(91,127,255,.3); }
.avatar-info { display: flex; flex-direction: column; }
.avatar-name { font-size: 13px; font-weight: 600; color: rgba(255,255,255,.85); }
.avatar-role { font-size: 11px; color: rgba(255,255,255,.35); }
.arrow-icon { margin-left: auto; color: rgba(255,255,255,.35); font-size: 12px; }

/* Main */
.main-area { display: flex; flex-direction: column; overflow: hidden; background: var(--bg-body); }
.top-header { flex-shrink: 0; height: 52px !important; background: rgba(255,255,255,.92); backdrop-filter: blur(12px); border-bottom: 1px solid var(--border-light); display: flex; align-items: center; justify-content: space-between; padding: 0 12px; position: sticky; top: 0; z-index: 5; }
:deep(.el-breadcrumb) { font-size: 14px; }
:deep(.el-breadcrumb__inner) { color: var(--text-tertiary) !important; font-weight: 400 !important; }
:deep(.el-breadcrumb__inner.is-link) { color: var(--text-secondary) !important; font-weight: 500 !important; }
:deep(.el-breadcrumb__inner.is-link:hover) { color: var(--primary) !important; }
.header-right { display: flex; align-items: center; gap: 4px; }
.action-btn { width: 34px !important; height: 34px !important; border: none !important; background: transparent !important; color: var(--text-tertiary) !important; font-size: 16px !important; }
.action-btn:active { background: var(--border-light) !important; color: var(--text-primary) !important; }
.main-content { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 16px; padding-bottom: calc(84px + env(safe-area-inset-bottom, 0px)); background: var(--bg-body); -webkit-overflow-scrolling: touch; }
@media (min-width: 768px) { .main-content { padding: 24px 28px; padding-bottom: 24px; } }

.mobile-title { font-size: 17px; font-weight: 700; color: var(--text-primary); }

/* Bottom Tab Bar */
.bottom-tab-bar { position: fixed; bottom: 0; left: 0; right: 0; height: calc(64px + env(safe-area-inset-bottom, 0px)); display: flex; align-items: center; justify-content: space-around; background: rgba(255,255,255,.96); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-top: 1px solid var(--border-light); z-index: 100; padding-bottom: env(safe-area-inset-bottom, 0px); box-shadow: 0 -1px 6px rgba(0,0,0,.04); }
.tab-item { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; padding: 4px 20px; min-width: 72px; height: 100%; cursor: pointer; -webkit-tap-highlight-color: transparent; user-select: none; transition: all .15s; border-radius: 0; position: relative; }
.tab-item::after { content: ''; position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 24px; height: 3px; border-radius: 0 0 3px 3px; background: var(--primary); opacity: 0; transition: opacity .2s; }
.tab-item.active::after { opacity: 1; }
.tab-item:active { background: var(--border-light); }
.tab-icon { font-size: 24px; color: var(--text-tertiary); transition: color .15s; }
.tab-label { font-size: 11px; font-weight: 500; color: var(--text-tertiary); transition: color .15s; letter-spacing: .3px; }
.tab-item.active .tab-icon, .tab-item.active .tab-label { color: var(--primary); }
.tab-item.active .tab-label { font-weight: 600; }

/* Responsive */
.desktop-only-breadcrumb { display: none; }
.mobile-only { display: flex; }
.sidebar-desktop { display: none; }
@media (min-width: 768px) {
  .desktop-only-breadcrumb { display: flex; }
  .mobile-only { display: none !important; }
  .sidebar-desktop { display: flex; }
  .main-content { padding: 24px 28px; padding-bottom: 24px; }
  .top-header { padding: 0 24px; }
}
.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
