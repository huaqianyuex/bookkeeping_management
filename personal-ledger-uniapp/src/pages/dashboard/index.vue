<template>
	<view class="container">
		<!-- 状态栏占位 -->
		<view class="status-bar" :style="{ height: statusBarHeight + 'px' }"></view>
		<scroll-view
		scroll-y
		class="scroll-content"
		:enhanced="true"
		show-scrollbar="false"
		:lower-threshold="50"
		@scrolltolower="loadMore"
		:refresher-enabled="true"
		:refresher-triggered="refreshing"
		@refresherrefresh="onRefresh"
		@touchmove.stop
	>
			<!-- 月份选择器 -->
			<view class="month-selector">
				<view class="month-arrow" @click="prevMonth">
					<text class="arrow-icon">‹</text>
				</view>
				<view class="month-badge">
					<text class="month-text">{{ currentMonthLabel }}</text>
				</view>
				<view class="month-arrow" @click="nextMonth">
					<text class="arrow-icon">›</text>
				</view>
			</view>

			<!-- Loading skeleton -->
			<animated-transition v-if="loading && !monthlyData" name="fade">
				<view class="stats-container">
					<skeleton-card :lines="2" style="margin-bottom: 20rpx;"></skeleton-card>
					<skeleton-card :lines="2" style="margin-bottom: 20rpx;"></skeleton-card>
					<skeleton-card :lines="2"></skeleton-card>
				</view>
			</animated-transition>

			<animated-transition v-else-if="monthlyData" name="fade">
				<!-- 统计卡片：左右分栏 -->
				<view class="stats-container stats-split">
					<view class="stats-main">
						<stat-card
							class="stat-main-card"
							label="结余"
							:value="monthlyData.balance"
							:type="monthlyData.balance >= 0 ? 'income' : 'expense'"
							icon="◆"
						></stat-card>
					</view>
					<view class="stats-side">
						<stat-card
							class="stat-side-card"
							label="收入"
							:value="monthlyData.totalIncome"
							type="income"
							icon="↑"
							:compact="true"
						></stat-card>
						<stat-card
							class="stat-side-card"
							label="支出"
							:value="monthlyData.totalExpense"
							type="expense"
							icon="↓"
							:compact="true"
						></stat-card>
					</view>
				</view>

				<!-- 收入趋势与对比分析 -->
				<view class="income-chart-card">
					<view class="chart-header">
						<text class="chart-title">收入分析</text>
						<view class="chart-mode-switch">
							<view class="mode-item" :class="{ active: chartMode === 'trend' }" @click="chartMode = 'trend'">
								<text class="mode-text" :class="{ active: chartMode === 'trend' }">趋势</text>
							</view>
							<view class="mode-item" :class="{ active: chartMode === 'compare' }" @click="chartMode = 'compare'">
								<text class="mode-text" :class="{ active: chartMode === 'compare' }">对比</text>
							</view>
						</view>
					</view>

					<view v-if="chartMode === 'trend' && incomeTrendData.length > 0" class="chart-panel">
						<view class="chart-kpi-row">
							<view class="kpi-main">
								<text class="kpi-label">{{ selectedTrendData ? selectedTrendData.label : '--' }}</text>
								<text class="kpi-value">¥{{ formatAmount(selectedTrendData ? selectedTrendData.amount : 0) }}</text>
							</view>
							<view class="kpi-side">
								<text class="kpi-side-label">较上月</text>
								<text class="kpi-side-value" :class="trendComparison.rate >= 0 ? 'rise' : 'down'">
									{{ formatGrowthRate(trendComparison.rate) }}
								</text>
							</view>
						</view>

						<view class="trend-chart-wrap">
							<view
								v-for="(item, index) in incomeTrendData"
								:key="item.key"
								class="trend-col"
								:class="{ active: index === selectedTrendIndex }"
								@click="selectTrendPoint(index)"
							>
								<view class="trend-bar-bg">
									<view class="trend-bar" :class="{ active: index === selectedTrendIndex }" :style="{ height: getTrendBarHeight(item.amount) }"></view>
								</view>
								<text class="trend-label" :class="{ active: index === selectedTrendIndex }">{{ item.month }}<text class="trend-label-unit">月</text></text>
							</view>
						</view>
					</view>

					<view v-else-if="chartMode === 'compare' && incomeCategoryChartData.length > 0" class="chart-panel">
						<view class="compare-list">
							<view
								v-for="(item, index) in incomeCategoryChartData"
								:key="item.categoryId"
								class="compare-row"
								@click="selectIncomeCategory(index)"
							>
								<view class="compare-row-left">
									<text class="compare-name">{{ item.categoryName }}</text>
									<view class="compare-track">
										<view class="compare-fill" :class="{ active: index === selectedIncomeCategoryIndex }" :style="{ width: getCategoryBarWidth(item.percent) }"></view>
									</view>
								</view>
								<view class="compare-row-right">
									<text class="compare-amount">¥{{ formatAmount(item.amount) }}</text>
									<text class="compare-percent">{{ item.percent.toFixed(1) }}%</text>
								</view>
							</view>
						</view>

						<view v-if="selectedIncomeCategory" class="compare-highlight">
							<text class="compare-highlight-label">当前选中分类</text>
							<text class="compare-highlight-value">{{ selectedIncomeCategory.categoryName }} · ¥{{ formatAmount(selectedIncomeCategory.amount) }}</text>
						</view>
					</view>

					<empty-state
						v-else
						icon="📈"
						title="暂无收入图表数据"
						description="请先新增收入记录后查看趋势"
					></empty-state>
				</view>

				<!-- 分类统计 -->
				<view class="table-card">
					<view class="table-header">
						<text class="table-title">支出分类统计</text>
						<text class="table-count" v-if="expenseData.length > 0">{{ expenseData.length }} 类</text>
					</view>
					<empty-state
						v-if="expenseData.length === 0"
						icon="📊"
						title="暂无支出数据"
						description="本月还没有支出记录"
					></empty-state>
					<view v-else>
						<view v-for="item in expenseData" :key="item.categoryId" class="table-row">
							<view class="table-row-left">
								<view class="category-dot type-expense"></view>
								<text class="category-name">{{ item.categoryName }}</text>
							</view>
							<view class="table-row-right">
								<view class="bar-container">
									<view class="bar type-expense" :style="{ width: item.percentage + '%' }"></view>
								</view>
								<text class="amount type-expense">¥{{ formatAmount(item.amount) }}</text>
								<text class="percentage">{{ item.percentage }}%</text>
							</view>
						</view>
					</view>
				</view>

				<view class="table-card">
					<view class="table-header">
						<text class="table-title">收入分类统计</text>
						<text class="table-count" v-if="incomeData.length > 0">{{ incomeData.length }} 类</text>
					</view>
					<empty-state
						v-if="incomeData.length === 0"
						icon="💰"
						title="暂无收入数据"
						description="本月还没有收入记录"
					></empty-state>
					<view v-else>
						<view v-for="item in incomeData" :key="item.categoryId" class="table-row">
							<view class="table-row-left">
								<view class="category-dot type-income"></view>
								<text class="category-name">{{ item.categoryName }}</text>
							</view>
							<view class="table-row-right">
								<view class="bar-container">
									<view class="bar type-income" :style="{ width: item.percentage + '%' }"></view>
								</view>
								<text class="amount type-income">¥{{ formatAmount(item.amount) }}</text>
								<text class="percentage">{{ item.percentage }}%</text>
							</view>
						</view>
					</view>
				</view>
			</animated-transition>
		</scroll-view>
		<TabBar currentPage="pages/dashboard/index" />
	</view>
