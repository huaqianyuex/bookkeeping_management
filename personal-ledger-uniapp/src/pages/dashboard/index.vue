<template>
	<view class="container">
		<!-- 状态栏占位 -->
		<view class="status-bar" :style="{ height: statusBarHeight + 'px' }"></view>
		<scroll-view
			scroll-y
			class="scroll-content"
			:enhanced="true"
			show-scrollbar="false"
			:refresher-enabled="true"
			:refresher-triggered="refreshing"
			@refresherrefresh="onRefresh"
			@touchmove.stop
		>
			<!-- Loading skeleton：仅「当前月份还没有自己的一份数据」时显示，
			     有缓存/旧数据时静默刷新，绝不把上个月数字伪装成当月 -->
			<animated-transition v-if="loading && loadedKey !== currentKey" name="fade">
				<view class="skeleton-zone">
					<skeleton-card :lines="2"></skeleton-card>
					<skeleton-card :lines="3"></skeleton-card>
					<skeleton-card :lines="4"></skeleton-card>
				</view>
			</animated-transition>

			<animated-transition v-else-if="monthlyData" name="fade">
				<!-- 账期抬头：月份切换 + AI 解读入口 -->
				<view class="period-row">
					<view class="period-nav">
						<view class="period-arrow" @click="prevMonth"><text class="arrow-glyph">‹</text></view>
						<text class="period-text">{{ currentMonthLabel }}</text>
						<view class="period-arrow" @click="nextMonth"><text class="arrow-glyph">›</text></view>
					</view>
					<view class="ai-entry" @click="goAiRead">
						<text class="ai-entry-text">AI 解读</text>
						<text class="ai-entry-arrow">→</text>
					</view>
				</view>

				<!-- 结余焦点：无盒版面，数字即主角 -->
				<view class="balance-block">
					<view class="balance-row">
						<text v-if="balanceParts.sign" class="balance-sign">{{ balanceParts.sign }}</text>
						<text class="balance-currency">¥</text>
						<text class="balance-num">{{ balanceParts.int }}</text>
						<text class="balance-dec">.{{ balanceParts.dec }}</text>
					</view>
					<view class="balance-meta">
						<text class="balance-label">{{ monthShortLabel }}结余</text>
						<view v-if="momBalance.text !== '—'" class="mom-chip" :class="momBalance.cls">
							<text class="mom-arrow">{{ momBalance.arrow }}</text>
							<text class="mom-text">{{ momBalance.text }}</text>
						</view>
					</view>
				</view>

				<!-- 收支行情带：值 + 环比 + 六月微趋势 -->
				<view class="tape-row">
					<view class="tape-col">
						<view class="tape-head">
							<text class="tape-label">收入</text>
							<text v-if="momIncome.text !== '—'" class="tape-mom" :class="momIncome.cls">{{ momIncome.arrow }} {{ momIncome.text }}</text>
						</view>
						<text class="tape-amount is-income">¥{{ formatAmount(monthlyData.totalIncome) }}</text>
						<view class="tape-spark">
							<view
								v-for="(p, i) in monthSeries"
								:key="'in' + p.key"
								class="spark-bar is-income"
								:class="{ latest: i === monthSeries.length - 1 }"
								:style="{ height: sparkHeight(p.income, seriesMax.income), animationDelay: i * 45 + 'ms' }"
							></view>
						</view>
					</view>
					<view class="tape-col tape-col--right">
						<view class="tape-head">
							<text class="tape-label">支出</text>
							<text v-if="momExpense.text !== '—'" class="tape-mom" :class="momExpense.cls">{{ momExpense.arrow }} {{ momExpense.text }}</text>
						</view>
						<text class="tape-amount is-expense">¥{{ formatAmount(monthlyData.totalExpense) }}</text>
						<view class="tape-spark">
							<view
								v-for="(p, i) in monthSeries"
								:key="'ex' + p.key"
								class="spark-bar is-expense"
								:class="{ latest: i === monthSeries.length - 1 }"
								:style="{ height: sparkHeight(p.expense, seriesMax.expense), animationDelay: i * 45 + 120 + 'ms' }"
							></view>
						</view>
					</view>
				</view>

				<!-- 支出板块排行：钱花在哪 -->
				<view class="section">
					<view class="section-head">
						<text class="section-title">支出板块</text>
						<text class="section-sub" v-if="expenseSectors.length > 0">合计 ¥{{ formatAmount(monthlyData.totalExpense) }}</text>
					</view>
					<empty-state
						v-if="expenseSectors.length === 0"
						icon="receipt"
						title="暂无支出"
						description="本月还没有支出记录，点右下角 + 记一笔"
					></empty-state>
					<view v-else class="sector-list">
						<view v-for="(row, index) in expenseSectors" :key="row.key" class="sector-row">
							<view class="sector-chip" :style="{ background: row.bg }">
								<text class="sector-glyph" :style="{ color: row.deep }">{{ row.glyph }}</text>
							</view>
							<view class="sector-main">
								<view class="sector-line">
									<text class="sector-name">{{ row.name }}</text>
									<text class="sector-amount">¥{{ formatAmount(row.amount) }}</text>
									<text class="sector-percent">{{ row.percent.toFixed(1) }}%</text>
								</view>
								<view class="sector-track">
									<view
										class="sector-fill"
										:style="{ width: row.width + '%', background: row.deep, animationDelay: index * 55 + 'ms' }"
									></view>
								</view>
							</view>
						</view>
					</view>
				</view>

				<!-- 近六月走势：收支双序列，点击月份查看结算 -->
				<view class="section">
					<view class="section-head">
						<text class="section-title">近六月走势</text>
						<text class="section-sub legend">
							<text class="legend-dot is-income"></text>收入
							<text class="legend-dot is-expense"></text>支出
						</text>
					</view>
					<empty-state
						v-if="monthSeries.length === 0"
						icon="trend"
						title="暂无走势数据"
						description="记账后这里会展示近六个月的收支对比"
					></empty-state>
					<view v-else>
						<view class="trend-chart">
							<view
								v-for="(p, i) in monthSeries"
								:key="p.key"
								class="trend-col"
								:class="{ active: i === selectedSeriesIndex }"
								@click="selectSeriesPoint(i)"
							>
								<view class="trend-bars">
									<view class="trend-bar is-income" :style="{ height: barHeight(p.income), animationDelay: i * 45 + 'ms' }"></view>
									<view class="trend-bar is-expense" :style="{ height: barHeight(p.expense), animationDelay: i * 45 + 60 + 'ms' }"></view>
								</view>
								<text class="trend-label">{{ p.shortLabel }}</text>
							</view>
						</view>
						<view v-if="selectedPoint" class="trend-detail">
							<view class="detail-item">
								<text class="detail-label">收入</text>
								<text class="detail-value is-income">¥{{ formatAmount(selectedPoint.income) }}</text>
							</view>
							<view class="detail-item">
								<text class="detail-label">支出</text>
								<text class="detail-value is-expense">¥{{ formatAmount(selectedPoint.expense) }}</text>
							</view>
							<view class="detail-item">
								<text class="detail-label">结余</text>
								<text class="detail-value" :class="{ 'is-expense': selectedPoint.balance < 0 }">¥{{ formatAmount(selectedPoint.balance) }}</text>
							</view>
						</view>
					</view>
				</view>

				<!-- 收入构成：收纳为紧凑列表 -->
				<view class="section section--last">
					<view class="section-head">
						<text class="section-title">收入构成</text>
						<text class="section-sub" v-if="incomeSectors.length > 0">合计 ¥{{ formatAmount(monthlyData.totalIncome) }}</text>
					</view>
					<empty-state
						v-if="incomeSectors.length === 0"
						icon="receipt"
						title="暂无收入"
						description="本月还没有收入记录"
					></empty-state>
					<view v-else class="sector-list">
						<view v-for="(row, index) in incomeSectors" :key="row.key" class="sector-row">
							<view class="sector-chip" :style="{ background: row.bg }">
								<text class="sector-glyph" :style="{ color: row.deep }">{{ row.glyph }}</text>
							</view>
							<view class="sector-main">
								<view class="sector-line">
									<text class="sector-name">{{ row.name }}</text>
									<text class="sector-amount">¥{{ formatAmount(row.amount) }}</text>
									<text class="sector-percent">{{ row.percent.toFixed(1) }}%</text>
								</view>
								<view class="sector-track sector-track--thin">
									<view
										class="sector-fill"
										:style="{ width: row.width + '%', background: row.deep, animationDelay: index * 55 + 'ms' }"
									></view>
								</view>
							</view>
						</view>
					</view>
				</view>
			</animated-transition>
		</scroll-view>
		<TabBar currentPage="pages/dashboard/index" fab />
	</view>
