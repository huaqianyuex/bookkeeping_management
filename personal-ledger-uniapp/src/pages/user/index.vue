<template>
	<view class="container">
		<!-- 状态栏占位 -->
		<view class="status-bar" :style="{ height: statusBarHeight + 'px' }"></view>
		<scroll-view scroll-y class="scroll-content">
			<!-- 设计稿06：顶部大标题 -->
			<text class="page-title">我的</text>

			<!-- 设计稿06 用户卡：头像左 + 名称信息右 -->
			<view class="profile-card">
				<view class="avatar-container" @click="handlePickAvatar">
					<image
						v-if="avatarSrc"
						:src="avatarSrc"
						class="avatar-image"
						mode="aspectFill"
					/>
					<view v-else class="avatar-placeholder">
						<text class="avatar-emoji">{{ (userInfo?.username || '记').slice(0, 1) }}</text>
					</view>
					<view class="avatar-badge">
						<app-icon name="camera" :size="24"></app-icon>
					</view>
				</view>

					<!-- 用户名 + 编辑 -->
					<view class="profile-info">
						<view class="username-row">
							<text class="username">{{ userInfo?.username || '加载中...' }}</text>
							<view class="edit-btn" @click="openUsernameEditor">
								<app-icon name="edit" :size="28"></app-icon>
							</view>
						</view>

						<view class="user-id-badge">
							<text class="user-id">ID: {{ userInfo?.id || '-' }}</text>
						</view>
						<text class="avatar-hint">点击头像更换</text>
					</view>
				</view>

			<!-- 功能菜单 -->
		<view class="menu-card">
			<view class="menu-item" @click="goPassword">
				<view class="menu-left">
					<view class="menu-icon">
						<app-icon name="lock" :size="32"></app-icon>
					</view>
					<text class="menu-text">修改密码</text>
				</view>
				<text class="menu-arrow">›</text>
			</view>
		</view>

			<!-- 退出按钮 -->
			<view class="logout-btn" @click="handleLogout">
				<app-icon name="logout" :size="32"></app-icon>
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
import { updateUserInfo, uploadAvatar } from '../../api/user'
import { getBaseUrl } from '../../api/config'
import AppIcon from '../../components/AppIcon.vue'

const USERNAME_REGEX = /^[A-Za-z0-9\u4e00-\u9fa5]{2,20}$/
const MAX_AVATAR_SIZE = 2 * 1024 * 1024 // 2MB

export default {
	components: { AppIcon },
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
			const avatarUrl = this.userInfo?.avatar
			if (!avatarUrl) return ''
			if (avatarUrl.startsWith('http://') || avatarUrl.startsWith('https://')) {
				return avatarUrl
			}
			const base = getBaseUrl().replace(/\/api\/?$/, '')
			return base + avatarUrl
		},
	},
	onShow() {
		// 未登录/登录过期由 App.vue onLaunch 与 request.js 的全局 401 拦截统一处理，
		// 此处不再主动 reLaunch，避免启动瞬间多个页面同时跳转造成 "do not operate continuously" 卡死。
		const token = uni.getStorageSync('token')
		if (!token) {
			return
		}
		this.fetchUserInfo()
	},
	methods: {
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
	background-color: var(--color-bg);
}

.scroll-content {
	flex: 1;
	box-sizing: border-box;
	padding: var(--space-lg) var(--space-xl) calc(var(--space-4xl) + 240rpx);
	-webkit-overflow-scrolling: touch;
}

/* 设计稿06：顶部大标题 */
.page-title {
	display: block;
	font-size: var(--font-3xl);
	font-weight: var(--weight-extrabold);
	color: var(--color-text-heading);
	margin-bottom: var(--space-xl);
}

/* ── 用户卡（设计稿06：白卡内头像左 + 信息右） ── */
/* ── 用户区：纸面上的发丝线分组，无卡片盒 ── */
.profile-card {
	display: flex;
	align-items: center;
	padding: var(--space-lg) 0 var(--space-2xl);
	border-bottom: var(--hairline) solid var(--color-border);
	margin-bottom: var(--space-lg);
}

.avatar-container {
	position: relative;
	flex-shrink: 0;
	margin-right: var(--space-xl);
}

.avatar-image {
	width: 128rpx;
	height: 128rpx;
	border-radius: var(--radius-full);
}

