<template>
	<view class="container">
		<!-- 状态栏占位 -->
		<view class="status-bar" :style="{ height: statusBarHeight + 'px' }"></view>
		<scroll-view scroll-y class="scroll-content">
			<!-- 用户头像卡片 -->
			<view class="profile-card">
				<view class="avatar-container" @click="handlePickAvatar">
					<image
						v-if="avatarSrc"
						:src="avatarSrc"
						class="avatar-image"
						mode="aspectFill"
					/>
					<view v-else class="avatar-placeholder">
						<text class="avatar-emoji">👤</text>
					</view>
					<view class="avatar-badge">
						<text class="badge-icon">📷</text>
					</view>
					<view class="online-indicator"></view>
				</view>
				<text class="avatar-hint">点击更换头像</text>

				<!-- 用户名 + 编辑 -->
				<view class="username-row">
					<text class="username">{{ userInfo?.username || '加载中...' }}</text>
					<view class="edit-btn" @click="openUsernameEditor">
						<text class="edit-icon">✏️</text>
					</view>
				</view>

				<view class="user-id-badge">
					<text class="user-id">ID: {{ userInfo?.id || '-' }}</text>
				</view>
			</view>

			<!-- 信息卡片 -->
			<view class="info-card">
				<text class="card-title">个人信息</text>
				<view class="info-row">
					<view class="info-left">
						<view class="info-icon">🔑</view>
						<text class="info-label">用户ID</text>
					</view>
					<text class="info-value">{{ userInfo?.id || '-' }}</text>
				</view>
				<view class="info-row">
					<view class="info-left">
						<view class="info-icon">👤</view>
						<text class="info-label">用户名</text>
					</view>
					<text class="info-value">{{ userInfo?.username || '-' }}</text>
				</view>
				<view class="info-row">
					<view class="info-left">
						<view class="info-icon">⏰</view>
						<text class="info-label">创建时间</text>
					</view>
					<text class="info-value">{{ formatDate(userInfo?.createTime) }}</text>
				</view>
				<view class="info-row last">
					<view class="info-left">
						<view class="info-icon">🔄</view>
						<text class="info-label">更新时间</text>
					</view>
					<text class="info-value">{{ formatDate(userInfo?.updateTime) }}</text>
				</view>
			</view>

			<!-- 功能菜单 -->
			<view class="menu-card">
				<view class="menu-item" @click="goAiChat">
					<view class="menu-left">
						<view class="menu-icon">🤖</view>
						<text class="menu-text">AI记账助手</text>
					</view>
					<text class="menu-arrow">›</text>
				</view>
				<view class="menu-item" @click="goPassword">
					<view class="menu-left">
						<view class="menu-icon">🔒</view>
						<text class="menu-text">修改密码</text>
					</view>
					<text class="menu-arrow">›</text>
				</view>
			</view>

			<!-- 退出按钮 -->
			<view class="logout-btn" @click="handleLogout">
				<text class="logout-icon">🚪</text>
				<text class="logout-text">退出登录</text>
			</view>
		</scroll-view>
		<TabBar currentPage="pages/user/index" />

		<!-- 用户名编辑弹窗 -->
		<view v-if="showUsernameEditor" class="modal-backdrop" @click="closeUsernameEditor">
			<view class="modal-card" @click.stop>
				<text class="modal-title">修改用户名</text>
				<text class="modal-desc">支持 2-20 个字符的中文、英文和数字组合</text>

				<input
					v-model="usernameInput"
					class="modal-input"
					:class="{ 'modal-input-error': usernameError }"
					placeholder="请输入新用户名"
					:maxlength="20"
					focus
					@input="onUsernameInput"
				/>
				<text v-if="usernameError" class="modal-error">{{ usernameError }}</text>

				<view class="modal-actions">
					<view class="modal-cancel-btn" @click="closeUsernameEditor">
						<text class="modal-cancel-text">取消</text>
					</view>
					<view
						class="modal-confirm-btn"
						:class="{ 'modal-confirm-disabled': !!usernameError || usernameSubmitting }"
						@click="handleUsernameSubmit"
					>
						<text class="modal-confirm-text">{{ usernameSubmitting ? '提交中...' : '确认修改' }}</text>
					</view>
				</view>
			</view>
		</view>
	</view>
</template>

<script>
import { useUserStore } from '../../utils/store'
import { formatDate } from '../../utils/format'
import { updateUserInfo, uploadAvatar } from '../../api/user'
import { getBaseUrl } from '../../api/config'