</template>

<script>
import { getMonthlyStatistics, getCategoryStatistics } from '../../api/statistics'
import { getWithRetry } from '../../api/request'
import { formatAmount } from '../../utils/format'
import { useLedgerStore } from '../../utils/store'
import { catColorVar, catColorDeepVar } from '../../utils/category'
import EmptyState from '../../components/EmptyState.vue'
import SkeletonCard from '../../components/SkeletonCard.vue'
import AnimatedTransition from '../../components/AnimatedTransition.vue'

export default {
	components: {
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
			// 近六月收支序列：income / expense / balance，由月度接口前端聚合
			monthSeries: [],
			selectedSeriesIndex: -1,
			loading: false,
			refreshing: false,
			// 已成功加载的月份 key，用于区分「当月骨架」与「静默刷新」
			loadedKey: '',
		}
	},
	onLoad() {
		const systemInfo = uni.getSystemInfoSync()
		this.statusBarHeight = systemInfo.statusBarHeight || 20
	},
	computed: {
		currentKey() {
			return `${this.year}-${String(this.month).padStart(2, '0')}`
		},
		currentMonthLabel() {
			return `${this.year}年${String(this.month).padStart(2, '0')}月`
		},
		monthShortLabel() {
			return `${this.month}月`
		},
		balanceValue() {
			return Number(this.monthlyData?.balance ?? 0)
		},
		balanceParts() {
			const num = this.balanceValue
			const [int, dec] = Math.abs(num).toFixed(2).split('.')
			return {
				sign: num < 0 ? '−' : '',
				int: int.replace(/\B(?=(\d{3})+(?!\d))/g, ','),
				dec,
			}
		},
		curPoint() {
			return this.monthSeries[this.monthSeries.length - 1] || null
		},
		prevPoint() {
			return this.monthSeries[this.monthSeries.length - 2] || null
		},
		// 环比：与序列内上一月比较；上月基数为 0 时不编造百分比
		momBalance() {
			return this.buildMom(this.balanceValue, this.prevPoint?.balance, true)
		},
		momIncome() {
			return this.buildMom(this.curPoint?.income, this.prevPoint?.income, true)
		},
		momExpense() {
			return this.buildMom(this.curPoint?.expense, this.prevPoint?.expense, false)
		},
		seriesMax() {
			let income = 0
			let expense = 0
			this.monthSeries.forEach((p) => {
				income = Math.max(income, Number(p.income) || 0)
				expense = Math.max(expense, Number(p.expense) || 0)
			})
			return { income, expense }
		},
		selectedPoint() {
			return this.monthSeries[this.selectedSeriesIndex] || null
		},
		expenseSectors() {
			const rows = this.buildSectorRows(this.expenseData)
			if (rows.length === 0) return []
			const top = rows.slice(0, 6)
			const rest = rows.slice(6)
			if (rest.length > 0) {
				const amount = rest.reduce((sum, r) => sum + r.amount, 0)
				const percent = rest.reduce((sum, r) => sum + r.percent, 0)
				top.push({
					key: 'other',
					name: `其他 ${rest.length} 类`,
					amount,
					percent,
					width: Math.max(4, Math.min(100, percent)),
					bg: 'var(--cat-gray)',
					deep: 'var(--cat-gray-deep)',
					glyph: '他',
				})
			}
			return top
		},
		incomeSectors() {
			return this.buildSectorRows(this.incomeData).slice(0, 6)
		},
	},
	watch: {
		year() { this.onMonthChange() },
		month() { this.onMonthChange() },
	},
	onShow() {
		const token = uni.getStorageSync('token')
		// 未登录跳转统一由 App.vue 启动时与 request.js 的全局 401 处理，这里只做静默返回
		if (!token) {
			return
		}
		// stale-while-revalidate：切 tab 回来先渲染缓存，再静默刷新
		const cache = useLedgerStore().dashboard
		if (cache.key === this.currentKey && cache.monthlyData) {
			this.monthlyData = cache.monthlyData
			this.expenseData = cache.expenseData
			this.incomeData = cache.incomeData
			this.monthSeries = cache.monthSeries || []
			this.selectedSeriesIndex = this.monthSeries.length - 1
			this.loadedKey = this.currentKey
			this.fetchData(true)
		} else {
			this.fetchData()
		}
	},
	methods: {
		formatAmount,
		async fetchData(silent = false) {
			if (!silent) this.loading = true
			try {
				// 四组请求并发：月度统计、支出分类、收入分类、近 6 个月序列
				const trendPromise = this.fetchMonthSeries()
				const [monthlyRes, expenseRes, incomeRes] = await Promise.all([
					getWithRetry(getMonthlyStatistics, { year: this.year, month: this.month }),
					getWithRetry(getCategoryStatistics, { year: this.year, month: this.month, type: 0 }),
					getWithRetry(getCategoryStatistics, { year: this.year, month: this.month, type: 1 }),
					trendPromise,
				])
				if (monthlyRes.code === 200) this.monthlyData = monthlyRes.data
				if (expenseRes.code === 200) this.expenseData = expenseRes.data
				if (incomeRes.code === 200) this.incomeData = incomeRes.data
				this.loadedKey = this.currentKey

				useLedgerStore().setDashboardCache({
					key: this.currentKey,
					monthlyData: this.monthlyData,
					expenseData: this.expenseData,
					incomeData: this.incomeData,
					monthSeries: this.monthSeries,
				})
			} catch (e) {
				console.error('[Dashboard] 加载数据失败:', e)
				uni.showToast({ title: '加载数据失败，请检查网络连接', icon: 'none' })
			} finally {
				this.loading = false
				this.refreshing = false
			}
		},
		// 近六月收支序列：复用月度汇总接口，前端聚合出收入/支出/结余三条信息
		async fetchMonthSeries() {
			const recentMonths = this.buildRecentMonths(6)
			try {
				const responses = await Promise.all(
					recentMonths.map(point => getWithRetry(getMonthlyStatistics, { year: point.year, month: point.month }))
				)
				this.monthSeries = recentMonths.map((point, index) => {
					const res = responses[index]
					const data = res?.code === 200 ? res.data || {} : {}
					const income = Number(data.totalIncome ?? data.total_income ?? 0) || 0
					const expense = Number(data.totalExpense ?? data.total_expense ?? 0) || 0
					return { ...point, income, expense, balance: income - expense }
				})
				this.selectedSeriesIndex = this.monthSeries.length - 1
			} catch (e) {
				console.error('[Dashboard] 月度序列加载失败:', e)
				this.monthSeries = []
				this.selectedSeriesIndex = -1
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
		buildSectorRows(list) {
			return (list || [])
				.map(item => {
					const id = item.categoryId ?? item.category_id
					const name = item.categoryName ?? item.category_name ?? ''
					const amount = Number(item.amount) || 0
					const percent = Number(item.percentage ?? item.percent) || 0
					return {
						key: String(id),
						id,
						name,
						amount,
						percent,
						width: Math.max(4, Math.min(100, percent)),
						bg: catColorVar(id),
						deep: catColorDeepVar(id),
						glyph: (name || '·').slice(0, 1),
					}
				})
				.filter(row => row.name)
				.sort((a, b) => b.amount - a.amount)
		},
		buildMom(value, prev, goodWhenUp) {
			const current = Number(value)
			const base = Number(prev)
			if (!Number.isFinite(current) || !Number.isFinite(base) || base <= 0) {
				return { text: '—', cls: 'flat', arrow: '' }
			}
			const rate = ((current - base) / base) * 100
			if (Math.abs(rate) < 0.05) {
				return { text: '持平', cls: 'flat', arrow: '' }
			}
			const up = rate > 0
			return {
				text: `${up ? '+' : ''}${rate.toFixed(1)}%`,
				cls: up === goodWhenUp ? 'rise' : 'down',
				arrow: up ? '▲' : '▼',
			}
		},
		selectSeriesPoint(index) {
			this.selectedSeriesIndex = index
		},
		sparkHeight(amount, max) {
			if (!max || max <= 0) return '12%'
			const ratio = (Number(amount) || 0) / max
			return `${Math.max(10, Math.round(ratio * 100))}%`
		},
		barHeight(amount) {
			const max = Math.max(this.seriesMax.income, this.seriesMax.expense)
			if (!max || max <= 0) return '4%'
			const ratio = (Number(amount) || 0) / max
			return `${Math.max(4, Math.round(ratio * 100))}%`
		},
		// 切月：命中缓存先渲染再静默刷；没缓存的月份走骨架屏
		onMonthChange() {
			const cache = useLedgerStore().dashboard
			if (cache.key === this.currentKey && cache.monthlyData) {
				this.monthlyData = cache.monthlyData
				this.expenseData = cache.expenseData
				this.incomeData = cache.incomeData
				this.monthSeries = cache.monthSeries || []
				this.selectedSeriesIndex = this.monthSeries.length - 1
				this.loadedKey = this.currentKey
				this.fetchData(true)
			} else {
				this.fetchData()
			}
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
		// 带着当前账期跳转 AI 助手，由 ai-chat 页预填问题
		goAiRead() {
			const q = encodeURIComponent(`帮我解读${this.currentMonthLabel}的收支情况`)
			uni.navigateTo({ url: `/pages/ai-chat/index?q=${q}` })
		},
		onRefresh() {
			this.refreshing = true
			this.fetchData()
		},
	},
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
	background-color: var(--color-bg);
}

.scroll-content {
	flex: 1;
	box-sizing: border-box;
	padding: var(--space-lg) var(--space-2xl) var(--page-bottom-space);
	-webkit-overflow-scrolling: touch;
	overflow: hidden;
}

.skeleton-zone {
	display: flex;
	flex-direction: column;
	gap: var(--space-lg);
	padding-top: var(--space-lg);
}

/* ── 进场动效：数据从基线生长（全页唯一编排的动效时刻） ── */
.grow-y {
	transform-origin: bottom;
	animation: growY 0.7s var(--ease-out-expo) backwards;
}

@keyframes growY {
	from { transform: scaleY(0.04); }
	to { transform: scaleY(1); }
}

.grow-x {
	transform-origin: left;
	animation: growX 0.7s var(--ease-out-expo) backwards;
}

@keyframes growX {
	from { transform: scaleX(0.02); }
	to { transform: scaleX(1); }
}

/* ── 账期抬头 ── */
.period-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-top: var(--space-sm);
}

.period-nav {
	display: flex;
	align-items: center;
	gap: var(--space-xs);
	margin-left: calc(-1 * var(--space-lg));
}

.period-arrow {
	width: 88rpx;
	height: 88rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: var(--radius-md);
	transition: background-color var(--transition-fast), transform var(--transition-fast);
}

.period-arrow:active {
	background-color: var(--color-surface-raised);
	transform: scale(0.92);
}

.arrow-glyph {
	font-size: var(--font-2xl);
	color: var(--color-text-secondary);
	font-weight: var(--weight-semibold);
	line-height: 1;
	display: block;
	transform: translateY(-2rpx);
}

.period-text {
	font-family: var(--font-numeric-mixed);
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
	color: var(--color-text-heading);
	letter-spacing: var(--tracking-caption);
	white-space: nowrap;
}

.ai-entry {
	display: flex;
	align-items: center;
	gap: var(--space-2xs);
	padding: var(--space-sm) var(--space-md);
	border-radius: var(--radius-md);
	min-height: 88rpx;
	box-sizing: border-box;
	transition: background-color var(--transition-fast);
}

.ai-entry:active {
	background-color: var(--color-accent-light);
}

.ai-entry-text {
	font-size: var(--font-sm);
	font-weight: var(--weight-semibold);
	color: var(--color-accent-deep);
}

.ai-entry-arrow {
	font-size: var(--font-sm);
	color: var(--color-accent-deep);
	font-family: var(--font-amount);
}

/* ── 结余焦点：紧凑报告版面，数字即主角 ── */
.balance-block {
	margin-top: 96rpx;
}

.balance-row {
	display: flex;
	align-items: baseline;
	gap: var(--space-sm);
}

.balance-sign {
	font-family: var(--font-amount);
	font-size: var(--font-3xl);
	font-weight: var(--weight-semibold);
	color: var(--color-text-heading);
}

.balance-currency {
	font-family: var(--font-amount);
	font-size: var(--font-3xl);
	font-weight: var(--weight-semibold);
	color: var(--color-text-tertiary);
}

.balance-num {
	font-family: var(--font-amount);
	font-size: var(--font-hero);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	line-height: 1.05;
	letter-spacing: -0.02em;
	font-variant-numeric: tabular-nums;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	max-width: 100%;
}

.balance-dec {
	font-family: var(--font-amount);
	font-size: var(--font-2xl);
	font-weight: var(--weight-semibold);
	color: var(--color-text-tertiary);
	font-variant-numeric: tabular-nums;
}

.balance-meta {
	display: flex;
	align-items: center;
	gap: var(--space-md);
	margin-top: var(--space-lg);
}

.balance-label {
	font-size: var(--font-sm);
	color: var(--color-text-secondary);
	font-weight: var(--weight-medium);
}

.mom-chip {
	display: flex;
	align-items: center;
	gap: var(--space-2xs);
	padding: var(--space-2xs) var(--space-md);
	border-radius: var(--radius-full);
	font-family: var(--font-amount);
	font-variant-numeric: tabular-nums;
}

.mom-chip.rise {
	background: var(--color-success-light);
	color: var(--color-success);
}

.mom-chip.down {
	background: var(--color-danger-light);
	color: var(--color-danger);
}

.mom-chip.flat {
	background: var(--color-surface-raised);
	color: var(--color-text-tertiary);
}

.mom-arrow {
	font-size: var(--font-2xs);
	line-height: 1;
}

.mom-text {
	font-size: var(--font-xs);
	font-weight: var(--weight-semibold);
	line-height: 1;
}

/* ── 收支行情带 ── */
.tape-row {
	display: flex;
	margin-top: 120rpx;
	padding: var(--space-2xl) 0;
	border-top: var(--hairline) solid var(--color-border);
	border-bottom: var(--hairline) solid var(--color-border);
}

.tape-col {
	flex: 1;
	min-width: 0;
}

.tape-col--right {
	border-left: var(--hairline) solid var(--color-border);
	padding-left: var(--space-2xl);
}

.tape-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--space-sm);
	margin-bottom: var(--space-sm);
}

