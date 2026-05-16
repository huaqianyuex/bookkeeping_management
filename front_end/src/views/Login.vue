<template>
  <div class="login-page">
    <div class="login-bg">
      <div class="bg-shapes">
        <div class="shape shape-1"></div>
        <div class="shape shape-2"></div>
        <div class="shape shape-3"></div>
        <div class="shape shape-4"></div>
      </div>
    </div>
    <div class="login-container">
      <div class="login-brand">
        <div class="brand-icon">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
            <rect width="40" height="40" rx="12" fill="url(#brand-gradient)"/>
            <path d="M10 20C10 14.4772 14.4772 10 20 10C25.5228 10 30 14.4772 30 20C30 25.5228 25.5228 30 20 30C14.4772 30 10 25.5228 10 20Z" fill="white" fill-opacity="0.2"/>
            <path d="M16 22L19 25L24 18" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            <defs>
              <linearGradient id="brand-gradient" x1="0" y1="0" x2="40" y2="40">
                <stop stop-color="#5B7FFF"/>
                <stop offset="1" stop-color="#3B5FFF"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <h1 class="brand-title">个人记账本</h1>
        <p class="brand-subtitle">轻松管理每一笔收支</p>
      </div>
      <div class="login-card-wrapper">
        <div class="login-card">
          <div class="card-tabs">
            <button
              :class="['tab-btn', { active: activeTab === 'login' }]"
              @click="activeTab = 'login'"
            >
              登录
            </button>
            <button
              :class="['tab-btn', { active: activeTab === 'register' }]"
              @click="activeTab = 'register'"
            >
              注册
            </button>
          </div>
          <transition name="tab-fade" mode="out-in">
            <div key="login" v-if="activeTab === 'login'" class="form-container">
              <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" label-position="top" size="large">
                <el-form-item label="用户名" prop="username">
                  <el-input
                    v-model="loginForm.username"
                    placeholder="请输入用户名"
                    :prefix-icon="User"
                    clearable
                  />
                </el-form-item>
                <el-form-item label="密码" prop="password">
                  <el-input
                    v-model="loginForm.password"
                    type="password"
                    placeholder="请输入密码"
                    :prefix-icon="Lock"
                    show-password
                    @keyup.enter="handleLogin"
                  />
                </el-form-item>
                <el-form-item>
                  <el-button
                    type="primary"
                    :loading="loginLoading"
                    class="submit-btn"
                    @click="handleLogin"
                  >
                    {{ loginLoading ? '登录中...' : '登 录' }}
                  </el-button>
                </el-form-item>
              </el-form>
              <div class="form-footer">
                <span>还没有账号？</span>
                <a href="javascript:void(0)" @click="activeTab = 'register'">立即注册</a>
              </div>
            </div>
            <div key="register" v-else class="form-container">
              <el-form ref="registerFormRef" :model="registerForm" :rules="registerRules" label-position="top" size="large">
                <el-form-item label="用户名" prop="username">
                  <el-input
                    v-model="registerForm.username"
                    placeholder="请输入用户名"
                    :prefix-icon="User"
                    clearable
                  />
                </el-form-item>
                <el-form-item label="密码" prop="password">
                  <el-input
                    v-model="registerForm.password"
                    type="password"
                    placeholder="6-20位密码"
                    :prefix-icon="Lock"
                    show-password
                  />
                </el-form-item>
                <el-form-item label="确认密码" prop="confirmPassword">
                  <el-input
                    v-model="registerForm.confirmPassword"
                    type="password"
                    placeholder="请再次输入密码"
                    :prefix-icon="Lock"
                    show-password
                    @keyup.enter="handleRegister"
                  />
                </el-form-item>
                <el-form-item>
                  <el-button
                    type="primary"
                    :loading="registerLoading"
                    class="submit-btn"
                    @click="handleRegister"
                  >
                    {{ registerLoading ? '注册中...' : '注 册' }}
                  </el-button>
                </el-form-item>
              </el-form>
              <div class="form-footer">
                <span>已有账号？</span>
                <a href="javascript:void(0)" @click="activeTab = 'login'">立即登录</a>
              </div>
            </div>
          </transition>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { userApi } from '@/api'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref('login')
const loginLoading = ref(false)
const registerLoading = ref(false)
const loginFormRef = ref<FormInstance>()
const registerFormRef = ref<FormInstance>()

const loginForm = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (_rule: any, value: any, callback: any) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const loginRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const registerRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度在6-20位之间', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    loginLoading.value = true
    try {
      const res = await userApi.login(loginForm)
      const token = res.data
      if (!token) {
        ElMessage.error('登录失败：未获取到 Token')
        return
      }
      userStore.setToken(token)
      await userStore.fetchUserInfo()
      ElMessage.success('登录成功')
      router.push('/')
    } catch {
      // error handled by interceptor
    } finally {
      loginLoading.value = false
    }
  })
}