</template>

<script>
import { getMonthlyStatistics, getCategoryStatistics } from '../../api/statistics'
import { formatAmount } from '../../utils/format'
import StatCard from '../../components/StatCard.vue'
import EmptyState from '../../components/EmptyState.vue'
import SkeletonCard from '../../components/SkeletonCard.vue'
import AnimatedTransition from '../../components/AnimatedTransition.vue'

export default {
	components: {
		StatCard,
		EmptyState,
		SkeletonCard,
		AnimatedTransition,
	},
	data() {
		const now = new Date()
		return {
			statusBarHeight: 20,
			year: now.getFullYear(),
			month: now.getMonth() + 1,
			monthlyData: null,
			expenseData: [],
			incomeData: [],
			incomeTrendData: [],
			selectedTrendIndex: -1,
			chartMode: 'trend',
			selectedIncomeCategoryIndex: 0,
			loading: false,
			refreshing: false,
		}
	},
	onLoad() {
		const systemInfo = uni.getSystemInfoSync()
		this.statusBarHeight = systemInfo.statusBarHeight || 20
	},
	computed: {
		currentMonthLabel() {
			return `${this.year}年${String(this.month).padStart(2, '0')}月`
		},
		selectedTrendData() {
			if (this.selectedTrendIndex < 0) return null
			return this.incomeTrendData[this.selectedTrendIndex] || null
		},
		trendMaxValue() {
			if (this.incomeTrendData.length === 0) return 0
			return Math.max(...this.incomeTrendData.map(item => Number(item.amount) || 0), 0)
		},
		trendComparison() {
			if (this.selectedTrendIndex < 0 || this.incomeTrendData.length === 0) {
				return { current: 0, previous: 0, rate: 0 }
			}
			const current = Number(this.incomeTrendData[this.selectedTrendIndex]?.amount || 0)
			const previous = Number(this.incomeTrendData[this.selectedTrendIndex - 1]?.amount || 0)
			if (previous <= 0) {
				return { current, previous, rate: current > 0 ? 100 : 0 }
			}
			return {
				current,
				previous,
				rate: ((current - previous) / previous) * 100,
			}
		},
		incomeCategoryChartData() {
			const totalIncome = Number(this.monthlyData?.totalIncome || 0)
			if (totalIncome <= 0 || this.incomeData.length === 0) return []
			return this.incomeData
				.map(item => ({
					categoryId: item.categoryId,
					categoryName: item.categoryName,
					amount: Number(item.amount) || 0,
					percent: ((Number(item.amount) || 0) / totalIncome) * 100,
				}))
				.sort((a, b) => b.amount - a.amount)
				.slice(0, 6)
		},
		selectedIncomeCategory() {
			return this.incomeCategoryChartData[this.selectedIncomeCategoryIndex] || null
		},
	},
	watch: {
		year() { this.fetchData() },
		month() { this.fetchData() },
	},
	onShow() {
		this.fetchData()
	},
	methods: {
		formatAmount,
		async fetchData() {
			this.loading = true
			try {
				const [monthlyRes, expenseRes, incomeRes] = await Promise.all([
					getMonthlyStatistics({ year: this.year, month: this.month }),
					getCategoryStatistics({ year: this.year, month: this.month, type: 0 }),
					getCategoryStatistics({ year: this.year, month: this.month, type: 1 }),
				])
				if (monthlyRes.code === 200) this.monthlyData = monthlyRes.data
				if (expenseRes.code === 200) this.expenseData = expenseRes.data
				if (incomeRes.code === 200) this.incomeData = incomeRes.data

				await this.fetchIncomeTrendData()

				if (this.selectedIncomeCategoryIndex > this.incomeCategoryChartData.length - 1) {
					this.selectedIncomeCategoryIndex = 0
				}
			} catch (e) {
				console.error(e)
			} finally {
				this.loading = false
				this.refreshing = false
			}
		},
		async fetchIncomeTrendData() {
			const recentMonths = this.buildRecentMonths(6)
			try {
				const responses = await Promise.all(
					recentMonths.map(point => getMonthlyStatistics({ year: point.year, month: point.month }))
				)
				this.incomeTrendData = recentMonths.map((point, index) => {
					const res = responses[index]
					return {
						...point,
						amount: res?.code === 200 ? Number(res.data?.totalIncome || 0) : 0,
					}
				})
				this.selectedTrendIndex = this.incomeTrendData.length > 0 ? this.incomeTrendData.length - 1 : -1
			} catch (e) {
				console.error(e)
				this.incomeTrendData = []
				this.selectedTrendIndex = -1
			}
		},
		buildRecentMonths(length = 6) {
			const points = []
			for (let i = length - 1; i >= 0; i--) {
				const date = new Date(this.year, this.month - 1 - i, 1)
				const y = date.getFullYear()
				const m = date.getMonth() + 1
				points.push({
					year: y,
					month: m,
					label: `${y}年${String(m).padStart(2, '0')}月`,
					shortLabel: `${m}月`,
					key: `${y}-${String(m).padStart(2, '0')}`,
				})
			}
			return points
		},
		selectTrendPoint(index) {
			this.selectedTrendIndex = index
		},
		selectIncomeCategory(index) {
			this.selectedIncomeCategoryIndex = index
		},
		getTrendBarHeight(amount) {
			const max = this.trendMaxValue
			if (!max || max <= 0) return '16%'
			const ratio = (Number(amount) || 0) / max
			const value = Math.max(16, Math.round(ratio * 100))
			return `${value}%`
		},
		getCategoryBarWidth(percent) {
			const safePercent = Number(percent) || 0
			return `${Math.max(8, Math.min(100, safePercent))}%`
		},
		formatGrowthRate(rate) {
			const safeRate = Number(rate) || 0
			const sign = safeRate > 0 ? '+' : ''
			return `${sign}${safeRate.toFixed(1)}%`
		},
		prevMonth() {
			if (this.month === 1) {
				this.year--
				this.month = 12
			} else {
				this.month--
			}
		},
		nextMonth() {
			if (this.month === 12) {
				this.year++
				this.month = 1
			} else {
				this.month++
			}
		},
		onRefresh() {
			this.refreshing = true
			this.fetchData()
		},
		loadMore() {}
	}
}
</script>

