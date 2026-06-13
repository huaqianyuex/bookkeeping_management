<template>
	<view class="container">
		<view class="form-card">
			<view class="form-header">
				<text class="form-icon">🔒</text>
				<text class="form-title">修改密码</text>
				<text class="form-subtitle">请填写您的新密码</text>
			</view>

			<view class="input-group">
				<text class="label">原密码</text>
				<input
					class="input"
					v-model="oldPassword"
					placeholder="请输入原密码"
					placeholder-class="placeholder"
					:password="true"
				/>
			</view>

			<view class="input-group">
				<text class="label">新密码</text>
				<input
					class="input"
					v-model="newPassword"
					placeholder="6-20位新密码"
					placeholder-class="placeholder"
					:password="true"
				/>
			</view>

			<view class="input-group">
				<text class="label">确认新密码</text>
				<input
					class="input"
					v-model="confirmPassword"
					placeholder="再次输入新密码"
					placeholder-class="placeholder"
					:password="true"
				/>
			</view>

			<button
				class="btn-primary"
				:loading="submitting"
				:disabled="submitting"
				@click="handleSubmit"
			>
				确认修改
			</button>
		</view>
	</view>
</template>

<script>
import { updatePassword } from '../../api/user'

export default {
	data() {
		return {
			oldPassword: '',
			newPassword: '',
			confirmPassword: '',
			submitting: false,
		}
	},
	methods: {
		async handleSubmit() {
			if (!this.oldPassword || !this.newPassword) {
				uni.showToast({ title: '请填写完整信息', icon: 'none' })
				return
			}
			if (this.newPassword.length < 6 || this.newPassword.length > 20) {
				uni.showToast({ title: '新密码长度6-20位', icon: 'none' })
				return
			}
			if (this.newPassword !== this.confirmPassword) {
				uni.showToast({ title: '两次密码不一致', icon: 'none' })
				return
			}
			this.submitting = true
			try {
				const res = await updatePassword({
					oldPassword: this.oldPassword,
					newPassword: this.newPassword,
				})
				if (res.code === 200) {
					uni.showToast({ title: '修改成功', icon: 'success' })
					setTimeout(() => {
						uni.navigateBack()
					}, 1500)
				} else {
					uni.showToast({ title: res.message || '修改失败', icon: 'none' })
				}
			} catch (e) {
				uni.showToast({ title: '网络连接失败', icon: 'none' })
			} finally {
				this.submitting = false
			}
		}
	}
}
</script>

<style scoped>
.container {
	min-height: 100vh;
	background-color: var(--color-bg);
	display: flex;
	align-items: center;
	justify-content: center;
	padding: 60rpx var(--space-3xl);
}

.form-card {
	background-color: var(--color-surface);
	border-radius: var(--radius-2xl);
	padding: var(--space-3xl);
	width: 100%;
	box-shadow: var(--shadow-sm);
}

.form-header {
	text-align: center;
	margin-bottom: var(--space-3xl);
}

.form-icon {
	font-size: var(--font-5xl);
	display: block;
	margin-bottom: var(--space-md);
}

.form-title {
	font-size: var(--font-2xl);
	font-weight: var(--weight-bold);
	color: var(--color-text);
	display: block;
	margin-bottom: var(--space-xs);
}

.form-subtitle {
	font-size: var(--font-sm);
	color: var(--color-text-secondary);
	display: block;
}

.input-group {
	margin-bottom: var(--space-lg);
}

.label {
	font-size: var(--font-md);
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
	font-size: var(--font-base);
	color: var(--color-text);
	background-color: var(--color-bg);
}

.placeholder {
	color: #bfbfbf;
}

.btn-primary {
	margin-top: var(--space-lg);
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
</style>