.tape-label {
	font-size: var(--font-sm);
	color: var(--color-text-secondary);
	font-weight: var(--weight-medium);
}

.tape-mom {
	font-family: var(--font-amount);
	font-size: var(--font-xs);
	font-weight: var(--weight-semibold);
	font-variant-numeric: tabular-nums;
}

.tape-mom.rise {
	color: var(--color-success);
}

.tape-mom.down {
	color: var(--color-danger);
}

.tape-amount {
	display: block;
	font-family: var(--font-amount);
	font-size: var(--font-stat-lg);
	font-weight: var(--weight-bold);
	line-height: 1.2;
	font-variant-numeric: tabular-nums;
	letter-spacing: -0.01em;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.tape-amount.is-income {
	color: var(--color-success);
}

.tape-amount.is-expense {
	color: var(--color-danger);
}

.tape-spark {
	display: flex;
	align-items: flex-end;
	justify-content: space-between;
	gap: 8rpx;
	height: 150rpx;
	margin-top: var(--space-lg);
}

.spark-bar {
	width: 20rpx;
	border-radius: 4rpx;
	animation: growY 0.6s var(--ease-out-expo) backwards;
}

.spark-bar.is-income {
	background: var(--color-success);
}

.spark-bar.is-expense {
	background: var(--color-danger);
}

.spark-bar {
	opacity: 0.22;
}

.spark-bar.latest {
	opacity: 1;
}

/* ── 通用分区 ── */
.section {
	margin-top: 96rpx;
}

.section--last {
	margin-bottom: var(--space-lg);
}

.section-head {
	display: flex;
	align-items: baseline;
	justify-content: space-between;
	gap: var(--space-md);
	margin-bottom: var(--space-lg);
}

.section-title {
	font-size: var(--font-base);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	letter-spacing: var(--tracking-heading);
}

.section-sub {
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
	font-variant-numeric: tabular-nums;
}

.legend {
	display: flex;
	align-items: center;
	gap: var(--space-xs);
}

.legend-dot {
	width: 16rpx;
	height: 16rpx;
	border-radius: var(--radius-xs);
	display: inline-block;
}

.legend-dot.is-income {
	background: var(--color-success);
}

.legend-dot.is-expense {
	background: var(--color-danger);
}

/* ── 板块排行行 ── */
.sector-list {
	display: flex;
	flex-direction: column;
	gap: var(--space-xl);
}

.sector-row {
	display: flex;
	align-items: flex-start;
	gap: var(--space-lg);
}

.sector-chip {
	width: 60rpx;
	height: 60rpx;
	border-radius: var(--radius-md);
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
	margin-top: 2rpx;
}

.sector-glyph {
	font-size: var(--font-md);
	font-weight: var(--weight-bold);
	line-height: 1;
}

.sector-main {
	flex: 1;
	min-width: 0;
}

.sector-line {
	display: flex;
	align-items: baseline;
	gap: var(--space-md);
	margin-bottom: var(--space-sm);
}

.sector-name {
	flex: 1;
	min-width: 0;
	font-size: var(--font-sm);
	color: var(--color-text);
	font-weight: var(--weight-medium);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.sector-amount {
	font-family: var(--font-amount);
	font-size: var(--font-sm);
	font-weight: var(--weight-semibold);
	color: var(--color-text-heading);
	font-variant-numeric: tabular-nums;
	white-space: nowrap;
}

.sector-percent {
	font-family: var(--font-amount);
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
	width: 96rpx;
	text-align: right;
	font-variant-numeric: tabular-nums;
	white-space: nowrap;
}

.sector-track {
	height: 12rpx;
	border-radius: var(--radius-full);
	background: var(--color-surface-raised);
	overflow: hidden;
}

.sector-track--thin {
	height: 8rpx;
}

.sector-fill {
	height: 100%;
	border-radius: var(--radius-full);
	animation: growX 0.7s var(--ease-out-expo) backwards;
}

/* ── 走势图 ── */
.trend-chart {
	display: flex;
	align-items: flex-end;
	gap: var(--space-sm);
	height: 260rpx;
}

.trend-col {
	flex: 1;
	min-width: 0;
	height: 100%;
	display: flex;
	flex-direction: column;
	justify-content: flex-end;
	border-radius: var(--radius-sm);
	transition: background-color var(--transition-fast);
}

.trend-col:active {
	background: var(--color-surface-raised);
}

.trend-bars {
	flex: 1;
	display: flex;
	align-items: flex-end;
	justify-content: center;
	gap: 8rpx;
	min-height: 0;
}

.trend-bar {
	width: 18rpx;
	border-radius: 4rpx;
	animation: growY 0.6s var(--ease-out-expo) backwards;
	opacity: 0.35;
	transition: opacity var(--transition-normal);
}

.trend-bar.is-income {
	background: var(--color-success);
}

.trend-bar.is-expense {
	background: var(--color-danger);
}

.trend-col.active .trend-bar {
	opacity: 1;
}

.trend-label {
	display: block;
	text-align: center;
	margin-top: var(--space-sm);
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
	font-weight: var(--weight-medium);
	white-space: nowrap;
}

.trend-col.active .trend-label {
	color: var(--color-text-heading);
	font-weight: var(--weight-bold);
}

.trend-detail {
	display: flex;
	margin-top: var(--space-lg);
	padding-top: var(--space-lg);
	border-top: var(--hairline) solid var(--color-divider);
}

.detail-item {
	flex: 1;
	display: flex;
	flex-direction: column;
	gap: var(--space-2xs);
}

.detail-label {
	font-size: var(--font-2xs);
	color: var(--color-text-tertiary);
}

.detail-value {
	font-family: var(--font-amount);
	font-size: var(--font-lg);
	font-weight: var(--weight-semibold);
	color: var(--color-text-heading);
	font-variant-numeric: tabular-nums;
}

.detail-value.is-income {
	color: var(--color-success);
}

.detail-value.is-expense {
	color: var(--color-danger);
}

/* ── 窄屏适配 ── */
@media screen and (max-width: 360px) {
	.scroll-content {
		padding: var(--space-md) var(--space-lg) var(--page-bottom-space);
	}

	.balance-num {
		font-size: var(--font-4xl);
	}

	.tape-col--right {
		padding-left: var(--space-xl);
	}

	.tape-amount {
		font-size: var(--font-2xl);
	}

	.sector-percent {
		width: 84rpx;
	}
}
</style>