<style scoped>
.container {
	height: 100vh;
	background-color: var(--color-bg);
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.status-bar {
	width: 100%;
	background-color: var(--color-surface);
}

.scroll-content {
	flex: 1;
	box-sizing: border-box;
	padding: var(--space-lg) var(--space-xl) calc(var(--space-4xl) + 120rpx);
	-webkit-overflow-scrolling: touch;
}

/* ── 月份选择器 ── */
.month-selector {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 100%;
	max-width: 100%;
	box-sizing: border-box;
	padding: 0 20rpx;
	margin-bottom: 32rpx;
	gap: 16rpx;
}

.month-arrow {
	width: 60rpx;
	height: 60rpx;
	flex-shrink: 0;
	border-radius: var(--radius-full);
	background-color: var(--color-surface);
	display: flex;
	align-items: center;
	justify-content: center;
	box-shadow: var(--shadow-xs);
	border: 1rpx solid var(--color-border);
	transition:
		background-color var(--transition-fast),
		transform var(--transition-spring),
		box-shadow var(--transition-fast);
}

.month-arrow:active {
	background-color: var(--color-surface-raised);
	transform: scale(0.92);
}

.arrow-icon {
	font-size: var(--font-xl);
	color: var(--color-text-secondary);
	font-weight: var(--weight-semibold);
	line-height: 1;
	display: block;
}

.month-badge {
	flex: 1;
	min-width: 0;
	max-width: none;
	background: var(--color-primary);
	padding: var(--space-md) 32rpx;
	border-radius: var(--radius-lg);
	box-shadow: var(--shadow-sm);
}

.month-text {
	display: block;
	text-align: center;
	font-size: var(--font-base);
	font-weight: var(--weight-bold);
	color: var(--color-text-inverse);
	letter-spacing: 2rpx;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

/* ── 统计卡片容器 ── */
.stats-container {
	margin-bottom: 28rpx;
}

.stats-split {
	display: grid;
	grid-template-columns: 1.2fr 1fr;
	gap: 16rpx;
	align-items: stretch;
}

.stats-main,
.stats-side {
	min-width: 0;
}

.stats-side {
	display: grid;
	grid-template-rows: 1fr 1fr;
	gap: 12rpx;
}

.stat-main-card {
	height: 100%;
	min-height: 220rpx;
	background: var(--color-surface);
	border: 1rpx solid var(--color-border);
	box-shadow: var(--shadow-xs);
}

.stat-side-card {
	min-height: 106rpx;
	background: var(--color-surface);
	border: 1rpx solid var(--color-border);
}

::v-deep(.stat-main-card .stat-body) {
	text-align: left;
	width: 100%;
}

::v-deep(.stat-main-card .stat-label) {
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
	margin-bottom: var(--space-sm);
}

::v-deep(.stat-main-card .stat-value) {
	font-size: 46rpx;
	font-weight: var(--weight-extrabold);
	line-height: 1.15;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	font-variant-numeric: tabular-nums;
}

::v-deep(.stat-side-card .stat-label) {
	font-size: var(--font-xs);
	margin-bottom: 4rpx;
}

::v-deep(.stat-side-card .stat-value) {
	font-size: 34rpx;
	font-weight: var(--weight-bold);
	font-variant-numeric: tabular-nums;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

::v-deep(.stat-side-card .stat-icon-wrap) {
	margin-right: var(--space-sm);
}

/* ── 收入图表卡片 ── */
.income-chart-card {
	background-color: var(--color-surface);
	border-radius: var(--radius-2xl);
	padding: var(--space-lg) var(--space-xl) var(--space-md);
	margin-bottom: 24rpx;
	box-shadow: var(--shadow-xs);
	border: 1rpx solid var(--color-border);
}

.chart-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--space-md);
	margin-bottom: var(--space-lg);
}

.chart-title {
	font-size: var(--font-md);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
}

.chart-mode-switch {
	display: inline-flex;
	align-items: center;
	background-color: var(--color-bg);
	border-radius: var(--radius-md);
	padding: 4rpx;
	gap: 4rpx;
	flex-shrink: 0;
}

.mode-item {
	padding: 10rpx 20rpx;
	border-radius: var(--radius-sm);
	transition: all var(--transition-fast);
}

.mode-item.active {
	background: var(--color-primary);
	box-shadow: var(--shadow-sm);
}

.mode-text {
	font-size: var(--font-xs);
	color: var(--color-text-secondary);
	font-weight: var(--weight-medium);
}

.mode-text.active {
	color: var(--color-text-inverse);
}

.chart-panel {
	display: flex;
	flex-direction: column;
	gap: var(--space-lg);
}

.chart-kpi-row {
	display: flex;
	justify-content: space-between;
	align-items: flex-end;
	gap: var(--space-md);
	padding-bottom: var(--space-md);
	border-bottom: 1rpx solid var(--color-divider);
}

.kpi-label {
	display: block;
	font-size: var(--font-2xs);
	color: var(--color-text-tertiary);
	margin-bottom: 8rpx;
	letter-spacing: 1rpx;
}

.kpi-value {
	display: block;
	font-size: 48rpx;
	font-weight: var(--weight-extrabold);
	color: var(--color-text-heading);
	line-height: 1.1;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	font-variant-numeric: tabular-nums;
}

.kpi-side {
	flex-shrink: 0;
	text-align: right;
}

.kpi-side-label {
	display: block;
	font-size: var(--font-2xs);
	color: var(--color-text-tertiary);
	margin-bottom: 6rpx;
}

.kpi-side-value {
	display: block;
	font-size: var(--font-sm);
	font-weight: var(--weight-bold);
}

.kpi-side-value.rise {
	color: var(--color-success);
}

.kpi-side-value.down {
	color: var(--color-danger);
}

.trend-chart-wrap {
	height: 180rpx;
	display: flex;
	align-items: flex-end;
	justify-content: space-between;
	gap: 10rpx;
	padding: var(--space-sm) 16rpx 0;
	overflow: hidden;
}

.trend-col {
	flex: 1;
	min-width: 0;
	display: flex;
	flex-direction: column;
	align-items: center;
}

.trend-bar-bg {
	width: 100%;
	height: 120rpx;
	border-radius: var(--radius-sm);
	background: var(--color-bg);
	display: flex;
	align-items: flex-end;
	justify-content: center;
	padding: 8rpx 6rpx;
	box-sizing: border-box;
}

.trend-bar {
	width: 100%;
	margin: 0 auto;
	border-radius: var(--radius-xs);
	background: var(--color-primary-lighter);
	opacity: 0.4;
	min-height: 8rpx;
	transition: all var(--transition-normal);
}

.trend-bar.active {
	background: var(--color-success);
	opacity: 1;
}

.trend-label {
	display: block;
	width: 100%;
	text-align: center;
	margin-top: 10rpx;
	padding: 0;
	box-sizing: border-box;
	font-size: 20rpx;
	line-height: 1.3;
	color: var(--color-text-tertiary);
	font-weight: var(--weight-medium);
	white-space: nowrap;
	overflow: visible;
}

.trend-label-unit {
	font-size: 18rpx;
}

.trend-label.active {
	color: var(--color-text-heading);
	font-weight: var(--weight-bold);
}

.compare-list {
	display: flex;
	flex-direction: column;
	gap: var(--space-md);
}

.compare-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--space-md);
}

