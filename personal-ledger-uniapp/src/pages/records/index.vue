<template>
	<view class="container">
		<!-- 状态栏占位 -->
		<view class="status-bar" :style="{ height: statusBarHeight + 'px' }"></view>
		<view class="page-top-bar">
			<view class="top-bar-actions">
				<view class="filter-btn" :class="{ active: filterCategory }" @click="showFilter">
					<text class="filter-icon">⚲</text>
				</view>
				<view class="add-btn" @click="goAdd">
					<text class="add-icon">+</text>
				</view>
			</view>
		</view>

		<view v-if="filterCategory" class="active-filter">
			<text class="filter-text">筛选：{{ getFilterCategoryName() }}</text>
			<text class="filter-close" @click="resetFilter">✕</text>
		</view>

		<scroll-view scroll-y class="scroll-content" @scrolltolower="loadMore" :refresher-enabled="true" :refresher-triggered="refreshing" @refresherrefresh="onRefresh">
			<view v-if="loading && records.length === 0" class="skeleton-list">
				<skeleton-card :lines="2" style="margin-bottom: 16rpx;"></skeleton-card>
				<skeleton-card :lines="2" style="margin-bottom: 16rpx;"></skeleton-card>
				<skeleton-card :lines="2" style="margin-bottom: 16rpx;"></skeleton-card>
				<skeleton-card :lines="2"></skeleton-card>
			</view>

			<empty-state
				v-else-if="groupedRecords.length === 0 && !loading"
				icon="📄"
				title="暂无账单记录"
				description="点击下方按钮开始记账"
			>
				<template #action>
					<view class="empty-btn" @click="goAdd">
						<text class="empty-btn-text">记一笔</text>
					</view>
				</template>
			</empty-state>

			<view v-else>
				<view v-for="group in groupedRecords" :key="group.date" class="section">
					<view class="section-header">
						<view class="section-left">
							<view class="date-badge" :class="{ today: group.isToday }">
								<text class="date-day" :class="{ today: group.isToday }">{{ group.day }}</text>
							</view>
							<view>
								<text class="section-date">{{ group.date }}</text>
								<text class="section-day">{{ group.dayOfWeek }}{{ group.isToday ? ' · 今天' : '' }}</text>
							</view>
						</view>
						<view class="section-summary">
							<view v-if="group.totalIncome > 0" class="summary-item">
								<text class="summary-income">+ ¥{{ formatAmount(group.totalIncome) }}</text>
							</view>
							<view v-if="group.totalExpense > 0" class="summary-item">
								<text class="summary-expense">− ¥{{ formatAmount(group.totalExpense) }}</text>
							</view>
						</view>
					</view>

					<record-card
						v-for="item in group.records"
						:key="item.id"
						:record="item"
						@edit="goEdit"
						@delete="handleDelete"
					></record-card>
				</view>
			</view>

			<view v-if="loading && records.length > 0" class="loading-more">
				<text>加载中...</text>
			</view>

			<view v-if="current >= pages && records.length > 0" class="no-more">
				<text>没有更多了</text>
			</view>
		</scroll-view>
		<TabBar currentPage="pages/records/index" />

		<!-- 筛选弹窗 -->
		<view v-if="filterOpen" class="modal-overlay" @click="filterOpen = false">
			<view class="modal-content" @click.stop>
				<view class="modal-header">
					<text class="modal-title">筛选条件</text>
					<text class="modal-close" @click="filterOpen = false">✕</text>
				</view>

				<text class="filter-label">分类</text>
				<view class="filter-options">
					<view class="filter-option" :class="{ active: !filterCategory }" @click="handleFilter(null)">
						<text class="filter-option-text" :class="{ active: !filterCategory }">全部</text>
					</view>
					<view v-for="c in categories" :key="c.id" class="filter-option" :class="{ active: filterCategory === c.id }" @click="handleFilter(c.id)">
						<text class="filter-option-text" :class="{ active: filterCategory === c.id }">{{ c.name }}</text>
					</view>
				</view>

				<view class="modal-actions">
					<view class="reset-btn" @click="resetFilter">
						<text class="reset-btn-text">重置</text>
					</view>
					<view class="apply-btn" @click="filterOpen = false">
						<text class="apply-btn-text">确定</text>
					</view>
				</view>
			</view>
		</view>
	</view>