const USERNAME_REGEX = /^[A-Za-z0-9\u4e00-\u9fa5]{2,20}$/
const MAX_AVATAR_SIZE = 2 * 1024 * 1024 // 2MB

export default {
	components: {},
	data() {
		return {
			statusBarHeight: 20,
			userInfo: null,
			// 用户名编辑弹窗
			showUsernameEditor: false,
			usernameInput: '',
			usernameError: '',
			usernameSubmitting: false,
		}
	},
	onLoad() {
		const systemInfo = uni.getSystemInfoSync()
		this.statusBarHeight = systemInfo.statusBarHeight || 20
	},
	computed: {
		/** 拼接完整的头像 URL */
		avatarSrc() {
			const avatarUrl = this.userInfo?.avatarUrl
			if (!avatarUrl) return ''
			if (avatarUrl.startsWith('http://') || avatarUrl.startsWith('https://')) {
				return avatarUrl
			}
			const base = getBaseUrl().replace(/\/api\/?$/, '')
			return base + avatarUrl
		},
	},
	onShow() {
		this.fetchUserInfo()
	},
	methods: {
		formatDate,

		// ── 获取用户信息 ──
		async fetchUserInfo() {
			const store = useUserStore()
			if (store.isLoggedIn) {
				const info = await store.fetchUserInfo()
				this.userInfo = info
			}
		},

		// ── 头像选择与上传 ──
		handlePickAvatar() {
			uni.chooseImage({
				count: 1,
				sizeType: ['compressed'],
				sourceType: ['album', 'camera'],
				success: async (res) => {
					const filePath = res.tempFilePaths[0]

					// 获取文件信息以校验大小
					// #ifdef H5
					// H5 环境下无法直接获取文件大小，跳过大小校验
					this.doUploadAvatar(filePath)
					// #endif

					// #ifndef H5
					uni.getFileInfo({
						filePath: filePath,
						success: (info) => {
							if (info.size > MAX_AVATAR_SIZE) {
								uni.showToast({ title: '头像大小不能超过2MB', icon: 'none' })
								return
							}
							this.doUploadAvatar(filePath)
						},
						fail: () => {
							// 获取失败仍尝试上传，由后端校验
							this.doUploadAvatar(filePath)
						},
					})
					// #endif
				},
			})
		},

		async doUploadAvatar(filePath) {
			uni.showLoading({ title: '上传中...', mask: true })
			try {
				const res = await uploadAvatar(filePath)
				if (res.code === 200) {
					const store = useUserStore()
					store.setUserInfo(res.data)
					this.userInfo = res.data
					uni.showToast({ title: '头像上传成功', icon: 'success' })
				} else {
					uni.showToast({ title: res.message || '头像上传失败', icon: 'none' })
				}
			} catch (e) {
				const msg = e?.message || '头像上传失败，请稍后重试'
				uni.showToast({ title: msg, icon: 'none' })
			} finally {
				uni.hideLoading()
			}
		},

		// ── 用户名编辑 ──
		openUsernameEditor() {
			this.usernameInput = this.userInfo?.username || ''
			this.usernameError = ''
			this.showUsernameEditor = true
		},

		closeUsernameEditor() {
			this.showUsernameEditor = false
			this.usernameError = ''
		},

		onUsernameInput(e) {
			const val = e.detail?.value ?? this.usernameInput
			this.usernameInput = val
			if (!val || val.trim().length === 0) {
				this.usernameError = '用户名不能为空'
			} else if (val.trim().length < 2) {
				this.usernameError = '用户名至少需要 2 个字符'
			} else if (!USERNAME_REGEX.test(val.trim())) {
				this.usernameError = '用户名仅支持中英文和数字组合'
			} else {
				this.usernameError = ''
			}
		},

		async handleUsernameSubmit() {
			const trimmed = this.usernameInput.trim()
			if (!trimmed) {
				this.usernameError = '用户名不能为空'
				return
			}
			if (!USERNAME_REGEX.test(trimmed)) {
				this.usernameError = '用户名需为 2-20 位中英文或数字组合'
				return
			}
			if (this.usernameError || this.usernameSubmitting) return

			this.usernameSubmitting = true
			try {
				const res = await updateUserInfo({ username: trimmed })
				if (res.code === 200) {
					const store = useUserStore()
					store.setUserInfo(res.data)
					this.userInfo = res.data
					this.showUsernameEditor = false
					uni.showToast({ title: '用户名更新成功', icon: 'success' })
				} else {
					this.usernameError = res.message || '用户名更新失败'
				}
			} catch (e) {
				const msg = e?.message || '请求失败，请稍后重试'
				this.usernameError = msg
			} finally {
				this.usernameSubmitting = false
			}
		},

		// ── 导航 ──
		goPassword() {
			uni.navigateTo({ url: '/pages/password/index' })
		},
		goAiChat() {
			uni.navigateTo({ url: '/pages/ai-chat/index' })
		},

		// ── 退出 ──
		handleLogout() {
			uni.showModal({
				title: '退出登录',
				content: '确定要退出登录吗？',
				success: (res) => {
					if (res.confirm) {
						const store = useUserStore()
						store.logout()
					}
				},
			})
		},
	},
}
</script>

