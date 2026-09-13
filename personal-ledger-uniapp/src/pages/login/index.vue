<template>
	<view class="container">
		<!-- 设计稿01 品牌区：黄色圆角 Logo + 品牌名 + slogan -->
		<view class="brand">
			<view class="brand-logo">
				<text class="brand-logo-icon">🧾</text>
			</view>
			<text class="brand-name">简记</text>
			<text class="brand-slogan">简单记录每一笔</text>
		</view>

		<view class="form-card">
			<view class="input-group">
				<input
					class="input"
					v-model="username"
					placeholder="请输入用户名"
					placeholder-class="placeholder"
				/>
			</view>

			<view class="input-group">
				<input
					class="input"
					v-model="password"
					placeholder="请输入密码"
					placeholder-class="placeholder"
					:password="true"
				/>
			</view>

			<button
				class="btn-primary"
				:loading="submitting"
				:disabled="submitting"
				@click="handleLogin"
			>
				登录
			</button>

			<view class="link" @click="goRegister">
				<text class="link-text">还没有账号？</text>
				<text class="link-highlight">立即注册</text>
			</view>
		</view>

		<!-- 设计稿01 底部协议文案（静态展示） -->
		<view class="agreement">
			<text class="agreement-text">登录即代表同意《用户协议》和《隐私政策》</text>
		</view>
	</view>
</template>

<script>
import { login } from '../../api/user'
import { useUserStore } from '../../utils/store'

export default {
	data() {
		return {
			username: '',
			password: '',
			submitting: false,
		}
	},
		onLoad() {
			// 已登录则直接跳主页，避免在登录页卡住
			const token = uni.getStorageSync('token')
			console.log('[Login] onLoad, token存在:', !!token, ', token值:', token ? token.substring(0, 20) + '...' : '无')
			if (token) {
				console.log('[Login] 检测到已有token，自动跳转到 dashboard')
				uni.reLaunch({ url: '/pages/dashboard/index' })
			}
		},
		methods: {
			async handleLogin() {
				console.log('[Login] handleLogin 被调用, username:', this.username, ', password长度:', this.password?.length)
				if (!this.username || !this.password) {
					uni.showToast({ title: '请输入用户名和密码', icon: 'none' })
					return
				}
				this.submitting = true
				console.log('[Login] 开始请求登录接口...')
				try {
					const res = await login({
						username: this.username,
						password: this.password
					})
					console.log('[Login] 登录接口返回:', JSON.stringify(res))
					if (res.code === 200) {
						console.log('[Login] 登录成功，设置 token...')
						const store = useUserStore()
						store.setToken(res.data?.token || '')
						console.log('[Login] 获取用户信息...')
						await store.fetchUserInfo()
						console.log('[Login] 跳转到 dashboard...')
						uni.reLaunch({ url: '/pages/dashboard/index' })
					} else {
						console.log('[Login] 登录失败:', res.message)
						uni.showToast({ title: res.message || '登录失败', icon: 'none' })
					}
				} catch (e) {
					console.error('[Login] 登录异常:', e)
					uni.showToast({ title: e?.message || '网络连接失败', icon: 'none' })
				} finally {
					this.submitting = false
				}
			},
		goRegister() {
			uni.navigateTo({ url: '/pages/register/index' })
		}
	}
}
</script>

<style scoped>
.container {
	min-height: 100vh;
	background-color: var(--color-bg);
	display: flex;
	flex-direction: column;
	justify-content: center;
	padding: 80rpx var(--space-3xl);
}

/* ── 品牌区（设计稿01：黄色圆角 Logo 居中 + 品牌名 + slogan） ── */
.brand {
	display: flex;
	flex-direction: column;
	align-items: center;
	margin-bottom: 80rpx;
}

.brand-logo {
	width: 152rpx;
	height: 152rpx;
	border-radius: 40rpx;
	background-color: var(--color-accent);
	display: flex;
	align-items: center;
	justify-content: center;
	box-shadow: var(--shadow-accent);
	margin-bottom: var(--space-xl);
}

.brand-logo-icon {
	font-size: 76rpx;
	line-height: 1;
}

.brand-name {
	font-size: 56rpx;
	font-weight: var(--weight-extrabold);
	color: var(--color-text-heading);
	line-height: var(--leading-tight);
	margin-bottom: var(--space-sm);
}

.brand-slogan {
	font-size: var(--font-md);
	color: var(--color-text-secondary);
}

/* ── 表单区（设计稿01：无边框灰底圆角输入） ── */
.form-card {
	background-color: transparent;
	border-radius: var(--radius-lg);
	padding: 0;
	border: none;
}

.input-group {
	margin-bottom: var(--space-lg);
}

.input {
	height: 104rpx;
	border: none;
	border-radius: var(--radius-lg);
	padding: 0 var(--space-xl);
	font-size: var(--font-base);
	color: var(--color-text);
	background-color: var(--color-surface-raised);
	transition: background-color var(--transition-fast);
}

/* 输入框激活效果用 focus 伪类的话 uni-app 支持有限，靠原生 */
.input:focus {
	background-color: var(--color-divider);
}

.placeholder {
	color: var(--color-text-tertiary);
	font-size: var(--font-base);
}

/* ── 登录按钮（设计稿01：黑色胶囊大按钮） ── */
.btn-primary {
	margin-top: var(--space-xl);
	height: 104rpx;
	line-height: 104rpx;
	background-color: var(--color-primary);
	color: var(--color-text-inverse);
	font-size: var(--font-lg);
	font-weight: var(--weight-semibold);
	border-radius: var(--radius-full);
	border: none;
	box-shadow: var(--shadow-primary);
	transition: opacity var(--transition-fast);
}

.btn-primary::after {
	border: none;
}

.btn-primary:active {
	opacity: 0.88;
}

.btn-primary[disabled] {
	opacity: 0.5;
	box-shadow: none;
}

/* ── 注册链接 ── */
.link {
	text-align: center;
	margin-top: var(--space-2xl);
}

.link-text {
	font-size: var(--font-sm);
	color: var(--color-text-secondary);
}

.link-highlight {
	font-size: var(--font-sm);
	color: var(--color-text);
	font-weight: var(--weight-semibold);
	margin-left: var(--space-xs);
}

/* ── 底部协议文案（设计稿01） ── */
.agreement {
	position: fixed;
	left: 0;
	right: 0;
	bottom: calc(env(safe-area-inset-bottom) + 32rpx);
	text-align: center;
}

.agreement-text {
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
}
</style>
