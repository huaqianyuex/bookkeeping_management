<template>
	<view class="container">
		<!-- 状态栏占位 -->
		<view class="status-bar" :style="{ height: statusBarHeight + 'px' }"></view>
		<view class="page-top-bar">
			<!-- 设计稿05：左大标题 + 右添加 -->
			<text class="page-title">分类管理</text>
			<view class="add-btn" @click="showAdd">
				<text class="add-icon">+</text>
			</view>
		</view>

		<!-- 设计稿05：支出/收入胶囊分段（仅视图筛选） -->
		<view class="type-tabs">
			<view class="type-tab" :class="{ active: viewType === 0 }" @click="viewType = 0">
				<text class="type-tab-text" :class="{ active: viewType === 0 }">支出</text>
			</view>
			<view class="type-tab" :class="{ active: viewType === 1 }" @click="viewType = 1">
				<text class="type-tab-text" :class="{ active: viewType === 1 }">收入</text>
			</view>
		</view>

		<scroll-view scroll-y class="scroll-content">
			<!-- Loading skeleton -->
			<view v-if="loading" class="skeleton-list">
				<skeleton-card :lines="2" style="margin-bottom: 16rpx;"></skeleton-card>
				<skeleton-card :lines="2" style="margin-bottom: 16rpx;"></skeleton-card>
				<skeleton-card :lines="2"></skeleton-card>
			</view>

			<!-- Empty state -->
			<empty-state
				v-else-if="filteredList.length === 0"
				icon="📂"
				title="暂无分类"
				description="点击右上角添加分类"
			></empty-state>

			<!-- 设计稿05：粉彩四列分类网格，点击编辑、长按删除 -->
			<view v-else>
				<view class="category-grid">
					<view
						v-for="(item, idx) in filteredList"
						:key="item.id"
						class="category-cell"
						@click="showEdit(item)"
						@longpress="handleDelete(item.id)"
					>
						<view class="category-icon" :class="'cat-palette-' + (idx % 7)">
							<text class="category-icon-text">{{ getCategoryEmoji(item.name) }}</text>
						</view>
						<text class="category-name">{{ item.name }}</text>
					</view>
				</view>
				<text class="grid-hint">长按分类可删除</text>
			</view>
		</scroll-view>
		<TabBar currentPage="pages/categories/index" fab />

		<!-- 新增/编辑弹窗 -->
		<view v-if="modalOpen" class="modal-overlay" @click="modalOpen = false">
			<view class="modal-content" @click.stop>
				<view class="modal-header">
					<text class="modal-title">{{ editing ? '编辑分类' : '新增分类' }}</text>
					<text class="modal-close" @click="modalOpen = false">✕</text>
				</view>

				<view class="form-group">
					<text class="form-label">分类名称</text>
					<input class="form-input" v-model="form.name" placeholder="请输入分类名称" placeholder-class="placeholder" />
				</view>

				<view class="form-group">
					<text class="form-label">分类类型</text>
					<view class="type-options">
						<view class="type-option" :class="{ active: form.type === 0 }" @click="form.type = 0">
							<text class="type-text" :class="{ active: form.type === 0 }">支出</text>
						</view>
						<view class="type-option" :class="{ active: form.type === 1 }" @click="form.type = 1">
							<text class="type-text" :class="{ active: form.type === 1 }">收入</text>
						</view>
					</view>
				</view>

				<view class="modal-actions">
					<view class="cancel-btn" @click="modalOpen = false">
						<text class="cancel-btn-text">取消</text>
					</view>
					<view class="confirm-btn" @click="handleOk">
						<text class="confirm-btn-text">确定</text>
					</view>
				</view>
			</view>
		</view>
	</view>
</template>

<script>
import { getCategoryList, addCategory, updateCategory, deleteCategory } from '../../api/category'
import EmptyState from '../../components/EmptyState.vue'
import SkeletonCard from '../../components/SkeletonCard.vue'