const handleRegister = async () => {
  if (!registerFormRef.value) return
  await registerFormRef.value.validate(async (valid) => {
    if (!valid) return
    registerLoading.value = true
    try {
      await userApi.register({
        username: registerForm.username,
        password: registerForm.password
      })
      ElMessage.success('注册成功，请登录')
      activeTab.value = 'login'
    } catch {
      // error handled by interceptor
    } finally {
      registerLoading.value = false
    }
  })
}
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #0F0F23;
}

/* Background */
.login-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.login-bg::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #1A1A3E 0%, #0F0F23 30%, #1A1A3E 60%, #0F0F23 100%);
}

.bg-shapes {
  position: absolute;
  inset: 0;
}

.shape {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.4;
  animation: float 20s ease-in-out infinite;
}

.shape-1 {
  width: 600px;
  height: 600px;
  background: linear-gradient(135deg, #5B7FFF, #3B5FFF);
  top: -200px;
  right: -100px;
  animation-delay: 0s;
}

.shape-2 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #7C3AED, #5B7FFF);
  bottom: -100px;
  left: -100px;
  animation-delay: -5s;
}

.shape-3 {
  width: 300px;
  height: 300px;
  background: linear-gradient(135deg, #5B7FFF, #06B6D4);
  top: 40%;
  left: -50px;
  animation-delay: -10s;
}

.shape-4 {
  width: 200px;
  height: 200px;
  background: linear-gradient(135deg, #A78BFA, #5B7FFF);
  bottom: 20%;
  right: -30px;
  animation-delay: -15s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(30px, -30px) scale(1.05); }
  50% { transform: translate(-20px, 20px) scale(0.95); }
  75% { transform: translate(20px, 30px) scale(1.02); }
}

/* Layout */
.login-container {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 80px;
  padding: 40px;
}

/* Brand */
.login-brand {
  text-align: center;
  color: #fff;
}

.brand-icon {
  margin-bottom: 16px;
  display: flex;
  justify-content: center;
}

.brand-icon svg {
  filter: drop-shadow(0 4px 12px rgba(91, 127, 255, 0.4));
}

.brand-title {
  font-size: 36px;
  font-weight: 700;
  letter-spacing: -0.5px;
  margin-bottom: 8px;
  background: linear-gradient(135deg, #fff 0%, #A5B4FC 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.brand-subtitle {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.6);
  letter-spacing: 0.5px;
}

/* Card */
.login-card-wrapper {
  width: 420px;
}

.login-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  padding: 36px 32px 32px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.3);
  transition: all var(--transition-normal);
}

.card-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 28px;
  padding: 4px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 10px;
}

.tab-btn {
  flex: 1;
  padding: 10px 0;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  border-radius: 8px;
  transition: all var(--transition-fast);
  font-family: inherit;
}

.tab-btn.active {
  background: var(--primary-gradient);
  color: #fff;
  box-shadow: 0 2px 8px rgba(91, 127, 255, 0.3);
}

.tab-btn:hover:not(.active) {
  color: rgba(255, 255, 255, 0.8);
}

/* Form */
.form-container {
  min-height: 280px;
}

:deep(.el-form-item) {
  margin-bottom: 22px;
}

:deep(.el-form-item__label) {
  color: rgba(255, 255, 255, 0.85) !important;
  font-weight: 500 !important;
  font-size: 13px !important;
  padding-bottom: 6px !important;
}

:deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.08) !important;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.12) inset !important;
  border-radius: 10px !important;
  padding: 2px 16px !important;
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px rgba(91, 127, 255, 0.4) inset !important;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(91, 127, 255, 0.3) inset !important;
}

:deep(.el-input__inner) {
  color: #fff !important;
  height: 42px !important;
}

:deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.35) !important;
}

:deep(.el-input__prefix) {
  color: rgba(255, 255, 255, 0.4) !important;
}

:deep(.el-icon.el-input__icon) {
  color: rgba(255, 255, 255, 0.4) !important;
}

.submit-btn {
  width: 100% !important;
  height: 44px !important;
  font-size: 16px !important;
  font-weight: 600 !important;
  border-radius: 10px !important;
  letter-spacing: 2px;
  margin-top: 4px;
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(91, 127, 255, 0.4);
}

.form-footer {
  text-align: center;
  margin-top: 20px;
  color: rgba(255, 255, 255, 0.4);
  font-size: 14px;
}

.form-footer a {
  color: var(--primary-light);
  font-weight: 500;
  margin-left: 4px;
}

.form-footer a:hover {
  color: #fff;
  text-decoration: underline;
}

/* Tab transition */
.tab-fade-enter-active,
.tab-fade-leave-active {
  transition: all 0.25s ease;
}

.tab-fade-enter-from {
  opacity: 0;
  transform: translateX(10px);
}

.tab-fade-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

/* Responsive */
@media (max-width: 768px) {
  .login-container {
    flex-direction: column;
    gap: 40px;
    padding: 24px;
    width: 100%;
  }

  .login-brand {
    margin-top: 20px;
  }

  .brand-title {
    font-size: 28px;
  }

  .login-card-wrapper {
    width: 100%;
    max-width: 420px;
  }
}
</style>
