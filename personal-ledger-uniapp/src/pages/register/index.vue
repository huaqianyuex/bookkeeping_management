<template>
	<view class="container">
		<view class="header">
			<text class="title">注册账号</text>
			<text class="subtitle">创建您的记账账户</text>
		</view>

		<view class="form-card">
			<view class="input-group">
				<text class="label">用户名</text>
				<input
					class="input"
					v-model="username"
					placeholder="2-20位用户名"
					placeholder-class="placeholder"
				/>
			</view>

			<view class="input-group">
				<text class="label">密码</text>
				<input
					class="input"
					v-model="password"
					placeholder="6-20位密码"
					placeholder-class="placeholder"
					:password="true"
				/>
			</view>

			<view class="input-group">
				<text class="label">确认密码</text>
				<input
					class="input"
					v-model="confirmPassword"
					placeholder="再次输入密码"
					placeholder-class="placeholder"
					:password="true"
				/>
			</view>

			<button
				class="btn-primary"
				:loading="submitting"
				:disabled="submitting"
				@click="handleRegister"
			>
				注册
			</button>

			<view class="link" @click="goLogin">
				<text class="link-text">已有账号？</text>
				<text class="link-highlight">返回登录</text>
			</view>
		</view>
	</view>
</template>

<script>
import { register } from '../../api/user'

export default {
	data() {
		return {
			username: '',
			password: '',
			confirmPassword: '',
			submitting: false,
		}
	},
	methods: {
		async handleRegister() {
			if (!this.username || !this.password) {
				uni.showToast({ title: '请填写完整信息', icon: 'none' })
				return
			}
			if (this.username.length < 2 || this.username.length > 20) {
				uni.showToast({ title: '用户名长度2-20位', icon: 'none' })
				return
			}
			if (this.password.length < 6 || this.password.length > 20) {
				uni.showToast({ title: '密码长度6-20位', icon: 'none' })
				return
			}
			if (this.password !== this.confirmPassword) {
				uni.showToast({ title: '两次密码不一致', icon: 'none' })
				return
			}
			this.submitting = true
			try {
				const res = await register({
					username: this.username,
					password: this.password
				})
				if (res.code === 200) {
					uni.showToast({ title: '注册成功', icon: 'success' })
					setTimeout(() => {
						uni.navigateBack()
					}, 1500)
				} else {
					uni.showToast({ title: res.message || '注册失败', icon: 'none' })
				}
			} catch (e) {
				uni.showToast({ title: '网络连接失败', icon: 'none' })
			} finally {
				this.submitting = false
			}
		},
		goLogin() {
			uni.navigateBack()
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
	padding: 60rpx var(--space-3xl);
}

.header {
	text-align: center;
	margin-bottom: 60rpx;
}

.title {
	font-size: var(--font-5xl);
	font-weight: var(--weight-bold);
	color: var(--color-text);
	display: block;
}

.subtitle {
	font-size: var(--font-md);
	color: #8c8c8c;
	margin-top: var(--space-sm);
	display: block;
}

.form-card {
	background-color: var(--color-surface);
	border-radius: var(--radius-xl);
	padding: var(--space-3xl);
	box-shadow: var(--shadow-sm);
}

.input-group {
	margin-bottom: var(--space-xl);
}

.label {
	font-size: var(--font-base);
	font-weight: var(--weight-medium);
	color: var(--color-text);
	margin-bottom: var(--space-sm);
	display: block;
}

.input {
	height: 88rpx;
	border: 1px solid var(--color-border-input);
	border-radius: var(--radius-md);
	padding: 0 var(--space-lg);
	font-size: var(--font-lg);
	color: var(--color-text);
	background-color: var(--color-bg);
}

.placeholder {
	color: #bfbfbf;
}

.btn-primary {
	margin-top: var(--space-md);
	height: 88rpx;
	line-height: 88rpx;
	background-color: var(--color-primary);
	color: var(--color-text-inverse);
	font-size: var(--font-lg);
	font-weight: var(--weight-semibold);
	border-radius: var(--radius-md);
	border: none;
}

.btn-primary::after {
	border: none;
}

.link {
	text-align: center;
	margin-top: var(--space-xl);
}

.link-text {
	font-size: var(--font-md);
	color: #8c8c8c;
}

.link-highlight {
	font-size: var(--font-md);
	color: var(--color-text);
	font-weight: var(--weight-medium);
}
</style>
