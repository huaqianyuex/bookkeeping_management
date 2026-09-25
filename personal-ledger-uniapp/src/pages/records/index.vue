<template>
	<view class="container">
		<!-- 状态栏占位 -->
		<view class="status-bar" :style="{ height: statusBarHeight + 'px' }"></view>
		<view class="page-top-bar">
			<!-- 设计稿03：左侧大标题 -->
			<text class="page-title">账单</text>
			<view class="top-bar-actions">
				<view class="filter-btn" :class="{ active: filterCategory }" @click="showFilter">
					<app-icon name="filter" :size="36"></app-icon>
				</view>
			</view>
		</view>

		<!-- 本月累计行情条：流水页的全局锚点 -->
		<view class="month-strip">
			<view class="strip-item">
				<text class="strip-label">本月收入</text>
				<text class="strip-value is-income">¥{{ formatAmount(monthTotals.income) }}</text>
			</view>
			<view class="strip-item">
				<text class="strip-label">本月支出</text>
				<text class="strip-value is-expense">¥{{ formatAmount(monthTotals.expense) }}</text>
			</view>
			<view class="strip-item">
				<text class="strip-label">结余</text>
				<text class="strip-value">¥{{ formatAmount(monthTotals.income - monthTotals.expense) }}</text>
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

			<!-- 加载失败 ≠ 没有账单：错误态明确区分，避免弱网用户误以为账全没了 -->
			<empty-state
				v-else-if="loadError && !loading"
				mode="error"
				title="账单加载失败"
				description="网络似乎不太顺畅，你的账单都还在"
			>
				<template #action>
					<view class="empty-btn" @click="retryFetch">
						<text class="empty-btn-text">重新加载</text>
					</view>
				</template>
			</empty-state>

			<empty-state
				v-else-if="groupedRecords.length === 0 && !loading"
				icon="receipt"
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
								<text class="section-date">{{ group.dateLabel }}</text>
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

					<!-- 设计稿03：同组账单合并在一张白卡内 -->
					<view class="list-card">
						<record-card
							v-for="item in group.records"
							:key="item.id"
							:record="item"
							@edit="goEdit"
							@delete="handleDelete"
						></record-card>
					</view>
				</view>
			</view>

			<view v-if="loading && records.length > 0" class="loading-more">
				<text>加载中...</text>
			</view>

			<view v-if="current >= pages && records.length > 0" class="no-more">
				<text>没有更多了</text>
			</view>
		</scroll-view>
		<TabBar currentPage="pages/records/index" fab />

		<!-- 筛选弹窗 -->
		<view v-if="filterOpen" class="modal-overlay" @click="filterOpen = false">
			<view class="modal-content" @click.stop>
				<view class="modal-header">
					<text class="modal-title">筛选条件</text>
					<text class="modal-close" @click="filterOpen = false">✕</text>
				</view>

				<text class="filter-label">分类</text>
				<!-- 选项多时可滚动，不让弹窗被撑爆 -->
				<scroll-view class="filter-options-scroll" scroll-y>
					<view class="filter-options">
						<view class="filter-option" :class="{ active: draftFilter === null }" @click="draftFilter = null">
							<text class="filter-option-text" :class="{ active: draftFilter === null }">全部</text>
						</view>
						<view v-for="c in categories" :key="c.id" class="filter-option" :class="{ active: draftFilter === c.id }" @click="draftFilter = c.id">
							<text class="filter-option-text" :class="{ active: draftFilter === c.id }">{{ c.name }}</text>
						</view>
					</view>
				</scroll-view>

				<view class="modal-actions">
					<view class="reset-btn" @click="resetFilter">
						<text class="reset-btn-text">重置</text>
					</view>
					<view class="apply-btn" @click="applyFilter">
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
import { getMonthlyStatistics } from '../../api/statistics'
import { formatAmount } from '../../utils/format'
import { useLedgerStore } from '../../utils/store'
import RecordCard from '../../components/RecordCard.vue'
import EmptyState from '../../components/EmptyState.vue'
import SkeletonCard from '../../components/SkeletonCard.vue'
import AppIcon from '../../components/AppIcon.vue'