export default {
	components: {
		EmptyState,
		SkeletonCard,
	},
	data() {
		return {
			statusBarHeight: 20,
			list: [],
			loading: false,
			modalOpen: false,
			editing: null,
			viewType: 0,
			form: {
				name: '',
				type: 0,
			}
		}
	},
	computed: {
		// 仅视图筛选，不改变任何请求与数据流
		filteredList() {
			return this.list.filter(item => item.type === this.viewType)
		},
	},
	onLoad() {
		const systemInfo = uni.getSystemInfoSync()
		this.statusBarHeight = systemInfo.statusBarHeight || 20
	},
	onShow() {
		// 未登录/登录过期由 App.vue onLaunch 与 request.js 的全局 401 拦截统一处理，
		// 此处不再主动 reLaunch，避免启动瞬间多个页面同时跳转造成 "do not operate continuously" 卡死。
		const token = uni.getStorageSync('token')
		if (!token) {
			return
		}
		this.fetchList()
	},
	methods: {
		// 纯展示辅助：分类名映射图标（与 add-edit 页保持一致）
		getCategoryEmoji(name) {
			const map = {
				'餐饮': '🍜', '交通': '🚗', '购物': '🛒', '娱乐': '🎮', '医疗': '💊',
				'教育': '📚', '住房': '🏠', '通讯': '📱', '服饰': '👔', '运动': '⚽',
				'旅行': '✈️', '礼物': '🎁', '其他': '📦', '宠物': '🐾', '居家': '🏡',
				'学习': '📖', '人情': '🧧',
				'工资': '💰', '奖金': '🏆', '兼职': '💼', '投资': '📈', '红包': '🧧',
				'其他收入': '💵',
			}
			return map[name] || '📝'
		},
		async fetchList() {
			this.loading = true
			try {
				const res = await getCategoryList()
				if (res.code === 200) this.list = res.data
			} catch (e) {
				console.error(e)
			} finally {
				this.loading = false
			}
		},
		showAdd() {
			this.editing = null
			this.form = { name: '', type: 0 }
			this.modalOpen = true
		},
		showEdit(item) {
			this.editing = item
			this.form = { name: item.name, type: item.type }
			this.modalOpen = true
		},
		async handleOk() {
			if (!this.form.name) {
				uni.showToast({ title: '请输入分类名称', icon: 'none' })
				return
			}
			try {
				let res
				if (this.editing) {
					res = await updateCategory(this.editing.id, this.form)
				} else {
					res = await addCategory(this.form)
				}
				if (res.code === 200) {
					uni.showToast({ title: this.editing ? '修改成功' : '新增成功', icon: 'success' })
					this.modalOpen = false
					this.fetchList()
				} else {
					uni.showToast({ title: res.message, icon: 'none' })
				}
			} catch (e) {
				uni.showToast({ title: '操作失败', icon: 'none' })
			}
		},
		handleDelete(id) {
			uni.showModal({
				title: '确认删除',
				content: '删除后关联账单的分类名称将保留，确定删除？',
				success: async (res) => {
					if (res.confirm) {
						try {
							const result = await deleteCategory(id)
							if (result.code === 200) {
								uni.showToast({ title: '删除成功', icon: 'success' })
								this.fetchList()
							} else {
								uni.showToast({ title: result.message, icon: 'none' })
							}
						} catch (e) {
							uni.showToast({ title: '删除失败', icon: 'none' })
						}
					}
				}
			})
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
}

.status-bar {
	width: 100%;
	background-color: var(--color-bg);
}

/* 设计稿05：白色胶囊圆形添加按钮 */
.add-btn {
	width: 76rpx;
	height: 76rpx;
	border-radius: var(--radius-full);
	background-color: var(--color-surface);
	box-shadow: var(--shadow-xs);
	display: flex;
	align-items: center;
	justify-content: center;
}

.add-icon {
	font-size: var(--font-2xl);
	color: var(--color-text);
}

/* ── 顶部操作栏（设计稿05：左大标题 + 右操作） ── */
.page-top-bar {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: var(--space-lg) var(--space-2xl) var(--space-md);
}

.page-title {
	font-size: 52rpx;
	font-weight: var(--weight-extrabold);
	color: var(--color-text-heading);
}

/* 设计稿02/05：灰底胶囊分段控件 */
.type-tabs {
	display: flex;
	margin: 0 var(--space-2xl) var(--space-md);
	padding: 6rpx;
	gap: 8rpx;
	border-radius: var(--radius-full);
	background-color: var(--color-surface-raised);
	width: 360rpx;
	box-sizing: border-box;
}

.type-tab {
	flex: 1;
	height: 68rpx;
	border-radius: var(--radius-full);
	background-color: transparent;
	display: flex;
	align-items: center;
	justify-content: center;
	transition: background-color 0.2s var(--ease-out-expo);
}

.type-tab.active {
	background-color: var(--color-primary);
}

.type-tab-text {
	font-size: var(--font-base);
	font-weight: var(--weight-medium);
	color: var(--color-text-secondary);
}

.type-tab-text.active {
	color: var(--color-text-inverse);
	font-weight: var(--weight-semibold);
}

.scroll-content {
	flex: 1;
	box-sizing: border-box;
	padding: var(--space-md) var(--space-xl) calc(var(--space-4xl) + 240rpx);
	-webkit-overflow-scrolling: touch;
}

.skeleton-list {
	/* Skeleton cards rendered here */
}

/* ── 设计稿05：粉彩四列网格 ── */
.category-grid {
	display: flex;
	flex-wrap: wrap;
}

.category-cell {
	display: flex;
	flex-direction: column;
	align-items: center;
	width: 25%;
	padding: var(--space-lg) 0;
	border-radius: var(--radius-lg);
	-webkit-tap-highlight-color: transparent;
}

.category-cell:active {
	opacity: 0.7;
}

.category-icon {
	width: 96rpx;
	height: 96rpx;
	border-radius: 32rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	margin-bottom: var(--space-sm);
}

.category-icon.cat-palette-0 { background-color: var(--cat-yellow); }
.category-icon.cat-palette-1 { background-color: var(--cat-pink); }
.category-icon.cat-palette-2 { background-color: var(--cat-blue); }
.category-icon.cat-palette-3 { background-color: var(--cat-orange); }
.category-icon.cat-palette-4 { background-color: var(--cat-green); }
.category-icon.cat-palette-5 { background-color: var(--cat-purple); }
.category-icon.cat-palette-6 { background-color: var(--cat-gray); }

.category-icon-text {
	font-size: var(--font-2xl);
}

.category-name {
	font-size: var(--font-sm);
	color: var(--color-text-secondary);
	text-align: center;
	max-width: 140rpx;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

/* 设计稿05：网格下方灰色提示文案 */
.grid-hint {
	display: block;
	margin-top: var(--space-lg);
	padding-left: var(--space-sm);
	font-size: var(--font-sm);
	color: var(--color-text-tertiary);
}

/* ── 弹窗（设计稿08 底部弹层风格） ── */
.modal-overlay {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background-color: rgba(0, 0, 0, 0.45);
	display: flex;
	align-items: flex-end;
	z-index: var(--z-modal);
	animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
	from { opacity: 0; }
	to { opacity: 1; }
}

.modal-content {
	background-color: var(--color-surface);
	border-radius: var(--radius-3xl) var(--radius-3xl) 0 0;
	padding: var(--space-3xl) var(--space-3xl) calc(var(--space-3xl) + env(safe-area-inset-bottom));
	width: 100%;
	animation: slideUp 0.25s var(--ease-out-expo);
}

@keyframes slideUp {
	from { transform: translateY(100%); }
	to { transform: translateY(0); }
}

.modal-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: var(--space-xl);
}

.modal-title {
	font-size: var(--font-2xl);
	font-weight: var(--weight-extrabold);
	color: var(--color-text-heading);
}

.modal-close {
	font-size: var(--font-2xl);
	color: var(--color-text-secondary);
}

.form-group {
	margin-bottom: var(--space-lg);
}

.form-label {
	font-size: var(--font-md);
	font-weight: var(--weight-medium);
	color: var(--color-text);
	margin-bottom: var(--space-sm);
	display: block;
}

/* 设计稿01/08：无边框灰底圆角输入 */
.form-input {
	height: 96rpx;
	border: none;
	border-radius: var(--radius-lg);
	padding: 0 var(--space-xl);
	font-size: var(--font-base);
	color: var(--color-text);
	background-color: var(--color-surface-raised);
}

.placeholder {
	color: var(--color-text-tertiary);
}

.type-options {
	display: flex;
	gap: var(--space-md);
	padding: 6rpx;
	border-radius: var(--radius-full);
	background-color: var(--color-surface-raised);
}

.type-option {
	flex: 1;
	height: 72rpx;
	border-radius: var(--radius-full);
	background-color: transparent;
	display: flex;
	align-items: center;
	justify-content: center;
	transition: background-color 0.2s var(--ease-out-expo);
}

.type-option.active {
	background-color: var(--color-primary);
}

.type-text {
	font-size: var(--font-md);
	color: var(--color-text-secondary);
	font-weight: var(--weight-medium);
}

.type-text.active {
	color: var(--color-text-inverse);
	font-weight: var(--weight-semibold);
}

.modal-actions {
	display: flex;
	gap: var(--space-md);
	margin-top: var(--space-2xl);
}

.cancel-btn {
	flex: 1;
	height: 96rpx;
	border-radius: var(--radius-full);
	background-color: var(--color-surface-raised);
	display: flex;
	align-items: center;
	justify-content: center;
}

.cancel-btn-text {
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
	color: var(--color-text-secondary);
}

.confirm-btn {
	flex: 1;
	height: 96rpx;
	border-radius: var(--radius-full);
	background-color: var(--color-primary);
	box-shadow: var(--shadow-primary);
	display: flex;
	align-items: center;
	justify-content: center;
}

.confirm-btn-text {
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
	color: var(--color-text-inverse);
}
</style>
