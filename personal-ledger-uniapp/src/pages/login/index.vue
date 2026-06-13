<template>
	<view class="container">
		<view class="header">
			<text class="title">个人记账本</text>
			<text class="subtitle">记录每一笔收支</text>
		</view>

		<view class="form-card">
			<view class="input-group">
				<text class="label">用户名</text>
				<input
					class="input"
					v-model="username"
					placeholder="请输入用户名"
					placeholder-class="placeholder"
				/>
			</view>

			<view class="input-group">
				<text class="label">密码</text>
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
		if (token) {
			uni.switchTab({ url: '/pages/dashboard/index' })
		}
	},
	methods: {
		async handleLogin() {
			if (!this.username || !this.password) {
				uni.showToast({ title: '请输入用户名和密码', icon: 'none' })
				return
			}
			this.submitting = true
			try {
				const res = await login({
					username: this.username,
					password: this.password
				})
				if (res.code === 200) {
					const store = useUserStore()
					store.setToken(res.data)
					await store.fetchUserInfo()
					uni.switchTab({ url: '/pages/dashboard/index' })
				} else {
					uni.showToast({ title: res.message || '登录失败', icon: 'none' })
				}
			} catch (e) {
				uni.showToast({ title: '网络连接失败', icon: 'none' })
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

/* ── 头部 ── */
.header {
	text-align: center;
	margin-bottom: 80rpx;
}

.title {
	font-size: var(--font-5xl);
	font-weight: var(--weight-extrabold);
	color: var(--color-text-heading);
	display: block;
	letter-spacing: var(--tracking-heading);
	line-height: var(--leading-tight);
}

.subtitle {
	font-size: var(--font-md);
	color: var(--color-text-secondary);
	margin-top: var(--space-md);
	display: block;
	font-weight: var(--weight-medium);
	letter-spacing: var(--tracking-caption);
}

/* ── 表单卡片 ── */
.form-card {
	background-color: var(--color-surface);
	border-radius: var(--radius-2xl);
	padding: var(--space-3xl);
	box-shadow: var(--shadow-sm);
}

.input-group {
	margin-bottom: var(--space-xl);
}

.label {
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
	color: var(--color-text);
	margin-bottom: var(--space-sm);
	display: block;
}

.input {
	height: 88rpx;
	border: 2rpx solid var(--color-border-input);
	border-radius: var(--radius-md);
	padding: 0 var(--space-lg);
	font-size: var(--font-lg);
	color: var(--color-text);
	background-color: var(--color-bg);
	transition: border-color var(--transition-fast);
}

/* 输入框激活效果用 focus 伪类的话 uni-app 支持有限，靠原生 */
.input:focus {
	border-color: var(--color-primary);
}

.placeholder {
	color: var(--color-text-tertiary);
	font-size: var(--font-base);
}

/* ── 登录按钮 ── */
.btn-primary {
	margin-top: var(--space-md);
	height: 88rpx;
	line-height: 88rpx;
	background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
	color: var(--color-text-inverse);
	font-size: var(--font-lg);
	font-weight: var(--weight-bold);
	border-radius: var(--radius-lg);
	border: none;
	box-shadow: var(--shadow-accent);
	transition: transform var(--transition-spring), opacity var(--transition-fast);
}

.btn-primary::after {
	border: none;
}

.btn-primary:active {
	transform: scale(0.97);
}

.btn-primary[disabled] {
	opacity: 0.6;
}

/* ── 注册链接 ── */
.link {
	text-align: center;
	margin-top: var(--space-2xl);
}

.link-text {
	font-size: var(--font-md);
	color: var(--color-text-secondary);
}

.link-highlight {
	font-size: var(--font-md);
	color: var(--color-accent);
	font-weight: var(--weight-semibold);
	margin-left: var(--space-xs);
}
</style>
