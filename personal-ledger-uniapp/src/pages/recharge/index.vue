<template>
	<view class="container">
		<!-- 加载骨架 -->
		<view v-if="loading" class="list">
			<view v-for="i in 4" :key="i" class="skl-row">
				<view class="skl skl-line" style="width: 200rpx"></view>
				<view class="skl skl-line" style="width: 100%"></view>
			</view>
		</view>

		<!-- 加载失败：显式错误态 + 重试 -->
		<view v-else-if="error" class="list">
			<empty-state mode="error" icon="alert" title="充值记录加载失败" :description="error">
				<template #action>
					<view class="retry-btn" @click="reload">
						<text class="retry-text">重试</text>
					</view>
				</template>
			</empty-state>
		</view>

		<!-- 空态：没有充值 ≠ 页面坏了 -->
		<view v-else-if="records.length === 0" class="list">
			<empty-state icon="receipt" title="还没有充值记录" description="在会员中心选择套餐即可开通/续费会员">
				<template #action>
					<view class="retry-btn" @click="goMembership">
						<text class="retry-text">去会员中心</text>
					</view>
				</template>
			</empty-state>
		</view>

		<view v-else class="list">
			<view v-for="row in records" :key="row.id" class="order-row">
				<view class="order-main">
					<view class="order-top">
						<text class="order-plan">{{ row.planName }}</text>
						<view class="chip" :class="statusChipClass(row.status)">
							<text class="chip-text">{{ row.statusText }}</text>
						</view>
					</view>
					<text class="order-no">{{ row.orderNo }}</text>
					<text class="order-time">{{ formatTime(row.createdAt) }}</text>
					<text v-if="row.status === 1" class="order-hold">
						大额/异常交易需人工审核，管理员通过后自动到账
					</text>
					<text v-else-if="row.status === 3 && row.reviewNote" class="order-hold">
						拒绝原因：{{ row.reviewNote }}
					</text>
				</view>
				<view class="order-amount-wrap">
					<text class="order-amount">¥ {{ row.amount }}</text>
					<text class="order-days">{{ row.days }} 天</text>
				</view>
			</view>

			<!-- 触底加载 -->
			<view v-if="hasMore" class="load-more" @click="loadMore">
				<text class="load-more-text">{{ loadingMore ? '加载中…' : '加载更多' }}</text>
			</view>
			<text v-else-if="records.length > 5" class="list-end">— 已到底 —</text>
		</view>
	</view>
</template>

<script>
import EmptyState from '../../components/EmptyState.vue'
import { listMyRechargeOrders } from '../../api/recharge'

const PAGE_SIZE = 20

/** 状态 → 徽章配色（与后端 statusText 口径一致） */
const STATUS_CHIP = {
	0: { cls: 'is-muted' },
	1: { cls: 'is-amber' },
	2: { cls: 'is-ink' },
	3: { cls: 'is-danger' },
	4: { cls: 'is-muted' },
	5: { cls: 'is-muted' },
}

export default {
	components: { EmptyState },
	data() {
		return {
			records: [],
			page: 1,
			total: 0,
			loading: true,
			loadingMore: false,
			error: '',
		}
	},
	computed: {
		hasMore() {
			return this.records.length < this.total
		},
	},
	onLoad() {
		this.reload()
	},
	onReachBottom() {
		if (this.hasMore && !this.loadingMore && !this.loading) this.loadMore()
	},
	methods: {
		async reload() {
			this.loading = true
			this.error = ''
			try {
				const res = await listMyRechargeOrders({ page: 1, size: PAGE_SIZE })
				if (res?.code === 200 && res.data) {
					this.records = res.data.records || []
					this.total = res.data.total || 0
					this.page = 1
				} else {
					this.error = res?.message || '服务返回为空'
				}
			} catch (e) {
				this.error = e?.message || '请求失败，请检查网络后重试'
			} finally {
				this.loading = false
			}
		},
		async loadMore() {
			if (this.loadingMore) return
			this.loadingMore = true
			try {
				const next = this.page + 1
				const res = await listMyRechargeOrders({ page: next, size: PAGE_SIZE })
				if (res?.code === 200 && res.data) {
					const fresh = res.data.records || []
					const seen = new Set(this.records.map((r) => r.id))
					this.records = this.records.concat(fresh.filter((r) => !seen.has(r.id)))
					this.total = res.data.total || 0
					this.page = next
				} else {
					uni.showToast({ title: res?.message || '加载失败', icon: 'none' })
				}
			} catch (e) {
				if (!e?.errMsg) uni.showToast({ title: e?.message || '加载失败', icon: 'none' })
			} finally {
				this.loadingMore = false
			}
		},
		statusChipClass(status) {
			return (STATUS_CHIP[status] || STATUS_CHIP[0]).cls
		},
		formatTime(iso) {
			if (!iso) return ''
			return String(iso).replace('T', ' ').slice(0, 19)
		},
		goMembership() {
			uni.navigateTo({ url: '/pages/membership/index' })
		},
	},
}
</script>