<style scoped>
.container {
	min-height: 100vh;
	background-color: var(--color-bg);
	display: flex;
	flex-direction: column;
}

.status-bar {
	width: 100%;
	background-color: var(--color-surface);
}

.scroll-content {
	flex: 1;
	box-sizing: border-box;
	padding: var(--space-xl) var(--space-xl) calc(var(--space-4xl) + 100rpx);
	-webkit-overflow-scrolling: touch;
}

/* ── 头像卡片 ── */
.profile-card {
	text-align: center;
	padding: 64rpx 0;
	background: linear-gradient(180deg, var(--color-surface-raised), var(--color-surface));
	border-radius: var(--radius-2xl);
	margin-bottom: var(--space-lg);
	box-shadow: var(--shadow-sm);
}

.avatar-container {
	position: relative;
	display: inline-block;
	margin-bottom: var(--space-sm);
}

.avatar-image {
	width: 140rpx;
	height: 140rpx;
	border-radius: var(--radius-full);
	border: 4rpx solid var(--color-border);
}

.avatar-placeholder {
	width: 140rpx;
	height: 140rpx;
	border-radius: var(--radius-full);
	background: linear-gradient(145deg, var(--color-primary), var(--color-accent));
	display: flex;
	align-items: center;
	justify-content: center;
	box-shadow: var(--shadow-accent);
}

.avatar-emoji {
	font-size: var(--font-5xl);
	opacity: 0.9;
}

.avatar-badge {
	position: absolute;
	bottom: 0;
	right: 0;
	width: 40rpx;
	height: 40rpx;
	border-radius: var(--radius-full);
	background-color: var(--color-accent);
	display: flex;
	align-items: center;
	justify-content: center;
	border: 4rpx solid var(--color-surface);
}

.badge-icon {
	font-size: var(--font-sm);
}

.avatar-hint {
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
	display: block;
	margin-bottom: var(--space-lg);
}

.online-indicator {
	position: absolute;
	top: 4rpx;
	right: 4rpx;
	width: 28rpx;
	height: 28rpx;
	border-radius: var(--radius-full);
	background-color: var(--color-success);
	border: 6rpx solid var(--color-surface);
	box-shadow: var(--shadow-success);
}

.username-row {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: var(--space-sm);
	margin-bottom: var(--space-sm);
}

.username {
	font-size: var(--font-3xl);
	font-weight: var(--weight-extrabold);
	color: var(--color-text-heading);
	letter-spacing: var(--tracking-heading);
}

.edit-btn {
	width: 48rpx;
	height: 48rpx;
	border-radius: var(--radius-sm);
	background-color: var(--color-border);
	display: flex;
	align-items: center;
	justify-content: center;
	transition: background-color var(--transition-fast);
}

.edit-btn:active {
	background-color: var(--color-primary-bg);
}

.edit-icon {
	font-size: var(--font-base);
}

.user-id-badge {
	display: inline-flex;
	align-items: center;
	padding: var(--space-xs) var(--space-lg);
	background-color: var(--color-border);
	border-radius: var(--radius-full);
}

.user-id {
	font-size: var(--font-sm);
	color: var(--color-text-secondary);
	font-weight: var(--weight-medium);
}

/* ── 信息卡片 ── */
.info-card {
	background-color: var(--color-surface);
	border-radius: var(--radius-2xl);
	padding: var(--space-xl);
	margin-bottom: var(--space-lg);
	box-shadow: var(--shadow-sm);
}

.card-title {
	font-size: var(--font-lg);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	margin-bottom: var(--space-lg);
	display: block;
	letter-spacing: var(--tracking-heading);
	padding-bottom: var(--space-md);
	border-bottom: 1rpx solid var(--color-divider);
}