.compare-row-left {
	flex: 1;
	min-width: 0;
}

.compare-name {
	display: block;
	font-size: var(--font-sm);
	color: var(--color-text);
	margin-bottom: 10rpx;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	font-weight: var(--weight-medium);
}

.compare-track {
	height: 10rpx;
	border-radius: var(--radius-full);
	background-color: var(--color-bg);
	overflow: hidden;
}

.compare-fill {
	height: 100%;
	border-radius: var(--radius-full);
	background: var(--color-primary-lighter);
	opacity: 0.5;
	transition: all var(--transition-normal);
}

.compare-fill.active {
	background: var(--color-success);
	opacity: 0.8;
}

.compare-row-right {
	width: 160rpx;
	text-align: right;
	flex-shrink: 0;
}

.compare-amount {
	display: block;
	font-size: var(--font-sm);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	font-variant-numeric: tabular-nums;
}

.compare-percent {
	display: block;
	font-size: var(--font-2xs);
	color: var(--color-text-tertiary);
	margin-top: 6rpx;
}

.compare-highlight {
	margin-top: var(--space-md);
	padding: var(--space-lg);
	border-radius: var(--radius-md);
	background: var(--color-success-light);
	border: 1rpx solid rgba(46, 204, 113, 0.15);
}

.compare-highlight-label {
	display: block;
	font-size: var(--font-2xs);
	color: var(--color-text-secondary);
	margin-bottom: 8rpx;
}

