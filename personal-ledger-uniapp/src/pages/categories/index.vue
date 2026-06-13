<template>
	<view class="container">
		<!-- 状态栏占位 -->
		<view class="status-bar" :style="{ height: statusBarHeight + 'px' }"></view>
		<view class="page-top-bar">
			<view class="add-btn" @click="showAdd">
				<text class="add-icon">+</text>
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
				v-else-if="list.length === 0"
				icon="📂"
				title="暂无分类"
				description="点击右上角添加分类"
			></empty-state>

			<!-- Category list -->
			<view v-else>
				<view v-for="item in list" :key="item.id" class="category-item">
					<view class="category-info">
						<view class="category-icon" :class="item.type === 0 ? 'type-expense' : 'type-income'">
							<text class="category-icon-text">{{ item.type === 0 ? '↑' : '↓' }}</text>
						</view>
						<view>
							<text class="category-name">{{ item.name }}</text>
							<text class="category-type">{{ item.type === 0 ? '支出' : '收入' }}</text>
						</view>
					</view>
					<view class="category-actions">
						<view class="action-btn edit" @click="showEdit(item)">
							<text class="action-text">编辑</text>
						</view>
						<view class="action-btn delete" @click="handleDelete(item.id)">
							<text class="action-text delete">删除</text>
						</view>
					</view>
				</view>
			</view>
		</scroll-view>
		<TabBar currentPage="pages/categories/index" />

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
			form: {
				name: '',
				type: 0,
			}
		}
	},
	onLoad() {
		const systemInfo = uni.getSystemInfoSync()
		this.statusBarHeight = systemInfo.statusBarHeight || 20
	},
	onShow() {
		this.fetchList()
	},
	methods: {
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
	background-color: var(--color-surface);
}

.add-btn {
	width: 72rpx;
	height: 72rpx;
	border-radius: 36rpx;
	background-color: var(--color-primary);
	display: flex;
	align-items: center;
	justify-content: center;
	box-shadow: var(--shadow-primary);
}

.add-icon {
	font-size: var(--font-2xl);
	color: var(--color-text-inverse);
}

/* ── 顶部操作栏 ── */
.page-top-bar {
	display: flex;
	justify-content: flex-end;
	padding: var(--space-3xl) var(--space-xl) var(--space-md);
}

.scroll-content {
	flex: 1;
	box-sizing: border-box;
	padding: var(--space-xl) var(--space-xl) calc(var(--space-4xl) + 100rpx);
	-webkit-overflow-scrolling: touch;
}

.skeleton-list {
	/* Skeleton cards rendered here */
}

.category-item {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	background-color: var(--color-surface);
	padding: var(--space-md);
	margin-bottom: var(--space-md);
	border-radius: var(--radius-xl);
	box-shadow: var(--shadow-sm);
	gap: var(--space-sm);
}

.category-info {
	display: flex;
	align-items: center;
	flex: 1;
	min-width: 0;
}

.category-icon {
	width: 64rpx;
	height: 64rpx;
	border-radius: var(--radius-lg);
	display: flex;
	align-items: center;
	justify-content: center;
	margin-right: var(--space-lg);
}

.category-icon.type-expense {
	background-color: var(--color-danger-light);
}

.category-icon.type-income {
	background-color: var(--color-success-light);
}

.category-icon-text {
	font-size: var(--font-base);
	font-weight: var(--weight-bold);
}

.category-icon.type-expense .category-icon-text {
	color: var(--color-danger);
}

.category-icon.type-income .category-icon-text {
	color: var(--color-success);
}

.category-name {
	font-size: var(--font-md);
	font-weight: var(--weight-semibold);
	color: var(--color-text);
	display: block;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	max-width: 280rpx;
}

.category-type {
	font-size: var(--font-xs);
	color: var(--color-text-secondary);
	margin-top: var(--space-2xs);
	display: block;
}

.category-actions {
	display: flex;
	gap: var(--space-xs);
	flex-shrink: 0;
	margin-left: var(--space-xs);
}

.action-btn {
	padding: 10rpx 16rpx;
	border-radius: var(--radius-sm);
	display: flex;
	align-items: center;
	justify-content: center;
	min-width: 82rpx;
}

.action-btn.edit {
	background-color: var(--color-border);
}

.action-btn.delete {
	background-color: var(--color-danger-light);
}

.action-text {
	font-size: var(--font-xs);
	font-weight: var(--weight-medium);
	color: var(--color-text-secondary);
}

.action-text.delete {
	color: var(--color-danger);
}

.modal-overlay {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background-color: rgba(0, 0, 0, 0.5);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: var(--z-modal);
}

.modal-content {
	background-color: var(--color-surface);
	border-radius: var(--radius-2xl);
	padding: var(--space-3xl);
	width: 80%;
}

.modal-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: var(--space-xl);
}

.modal-title {
	font-size: var(--font-2xl);
	font-weight: var(--weight-bold);
	color: var(--color-text);
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

.form-input {
	height: 80rpx;
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

.type-options {
	display: flex;
	gap: var(--space-md);
}

.type-option {
	flex: 1;
	height: 72rpx;
	border-radius: var(--radius-md);
	background-color: var(--color-border);
	display: flex;
	align-items: center;
	justify-content: center;
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
	margin-top: var(--space-xl);
}

.cancel-btn {
	flex: 1;
	height: 80rpx;
	border-radius: var(--radius-md);
	background-color: var(--color-border);
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
	height: 80rpx;
	border-radius: var(--radius-md);
	background-color: var(--color-primary);
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