/* 设计稿06：黄色圆形头像占位，显示用户名首字 */
.avatar-placeholder {
	width: 128rpx;
	height: 128rpx;
	border-radius: var(--radius-full);
	background: var(--color-accent);
	display: flex;
	align-items: center;
	justify-content: center;
}

.avatar-emoji {
	font-size: var(--font-3xl);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
}

.avatar-badge {
	position: absolute;
	bottom: 0;
	right: 0;
	width: 44rpx;
	height: 44rpx;
	border-radius: var(--radius-full);
	background-color: var(--color-surface);
	box-shadow: var(--shadow-xs);
	display: flex;
	align-items: center;
	justify-content: center;
}

.profile-info {
	flex: 1;
	min-width: 0;
}

.username-row {
	display: flex;
	align-items: center;
	gap: var(--space-sm);
	margin-bottom: var(--space-sm);
}

.username {
	font-size: var(--font-2xl);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.edit-btn {
	width: 56rpx;
	height: 56rpx;
	border-radius: var(--radius-full);
	background-color: var(--color-surface-raised);
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
	transition: background-color var(--transition-fast);
}

.edit-btn:active {
	background-color: var(--color-border);
}

.user-id-badge {
	display: inline-flex;
	align-items: center;
	padding: var(--space-2xs) var(--space-md);
	background-color: var(--color-surface-raised);
	border-radius: var(--radius-full);
	margin-bottom: var(--space-xs);
}

.user-id {
	font-size: var(--font-xs);
	color: var(--color-text-secondary);
	font-weight: var(--weight-medium);
}

.avatar-hint {
	display: block;
	font-size: var(--font-2xs);
	color: var(--color-text-tertiary);
}

/* ── 功能菜单（设计稿06：白卡菜单行 + 右箭头） ── */
.menu-card {
	overflow: hidden;
	margin-bottom: var(--space-xl);
	border-top: var(--hairline) solid var(--color-border);
	border-bottom: var(--hairline) solid var(--color-border);
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
	flex-shrink: 0;
	display: flex;
	align-items: center;
	justify-content: center;
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

/* ── 退出登录（设计稿：红字胶囊按钮） ── */
.logout-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: var(--space-sm);
	height: 104rpx;
	border-radius: var(--radius-full);
	border: 2rpx solid var(--color-danger);
	background-color: transparent;
	margin-top: var(--space-xl);
	transition:
		background-color var(--transition-fast),
		opacity var(--transition-fast);
}

.logout-btn:active {
	background-color: var(--color-danger-light);
}

.logout-text {
	font-size: var(--font-base);
	font-weight: var(--weight-medium);
	color: var(--color-danger);
}

/* ── 编辑弹窗 ── */
.modal-backdrop {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background-color: var(--color-overlay);
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
	padding: var(--space-2xl);
	box-shadow: var(--shadow-lg);
}

.modal-title {
	font-size: var(--font-xl);
	font-weight: var(--weight-extrabold);
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

/* 设计稿01：灰底无边框圆角输入 */
.modal-input {
	height: 96rpx;
	border: none;
	border-radius: var(--radius-lg);
	padding: 0 var(--space-xl);
	font-size: var(--font-base);
	color: var(--color-text);
	background-color: var(--color-surface-raised);
}

.modal-input-error {
	background-color: var(--color-danger-light);
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
	height: 96rpx;
	border-radius: var(--radius-full);
	background-color: var(--color-surface-raised);
	display: flex;
	align-items: center;
	justify-content: center;
}

.modal-cancel-text {
	font-size: var(--font-base);
	color: var(--color-text-secondary);
	font-weight: var(--weight-semibold);
}

/* 设计稿01：黑色胶囊确认按钮 */
.modal-confirm-btn {
	flex: 1;
	height: 96rpx;
	border-radius: var(--radius-full);
	background-color: var(--color-primary);
	box-shadow: var(--shadow-primary);
	display: flex;
	align-items: center;
	justify-content: center;
}

.modal-confirm-disabled {
	opacity: 0.4;
	box-shadow: none;
}

.modal-confirm-text {
	font-size: var(--font-base);
	color: var(--color-text-inverse);
	font-weight: var(--weight-semibold);
}
</style>