<style scoped>
.container {
	min-height: 100vh;
	background-color: var(--color-bg);
}

.list {
	padding: var(--space-lg) var(--space-xl) var(--space-4xl);
	display: flex;
	flex-direction: column;
	gap: var(--space-lg);
}

/* ── 骨架 ── */
.skl {
	background-color: var(--color-surface-raised);
	border-radius: var(--radius-md);
	animation: sklPulse 1.6s ease-in-out infinite;
}

@keyframes sklPulse {
	0%,
	100% {
		opacity: 1;
	}
	50% {
		opacity: 0.55;
	}
}

.skl-line {
	height: 28rpx;
}

.skl-row {
	padding: var(--space-xl);
	border-radius: var(--radius-lg);
	background-color: var(--color-surface);
	display: flex;
	flex-direction: column;
	gap: var(--space-md);
}

/* ── 订单行 ── */
.order-row {
	display: flex;
	align-items: center;
	gap: var(--space-xl);
	padding: var(--space-xl);
	border-radius: var(--radius-lg);
	background-color: var(--color-surface);
}

.order-main {
	flex: 1;
	min-width: 0;
	display: flex;
	flex-direction: column;
	gap: var(--space-2xs);
}

.order-top {
	display: flex;
	align-items: center;
	gap: var(--space-md);
}

.order-plan {
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
	color: var(--color-text-heading);
}

.order-no,
.order-time {
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
	word-break: break-all;
}

.order-hold {
	font-size: var(--font-xs);
	line-height: var(--leading-relaxed);
	color: var(--color-danger);
}

.order-amount-wrap {
	display: flex;
	flex-direction: column;
	align-items: flex-end;
	gap: var(--space-2xs);
	flex-shrink: 0;
}

.order-amount {
	font-family: var(--font-amount);
	font-variant-numeric: tabular-nums;
	font-size: var(--font-lg);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	letter-spacing: var(--tracking-amount);
}

.order-days {
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
}

/* ── 状态徽章 ── */
.chip {
	display: inline-flex;
	align-items: center;
	padding: var(--space-2xs) var(--space-md);
	border-radius: var(--radius-full);
	flex-shrink: 0;
}

.chip-text {
	font-size: var(--font-xs);
	font-weight: var(--weight-semibold);
	line-height: 1.4;
}

.chip.is-amber {
	background-color: var(--color-accent-light);
}

.chip.is-amber .chip-text {
	color: var(--color-accent-deep);
}

.chip.is-danger {
	background-color: var(--color-danger-light);
}

.chip.is-danger .chip-text {
	color: var(--color-danger);
}

.chip.is-muted {
	background-color: var(--color-bg);
}

.chip.is-muted .chip-text {
	color: var(--color-text-tertiary);
}

.chip.is-ink {
	background-color: var(--color-surface-raised);
}

.chip.is-ink .chip-text {
	color: var(--color-text);
}

/* ── 加载更多 ── */
.load-more {
	display: flex;
	align-items: center;
	justify-content: center;
	height: 88rpx;
}

.load-more-text {
	font-size: var(--font-sm);
	color: var(--color-text-tertiary);
}

.list-end {
	text-align: center;
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
	padding: var(--space-md) 0;
}

/* ── 错误态重试 ── */
.retry-btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	height: 88rpx;
	padding: 0 var(--space-3xl);
	border-radius: var(--radius-full);
	background-color: var(--color-primary);
}

.retry-text {
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
	color: var(--color-text-inverse);
}
</style>