.info-row {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: var(--space-lg) 0;
	border-bottom: 1rpx solid var(--color-divider);
	transition: background-color var(--transition-fast);
}

.info-row.last {
	border-bottom: none;
}

.info-left {
	display: flex;
	align-items: center;
	gap: var(--space-md);
}

.info-icon {
	font-size: var(--font-base);
	opacity: 0.8;
}

.info-label {
	font-size: var(--font-md);
	color: var(--color-text-secondary);
	font-weight: var(--weight-medium);
}

.info-value {
	font-size: var(--font-md);
	color: var(--color-text);
	font-weight: var(--weight-semibold);
}

/* ── 功能菜单 ── */
.menu-card {
	background-color: var(--color-surface);
	border-radius: var(--radius-2xl);
	margin-bottom: var(--space-xl);
	overflow: hidden;
	box-shadow: var(--shadow-sm);
}

.menu-item {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: var(--space-xl);
	border-bottom: 1rpx solid var(--color-divider);
	transition:
		background-color var(--transition-fast),
		transform var(--transition-fast);
}

.menu-item:last-child {
	border-bottom: none;
}

.menu-item:active {
	background-color: var(--color-surface-raised);
}

.menu-left {
	display: flex;
	align-items: center;
	gap: var(--space-md);
	min-width: 0;
	flex: 1;
}

.menu-icon {
	font-size: var(--font-xl);
	opacity: 0.85;
	flex-shrink: 0;
}

.menu-text {
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
	color: var(--color-text);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.menu-arrow {
	font-size: var(--font-2xl);
	color: var(--color-text-tertiary);
	font-weight: var(--weight-bold);
	flex-shrink: 0;
}

/* ── 退出登录 ── */
.logout-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: var(--space-sm);
	height: 96rpx;
	border-radius: var(--radius-xl);
	border: 2rpx solid var(--color-danger-light);
	background-color: var(--color-surface);
	margin-top: var(--space-xl);
	transition:
		background-color var(--transition-fast),
		transform var(--transition-spring);
}

.logout-btn:active {
	background-color: var(--color-danger-light);
	transform: scale(0.97);
}

.logout-icon {
	font-size: var(--font-xl);
}

.logout-text {
	font-size: var(--font-lg);
	font-weight: var(--weight-semibold);
	color: var(--color-danger);
}

/* ── 编辑弹窗 ── */
.modal-backdrop {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background-color: rgba(0, 0, 0, 0.45);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 999;
	padding: var(--space-xl);
}

.modal-card {
	width: 100%;
	max-width: 600rpx;
	background-color: var(--color-surface);
	border-radius: var(--radius-2xl);
	padding: var(--space-xl);
	box-shadow: var(--shadow-lg);
}

.modal-title {
	font-size: var(--font-xl);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	display: block;
	margin-bottom: var(--space-xs);
}

.modal-desc {
	font-size: var(--font-sm);
	color: var(--color-text-secondary);
	display: block;
	margin-bottom: var(--space-lg);
	line-height: 1.5;
}

.modal-input {
	height: 88rpx;
	border: 2rpx solid var(--color-border);
	border-radius: var(--radius-md);
	padding: 0 var(--space-lg);
	font-size: var(--font-base);
	color: var(--color-text);
	background-color: var(--color-bg);
}

.modal-input-error {
	border-color: var(--color-danger);
}

.modal-error {
	font-size: var(--font-xs);
	color: var(--color-danger);
	margin-top: var(--space-xs);
	padding-left: var(--space-xs);
	display: block;
}

.modal-actions {
	display: flex;
	gap: var(--space-md);
	margin-top: var(--space-xl);
}

.modal-cancel-btn {
	flex: 1;
	height: 80rpx;
	border-radius: var(--radius-md);
	border: 2rpx solid var(--color-border);
	display: flex;
	align-items: center;
	justify-content: center;
}

.modal-cancel-text {
	font-size: var(--font-base);
	color: var(--color-text-secondary);
	font-weight: var(--weight-semibold);
}

.modal-confirm-btn {
	flex: 1;
	height: 80rpx;
	border-radius: var(--radius-md);
	background-color: var(--color-primary);
	display: flex;
	align-items: center;
	justify-content: center;
}

.modal-confirm-disabled {
	opacity: 0.5;
}

.modal-confirm-text {
	font-size: var(--font-base);
	color: #fff;
	font-weight: var(--weight-semibold);
}
</style>