.compare-highlight-value {
	display: block;
	font-size: var(--font-sm);
	font-weight: var(--weight-semibold);
	color: var(--color-text-heading);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

@media screen and (max-width: 360px) {
	.month-selector {
		padding: 0 12rpx;
		gap: 12rpx;
	}

	.month-arrow {
		width: 56rpx;
		height: 56rpx;
	}

	.month-badge {
		padding: 12rpx 20rpx;
	}

	.stats-split {
		grid-template-columns: 1fr;
		gap: var(--space-md);
	}

	.stats-side {
		grid-template-rows: none;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-sm);
	}

	::v-deep(.stat-main-card .stat-value) {
		font-size: 40rpx;
	}

	::v-deep(.stat-side-card .stat-value) {
		font-size: 28rpx;
	}

	.kpi-value {
		font-size: 36rpx;
	}

	.trend-chart-wrap {
		padding: 8rpx 8rpx 0;
		gap: 8rpx;
	}

	.trend-label {
		font-size: 18rpx;
	}

	.compare-row-right {
		width: 140rpx;
	}
}

/* ── 分类表格卡片 ── */
.table-card {
	background-color: var(--color-surface);
	border-radius: var(--radius-2xl);
	margin-bottom: 20rpx;
	overflow: hidden;
	box-shadow: var(--shadow-xs);
	border: 1rpx solid var(--color-border);
}

