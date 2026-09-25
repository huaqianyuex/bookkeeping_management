<template>
	<view class="container">
		<!-- 设计稿01 品牌区（注册页同风格） -->
		<view class="brand">
			<view class="brand-logo">
				<app-icon name="receipt" :size="64"></app-icon>
			</view>
			<text class="brand-name">创建账号</text>
			<text class="brand-slogan">加入简记，开始记录</text>
		</view>

		<view class="form-card">
			<view class="input-group">
				<input
					class="input"
					v-model="username"
					placeholder="2-20位用户名"
					placeholder-class="placeholder"
				/>
			</view>

			<view class="input-group">
				<input
					class="input"
					v-model="password"
					placeholder="6位数字密码"
					placeholder-class="placeholder"
					:password="true"
				/>
			</view>

			<view class="input-group">
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
import AppIcon from '../../components/AppIcon.vue'

export default {
	components: { AppIcon },
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
			if (this.password.length !== 6 || !/^\d{6}$/.test(this.password)) {
				uni.showToast({ title: '密码需为6位数字', icon: 'none' })
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
					// 回填用户名到登录页，注册→登录零重复输入
					uni.setStorageSync('login_prefill_username', this.username)
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
	padding: var(--space-4xl) var(--space-3xl);
}

/* ── 品牌区（设计稿01 同款，缩小版） ── */
.brand {
	display: flex;
	flex-direction: column;
	align-items: center;
	margin-bottom: 64rpx;
}

.brand-logo {
	width: 120rpx;
	height: 120rpx;
	border-radius: var(--radius-2xl);
	background-color: var(--color-accent);
	display: flex;
	align-items: center;
	justify-content: center;
	box-shadow: var(--shadow-accent);
	margin-bottom: var(--space-lg);
}

.brand-name {
	font-size: var(--font-2xl);
	font-weight: var(--weight-extrabold);
	color: var(--color-text-heading);
	line-height: var(--leading-tight);
	margin-bottom: var(--space-xs);
}

.brand-slogan {
	font-size: var(--font-sm);
	color: var(--color-text-secondary);
}

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
}

.input:focus {
	background-color: var(--color-divider);
}

.placeholder {
	color: var(--color-text-tertiary);
}

/* ── 注册按钮（设计稿01：黑色胶囊） ── */
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
}

.btn-primary::after {
	border: none;
}

.btn-primary[disabled] {
	opacity: 0.5;
	box-shadow: none;
}

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
}
</style>