</template>

<script>
import { getRecordPage, deleteRecord } from '../../api/record'
import { getCategoryList } from '../../api/category'
import { formatAmount } from '../../utils/format'
import RecordCard from '../../components/RecordCard.vue'
import EmptyState from '../../components/EmptyState.vue'
import SkeletonCard from '../../components/SkeletonCard.vue'

export default {
	components: {
		RecordCard,
		EmptyState,
		SkeletonCard,
	},
	data() {
		return {
			statusBarHeight: 20,
			records: [],
			total: 0,
			pages: 0,
			current: 1,
			size: 20,
			loading: false,
			refreshing: false,
			categories: [],
			filterOpen: false,
			filterCategory: null,
		}
	},
	onLoad() {
		const systemInfo = uni.getSystemInfoSync()
		this.statusBarHeight = systemInfo.statusBarHeight || 20
	},
	computed: {
		groupedRecords() {
			const groups = {}
			for (const r of this.records) {
				if (!groups[r.recordDate]) groups[r.recordDate] = []
				groups[r.recordDate].push(r)
			}
			const today = new Date().toISOString().split('T')[0]
			return Object.entries(groups)
				.sort(([a], [b]) => b.localeCompare(a))
				.map(([date, items]) => {
					const d = new Date(date)
					const dayOfWeek = ['日', '一', '二', '三', '四', '五', '六'][d.getDay()]
					const totalIncome = items.filter(i => i.categoryType === 1).reduce((s, i) => s + i.amount, 0)
					const totalExpense = items.filter(i => i.categoryType === 0).reduce((s, i) => s + i.amount, 0)
					return {
						date,
						day: String(d.getDate()).padStart(2, '0'),
						dayOfWeek: '周' + dayOfWeek,
						isToday: date === today,
						totalIncome,
						totalExpense,
						records: items,
					}
				})
		}
	},
	onShow() {
		this.fetchCategories()
		this.fetchData({ page: 1, size: this.size })
	},
	methods: {
		formatAmount,
		async fetchCategories() {
			try {
				const res = await getCategoryList()
				if (res.code === 200) this.categories = res.data
			} catch (e) {}
		},
		async fetchData(params, append = false) {
			this.loading = true
			try {
				const res = await getRecordPage(params)
				if (res.code === 200) {
					if (append && params.page > 1) {
						this.records = [...this.records, ...res.data.records]
					} else {
						this.records = res.data.records
					}
					this.total = res.data.total
					this.pages = res.data.pages
					this.current = res.data.current
				}
			} catch (e) {
				console.error(e)
			} finally {
				this.loading = false
				this.refreshing = false
			}
		},
		onRefresh() {
			this.refreshing = true
			this.fetchData({ page: 1, size: this.size })
		},
		loadMore() {
			if (this.loading || this.current >= this.pages) return
			const params = { page: this.current + 1, size: this.size }
			if (this.filterCategory) params.categoryId = this.filterCategory
			this.fetchData(params, true)
		},
		showFilter() {
			this.filterOpen = true
		},
		handleFilter(categoryId) {
			this.filterOpen = false
			this.filterCategory = categoryId
			const params = { page: 1, size: this.size }
			if (categoryId) params.categoryId = categoryId
			this.fetchData(params)
		},
		resetFilter() {
			this.filterCategory = null
			this.filterOpen = false
			this.fetchData({ page: 1, size: this.size })
		},
		getFilterCategoryName() {
			const c = this.categories.find(c => c.id === this.filterCategory)
			return c ? c.name : ''
		},
		goAdd() {
			uni.navigateTo({ url: '/pages/records/add-edit' })
		},
		goEdit(item) {
			uni.navigateTo({ url: '/pages/records/add-edit?id=' + item.id })
		},
		handleDelete(id) {
			uni.showModal({
				title: '确认删除',
				content: '确定要删除该账单记录吗？',
				success: async (res) => {
					if (res.confirm) {
						try {
							const result = await deleteRecord(id)
							if (result.code === 200) {
								uni.showToast({ title: '删除成功', icon: 'success' })
								this.fetchData({ page: 1, size: this.size })
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

/* ── 顶部操作栏 ── */
.page-top-bar {
	display: flex;
	justify-content: flex-end;
	padding: var(--space-md) var(--space-xl) var(--space-md);
	background-color: var(--color-surface);
}

.top-bar-actions {
	display: flex;
	align-items: center;
	gap: var(--space-md);
}

.filter-btn {
	width: 68rpx;
	height: 68rpx;
	border-radius: var(--radius-full);
	background-color: var(--color-border);
	display: flex;
	align-items: center;
	justify-content: center;
	transition:
		background-color var(--transition-fast),
		transform var(--transition-spring);
}

.filter-btn.active {
	background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
}

.filter-btn:active {
	transform: scale(0.92);
}

.filter-icon {
	font-size: var(--font-xl);
	opacity: 0.7;
}

.filter-btn.active .filter-icon {
	opacity: 1;
}

.add-btn {
	width: 68rpx;
	height: 68rpx;
	border-radius: var(--radius-full);
	background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
	display: flex;
	align-items: center;
	justify-content: center;
	box-shadow: var(--shadow-accent);
	transition: transform var(--transition-spring);
}

.add-btn:active {
	transform: scale(0.92);
}

.add-icon {
	font-size: var(--font-2xl);
	color: var(--color-text-inverse);
	font-weight: var(--weight-bold);
	line-height: 1;
}

/* ── 活动筛选标签 ── */
.active-filter {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: var(--space-md) var(--space-3xl);
	background-color: var(--color-warning-light);
	border-bottom: 1rpx solid rgba(243, 156, 18, 0.15);
	animation: slideDown var(--transition-normal);
}

@keyframes slideDown {
	from { opacity: 0; transform: translateY(-8rpx); }
	to { opacity: 1; transform: translateY(0); }
}

.filter-text {
	font-size: var(--font-sm);
	color: var(--color-warning-text);
	font-weight: var(--weight-medium);
}

.filter-close {
	font-size: var(--font-base);
	color: var(--color-text-secondary);
	font-weight: var(--weight-bold);
	padding: var(--space-xs);
}

/* ── 滚动区域 ── */
.scroll-content {
	flex: 1;
	box-sizing: border-box;
	padding: 0 var(--space-xl) calc(var(--space-4xl) + 100rpx);
	-webkit-overflow-scrolling: touch;
}

.skeleton-list {
	padding-top: var(--space-xl);
}

/* ── 日期分组 ── */
.section {
	padding-top: var(--space-2xl);
}

.section:first-child {
	padding-top: var(--space-xl);
}

/* ── 分组头部 ── */
.section-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding-bottom: var(--space-lg);
}

.section-left {
	display: flex;
	align-items: center;
	flex: 1;
	min-width: 0;
	padding-right: var(--space-sm);
}

.date-badge {
	width: 72rpx;
	height: 72rpx;
	border-radius: var(--radius-xl);
	background-color: var(--color-border);
	display: flex;
	align-items: center;
	justify-content: center;
	margin-right: var(--space-md);
	transition:
		background-color var(--transition-fast),
		transform var(--transition-fast);
}

.date-badge.today {
	background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
	box-shadow: var(--shadow-accent);
}

.date-day {
	font-size: var(--font-xl);
	font-weight: var(--weight-extrabold);
	color: var(--color-text-secondary);
}

.date-day.today {
	color: var(--color-text-inverse);
}

.section-date {
	font-size: var(--font-base);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	display: block;
	letter-spacing: var(--tracking-heading);
}

.section-day {
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
	margin-top: var(--space-2xs);
	display: block;
	font-weight: var(--weight-medium);
}

.section-summary {
	display: flex;
	flex-direction: column;
	align-items: flex-end;
	gap: var(--space-2xs);
	flex-shrink: 0;
	margin-left: var(--space-md);
}

.summary-income {
	font-size: var(--font-sm);
	color: var(--color-success);
	font-weight: var(--weight-bold);
	white-space: nowrap;
}

.summary-expense {
	font-size: var(--font-sm);
	color: var(--color-danger);
	font-weight: var(--weight-bold);
	white-space: nowrap;
}

/* ── 空状态按钮 ── */
.empty-btn {
	display: inline-flex;
	align-items: center;
	background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
	padding: var(--space-lg) 44rpx;
	border-radius: var(--radius-xl);
	box-shadow: var(--shadow-accent);
	transition: transform var(--transition-spring);
}

.empty-btn:active {
	transform: scale(0.96);
}

.empty-btn-text {
	color: var(--color-text-inverse);
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
}

/* ── 加载 / 无更多 ── */
.loading-more,
.no-more {
	text-align: center;
	padding: var(--space-xl) 0;
	color: var(--color-text-tertiary);
	font-size: var(--font-sm);
}

/* ── 弹窗 ── */
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
	animation: fadeIn var(--transition-fast);
}

@keyframes fadeIn {
	from { opacity: 0; }
	to { opacity: 1; }
}

.modal-content {
	background-color: var(--color-surface);
	border-radius: var(--radius-3xl) var(--radius-3xl) 0 0;
	padding: var(--space-3xl);
	width: 100%;
	max-height: 70vh;
	animation: slideUp var(--transition-normal);
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
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	letter-spacing: var(--tracking-heading);
}

.modal-close {
	font-size: var(--font-2xl);
	color: var(--color-text-secondary);
	padding: var(--space-xs);
}

.filter-label {
	font-size: var(--font-md);
	font-weight: var(--weight-semibold);
	color: var(--color-text);
	margin-bottom: var(--space-lg);
	display: block;
}

.filter-options {
	display: flex;
	flex-wrap: wrap;
	gap: var(--space-md);
	margin-bottom: var(--space-3xl);
}

.filter-option {
	padding: var(--space-md) var(--space-lg);
	border-radius: var(--radius-md);
	background-color: var(--color-border);
	transition:
		background-color var(--transition-fast),
		transform var(--transition-fast);
}

.filter-option:active {
	transform: scale(0.95);
}

.filter-option.active {
	background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
}

.filter-option-text {
	font-size: var(--font-md);
	color: var(--color-text-secondary);
	font-weight: var(--weight-medium);
}

.filter-option-text.active {
	color: var(--color-text-inverse);
	font-weight: var(--weight-semibold);
}

/* ── 弹窗按钮 ── */
.modal-actions {
	display: flex;
	gap: var(--space-lg);
}

.reset-btn {
	flex: 1;
	height: 88rpx;
	border-radius: var(--radius-lg);
	background-color: var(--color-border);
	display: flex;
	align-items: center;
	justify-content: center;
	transition:
		background-color var(--transition-fast),
		transform var(--transition-fast);
}

.reset-btn:active {
	background-color: var(--color-border-input);
	transform: scale(0.97);
}

.reset-btn-text {
	font-size: var(--font-lg);
	font-weight: var(--weight-semibold);
	color: var(--color-text-secondary);
}

.apply-btn {
	flex: 2;
	height: 88rpx;
	border-radius: var(--radius-lg);
	background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
	display: flex;
	align-items: center;
	justify-content: center;
	box-shadow: var(--shadow-accent);
	transition: transform var(--transition-spring);
}

.apply-btn:active {
	transform: scale(0.97);
}

.apply-btn-text {
	font-size: var(--font-lg);
	font-weight: var(--weight-semibold);
	color: var(--color-text-inverse);
}
</style>