.table-header {
	padding: var(--space-md) var(--space-xl);
	border-bottom: 1rpx solid var(--color-divider);
	display: flex;
	align-items: center;
	justify-content: space-between;
}

.table-title {
	font-size: var(--font-md);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	letter-spacing: var(--tracking-heading);
	line-height: var(--leading-tight);
}

.table-count {
	font-size: var(--font-2xs);
	color: var(--color-text-tertiary);
	font-weight: var(--weight-medium);
	background: var(--color-bg);
	padding: 6rpx 16rpx;
	border-radius: var(--radius-sm);
}

/* ── 表格行 ── */
.table-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: var(--space-lg) var(--space-xl);
	border-bottom: 1rpx solid var(--color-divider);
	transition: background-color var(--transition-fast);
}

.table-row:last-child {
	border-bottom: none;
}

.table-row:active {
	background-color: var(--color-surface-raised);
}

.table-row-left {
	display: flex;
	align-items: center;
	flex: 1;
	min-width: 0;
}

.category-dot {
	width: 12rpx;
	height: 12rpx;
	border-radius: var(--radius-xs);
	margin-right: var(--space-lg);
	flex-shrink: 0;
}

.category-dot.type-expense {
	background: var(--color-danger);
}

.category-dot.type-income {
	background: var(--color-success);
}

.category-name {
	font-size: var(--font-sm);
	color: var(--color-text);
	font-weight: var(--weight-medium);
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.table-row-right {
	display: flex;
	align-items: center;
	flex-shrink: 0;
}

.bar-container {
	width: 80rpx;
	height: 8rpx;
	background-color: var(--color-bg);
	border-radius: var(--radius-full);
	margin: 0 var(--space-lg);
	overflow: hidden;
}

.bar {
	height: 100%;
	border-radius: var(--radius-full);
	transition: width var(--transition-normal) cubic-bezier(0.34, 1.56, 0.64, 1);
}

.bar.type-expense {
	background: var(--color-danger);
	opacity: 0.6;
}

.bar.type-income {
	background: var(--color-success);
	opacity: 0.6;
}

.amount {
	font-size: var(--font-sm);
	font-weight: var(--weight-bold);
	min-width: 120rpx;
	text-align: right;
	font-variant-numeric: tabular-nums;
}

.amount.type-expense {
	color: var(--color-danger);
}

.amount.type-income {
	color: var(--color-success);
}

.percentage {
	font-size: var(--font-2xs);
	color: var(--color-text-tertiary);
	width: 72rpx;
	text-align: right;
	font-weight: var(--weight-medium);
	font-variant-numeric: tabular-nums;
}

</style>