export default {
	components: {
		RecordCard,
		EmptyState,
		SkeletonCard,
		AppIcon,
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
			loadError: false,
			categories: [],
			// 本月累计（行情条数据），加载失败静默保持 0
			monthTotals: { income: 0, expense: 0 },
			filterOpen: false,
			filterCategory: null,
			// 弹窗内的暂选分类：点选项不关弹窗，「确定」才真正生效
			draftFilter: null,
		}
	},
	onLoad() {
		const systemInfo = uni.getSystemInfoSync()
		this.statusBarHeight = systemInfo.statusBarHeight || 20
	},
	computed: {
		// 缓存键跟随筛选状态，切换筛选不串缓存
		cacheKey() {
			return this.filterCategory ? String(this.filterCategory) : 'all'
		},
		groupedRecords() {
			const groups = {}
			for (const r of this.records) {
				// recordDate 可能是纯日期或带时间的 ISO 串，统一截取日期部分分组
				const dateKey = String(r.recordDate || '').slice(0, 10)
				if (!dateKey) continue
				if (!groups[dateKey]) groups[dateKey] = []
				groups[dateKey].push(r)
			}
			// 本地时区的「今天」，不能用 toISOString（UTC 会在东八区 0-8 点标错昨天）
			const now = new Date()
			const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
			return Object.entries(groups)
				.sort(([a], [b]) => b.localeCompare(a))
				.map(([date, items]) => {
					const d = new Date(date)
					const dayOfWeek = ['日', '一', '二', '三', '四', '五', '六'][d.getDay()]
					const totalIncome = items.filter(i => i.categoryType === 1).reduce((s, i) => s + (Number(i.amount) || 0), 0)
					const totalExpense = items.filter(i => i.categoryType === 0).reduce((s, i) => s + (Number(i.amount) || 0), 0)
					return {
						date,
						dateLabel: `${Number(date.slice(5, 7))}月${Number(date.slice(8, 10))}日`,
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
		// 未登录/登录过期由 App.vue onLaunch 与 request.js 的全局 401 拦截统一处理，
		// 此处不再主动 reLaunch，避免启动瞬间多个页面同时跳转造成 "do not operate continuously" 卡死。
		const token = uni.getStorageSync('token')
		if (!token) {
			return
		}
		this.fetchCategories()
		this.fetchMonthTotals()
		// stale-while-revalidate：切 tab 回来先渲染缓存，再静默刷新（仅首页时；
		// 翻过页的列表不自动刷，避免覆盖已加载的分页，需要时下拉刷新）
		const cache = useLedgerStore().records
		if (cache.key === this.cacheKey && cache.records.length > 0) {
			this.records = cache.records
			this.total = cache.total
			this.pages = cache.pages
			this.current = cache.current
			if (cache.current === 1) {
				this.fetchData(this.listParams(1), false, { silent: true })
			}
		} else {
			this.fetchData(this.listParams(1))
		}
	},
	methods: {
		formatAmount,
		/** 组装列表请求参数，统一带上当前筛选 */
		listParams(page) {
			const params = { page, size: this.size }
			if (this.filterCategory) params.categoryId = this.filterCategory
			return params
		},
		saveCache() {
			useLedgerStore().setRecordsCache({
				key: this.cacheKey,
				records: this.records,
				total: this.total,
				pages: this.pages,
				current: this.current,
				size: this.size,
			})
		},
		async fetchCategories() {
			try {
				const res = await getCategoryList()
				if (res.code === 200) this.categories = res.data
			} catch (e) {}
		},
		// 本月累计：独立于列表分页，失败不影响流水展示
		async fetchMonthTotals() {
			try {
				const now = new Date()
				const res = await getMonthlyStatistics({ year: now.getFullYear(), month: now.getMonth() + 1 })
				if (res.code === 200 && res.data) {
					this.monthTotals = {
						income: Number(res.data.totalIncome ?? res.data.total_income ?? 0) || 0,
						expense: Number(res.data.totalExpense ?? res.data.total_expense ?? 0) || 0,
					}
				}
			} catch (e) {}
		},
		async fetchData(params, append = false, { silent = false } = {}) {
			if (!silent) this.loading = true
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
					this.loadError = false
					this.saveCache()
				}
			} catch (e) {
				// 首屏且无数据时把失败与「暂无账单」区分开；
				// 已有数据时保持展示，网络提示由 request.js 统一 toast
				if (this.records.length === 0) this.loadError = true
			} finally {
				if (!silent) this.loading = false
				this.refreshing = false
			}
		},
		retryFetch() {
			this.loadError = false
			this.fetchData(this.listParams(1))
		},
		onRefresh() {
			this.refreshing = true
			this.fetchMonthTotals()
			this.fetchData(this.listParams(1))
		},
		loadMore() {
			if (this.loading || this.current >= this.pages) return
			this.fetchData(this.listParams(this.current + 1), true)
		},
		showFilter() {
			// 打开时同步当前生效的筛选为暂选值
			this.draftFilter = this.filterCategory
			this.filterOpen = true
		},
		applyFilter() {
			this.filterCategory = this.draftFilter
			this.filterOpen = false
			this.fetchData(this.listParams(1))
		},
		resetFilter() {
			this.draftFilter = null
			this.filterCategory = null
			this.filterOpen = false
			this.fetchData(this.listParams(1))
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
				content: '删除后该笔账单无法恢复，确定删除吗？',
				success: async (res) => {
					if (res.confirm) {
						try {
							const result = await deleteRecord(id)
							if (result.code === 200) {
								uni.showToast({ title: '删除成功', icon: 'success' })
								// 就地移除并停留在当前页，不再整表刷新弹回第一页
								this.records = this.records.filter(r => r.id !== id)
								this.total = Math.max(0, this.total - 1)
								if (this.records.length === 0 && this.current > 1) {
									this.fetchData(this.listParams(this.current - 1))
								} else {
									this.saveCache()
								}
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
	/* 固定视口高度：scroll-view 必须拿到有界高度才能内部滚动，
	 否则滚动落到外层页面，与下拉刷新的手势拦截互相打架导致滑动失效 */
	height: 100vh;
	background-color: var(--color-bg);
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.status-bar {
	width: 100%;
	background-color: var(--color-bg);
}

/* ── 顶部操作栏（设计稿03：左大标题 + 右操作） ── */
.page-top-bar {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: var(--space-lg) var(--space-2xl);
	background-color: var(--color-bg);
}

.page-title {
	font-size: var(--font-3xl);
	font-weight: var(--weight-extrabold);
	color: var(--color-text-heading);
	letter-spacing: var(--tracking-heading);
}

.top-bar-actions {
	display: flex;
	align-items: center;
	gap: var(--space-md);
}

/* 设计稿03：白色胶囊圆形操作按钮 */
.filter-btn {
	width: 76rpx;
	height: 76rpx;
	border-radius: var(--radius-full);
	background-color: var(--color-surface);
	box-shadow: var(--shadow-xs);
	display: flex;
	align-items: center;
	justify-content: center;
	transition:
		background-color var(--transition-fast),
		transform var(--transition-spring);
}

.filter-btn.active {
	background: var(--color-accent);
}

.filter-btn:active {
	transform: scale(0.92);
}

/* ── 本月累计行情条 ── */
.month-strip {
	display: flex;
	margin: 0 var(--space-2xl);
	padding: var(--space-md) 0;
	border-top: var(--hairline) solid var(--color-border);
	border-bottom: var(--hairline) solid var(--color-border);
}

.strip-item {
	flex: 1;
	display: flex;
	flex-direction: column;
	gap: var(--space-2xs);
	min-width: 0;
}

.strip-item + .strip-item {
	border-left: var(--hairline) solid var(--color-divider);
	padding-left: var(--space-lg);
}

.strip-label {
	font-size: var(--font-2xs);
	color: var(--color-text-tertiary);
}

.strip-value {
	font-family: var(--font-amount);
	font-size: var(--font-md);
	font-weight: var(--weight-semibold);
	color: var(--color-text-heading);
	font-variant-numeric: tabular-nums;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.strip-value.is-income {
	color: var(--color-success);
}

.strip-value.is-expense {
	color: var(--color-danger);
}

/* ── 活动筛选标签 ── */
.active-filter {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: var(--space-md) var(--space-3xl);
	background-color: var(--color-warning-light);
	 border-bottom: 1rpx solid var(--color-warning-border);
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
	/* 扩大触控区到 56rpx，避免 ✕ 点不中 */
	width: 56rpx;
	height: 56rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	margin-right: -12rpx;
}

/* ── 滚动区域 ── */
.scroll-content {
	flex: 1;
	min-height: 0;
	box-sizing: border-box;
	padding: 0 var(--space-xl) var(--page-bottom-space);
	-webkit-overflow-scrolling: touch;
	overflow: hidden;
}

.skeleton-list {
	padding-top: var(--space-xl);
}

/* ── 日期分组 ── */
.section {
	padding-top: var(--space-xl);
}

.section:first-child {
	padding-top: var(--space-md);
}

/* ── 分组头部（设计稿03：小灰字日期行） ── */
.section-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding-bottom: var(--space-md);
}

.section-left {
	display: flex;
	align-items: center;
	flex: 1;
	min-width: 0;
	padding-right: var(--space-sm);
}

/* 设计稿03：无日期方块，仅灰字日期行 */
.date-badge {
	display: none;
}

.date-day {
	font-size: var(--font-lg);
	font-weight: var(--weight-bold);
	color: var(--color-text-secondary);
}

.date-day.today {
	color: var(--color-text-secondary);
}

.section-date {
	font-size: var(--font-md);
	font-weight: var(--weight-semibold);
	color: var(--color-text-secondary);
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

/* 收入绿、支出墨黑（与行金额语义一致） */
.summary-income {
	font-family: var(--font-amount);
	font-size: var(--font-sm);
	color: var(--color-success);
	font-weight: var(--weight-semibold);
	font-variant-numeric: tabular-nums;
	white-space: nowrap;
}

.summary-expense {
	font-family: var(--font-amount);
	font-size: var(--font-sm);
	color: var(--color-text-secondary);
	font-weight: var(--weight-semibold);
	font-variant-numeric: tabular-nums;
	white-space: nowrap;
}

/* ── 同组账单：纸面上的发丝线分组，无卡片盒 ── */
.list-card {
	overflow: hidden;
}

.list-card :deep(.record-card) {
	margin-bottom: 0;
	border-radius: 0;
}

/* 行底色必须不透明（左滑删除层不能透出），纸面即底色 */
.list-card :deep(.record-main) {
	background-color: var(--color-bg);
	border: none;
	box-shadow: none;
	border-radius: 0;
	padding: var(--space-lg) var(--space-2xs);
}

/* 行间发丝线 */
.list-card :deep(.record-card + .record-card .record-main) {
	border-top: var(--hairline) solid var(--color-divider);
}

/* 组收尾发丝线：与下一组日期行分隔 */
.list-card :deep(.record-card:last-child) {
	border-bottom: var(--hairline) solid var(--color-border);
}

/* ── 空状态按钮（设计稿10：黄色胶囊「去记一笔」） ── */
.empty-btn {
	display: inline-flex;
	align-items: center;
	background: var(--color-accent);
	padding: var(--space-lg) var(--space-3xl);
	border-radius: var(--radius-full);
	box-shadow: var(--shadow-accent);
	transition: opacity var(--transition-fast);
}

.empty-btn:active {
	opacity: 0.88;
}

.empty-btn-text {
	color: var(--color-text-heading);
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
	background-color: var(--color-overlay);
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

/* 分类较多时限高滚动 */
.filter-options-scroll {
	max-height: 40vh;
	margin-bottom: var(--space-3xl);
}

.filter-options {
	display: flex;
	flex-wrap: wrap;
	gap: var(--space-md);
	padding: 2rpx;
}

.filter-option {
	padding: var(--space-md) var(--space-lg);
	border-radius: var(--radius-full);
	background-color: var(--color-surface-raised);
	transition:
		background-color var(--transition-fast),
		transform var(--transition-fast);
}

.filter-option:active {
	transform: scale(0.95);
}

/* 选中项琥珀高亮胶囊 */
.filter-option.active {
	background: var(--color-accent-light);
}

.filter-option-text {
	font-size: var(--font-md);
	color: var(--color-text-secondary);
	font-weight: var(--weight-medium);
}

.filter-option-text.active {
	color: var(--color-accent-deep);
	font-weight: var(--weight-semibold);
}

/* ── 弹窗按钮 ── */
.modal-actions {
	display: flex;
	gap: var(--space-lg);
}

.reset-btn {
	flex: 1;
	height: 96rpx;
	border-radius: var(--radius-full);
	background-color: var(--color-surface-raised);
	display: flex;
	align-items: center;
	justify-content: center;
	transition:
		background-color var(--transition-fast),
		transform var(--transition-fast);
}

.reset-btn:active {
	background-color: var(--color-border);
	transform: scale(0.97);
}

.reset-btn-text {
	font-size: var(--font-lg);
	font-weight: var(--weight-semibold);
	color: var(--color-text-secondary);
}

/* 设计稿：黑色胶囊主操作 */
.apply-btn {
	flex: 2;
	height: 96rpx;
	border-radius: var(--radius-full);
	background: var(--color-primary);
	box-shadow: var(--shadow-primary);
	display: flex;
	align-items: center;
	justify-content: center;
	transition: opacity var(--transition-fast);
}

.apply-btn:active {
	opacity: 0.88;
}

.apply-btn-text {
	font-size: var(--font-lg);
	font-weight: var(--weight-semibold);
	color: var(--color-text-inverse);
}
</style>
