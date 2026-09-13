<template>
	<view class="stat-card" :class="[typeClass, { compact: compact }]" @click="$emit('click')">
		<view class="stat-accent" :class="typeClass"></view>
		<view class="stat-icon-wrap" :class="typeClass">
			<text class="stat-icon-text">{{ icon }}</text>
		</view>
		<view class="stat-body">
			<text class="stat-label">{{ label }}</text>
			<view class="stat-value-row">
				<text class="stat-currency" :class="typeClass">¥</text>
				<text class="stat-amount" :class="typeClass">{{ integerPart }}</text>
				<text class="stat-decimal" :class="typeClass">.{{ decimalPart }}</text>
			</view>
		</view>
	</view>
</template>

<script>
export default {
	name: 'StatCard',
	props: {
		label: { type: String, required: true },
		value: { type: [Number, String], default: 0 },
		type: { type: String, default: 'balance' },
		icon: { type: String, default: '' },
		compact: { type: Boolean, default: false },
		prefix: { type: String, default: '¥' },
	},
	computed: {
		typeClass() {
			return `type-${this.type}`
		},
		formattedValue() {
			const num = Number(this.value) || 0
			const parts = num.toFixed(2).split('.')
			return { integer: parts[0], decimal: parts[1] }
		},
		integerPart() {
			return this.formattedValue.integer
		},
		decimalPart() {
			return this.formattedValue.decimal
		},
	},
}
</script>

<style scoped>
.stat-card {
	position: relative;
	background-color: var(--color-surface);
	border-radius: var(--radius-2xl);
	padding: var(--space-xl);
	box-shadow: var(--shadow-card);
	display: flex;
	flex-direction: column;
	align-items: center;
	overflow: hidden;
	transition: background-color 0.15s ease;
}

.stat-card:active {
	background-color: var(--color-surface-raised);
}

/* 顶部色条 — 收支语义标记 */
.stat-accent {
	position: absolute;
	top: 0;
	left: 0;
	right: 0;
	height: 4rpx;
	opacity: 0.9;
}

.stat-accent.type-income { background: var(--color-success); }
.stat-accent.type-expense { background: var(--color-danger); }
.stat-accent.type-balance { background: var(--color-primary); }

/* Compact 模式 */
.stat-card.compact {
	flex-direction: row;
	align-items: center;
	padding: var(--space-lg);
}

/* 图标区 */
.stat-icon-wrap {
	width: 72rpx;
	height: 72rpx;
	border-radius: var(--radius-xl);
	display: flex;
	align-items: center;
	justify-content: center;
	margin-bottom: var(--space-md);
	flex-shrink: 0;
	position: relative;
	overflow: hidden;
}

.stat-icon-text {
	display: block;
	line-height: 1;
	font-weight: var(--weight-bold);
}

.stat-icon-wrap.type-income { background: var(--color-success-light); }
.stat-icon-wrap.type-expense { background: var(--color-danger-light); }
.stat-icon-wrap.type-balance { background: var(--color-accent-light); }

.stat-card.compact .stat-icon-wrap {
	width: 56rpx;
	height: 56rpx;
	border-radius: var(--radius-md);
	margin-bottom: 0;
	margin-right: var(--space-lg);
}

/* 文字区 */
.stat-body {
	flex: 1;
	text-align: center;
}

.stat-label {
	font-size: var(--font-2xs);
	color: var(--color-text-tertiary);
	font-weight: var(--weight-medium);
	display: block;
	margin-bottom: var(--space-sm);
	letter-spacing: 1rpx;
}

/* ── 财务级数字排版 ── */
.stat-value-row {
	display: flex;
	align-items: baseline;
	justify-content: center;
	line-height: 1;
}

.stat-currency {
	font-size: var(--font-lg);
	font-weight: var(--weight-semibold);
	color: var(--color-text-tertiary);
	margin-right: 2rpx;
	font-family: var(--font-amount);
	font-variant-numeric: tabular-nums;
}

.stat-amount {
	font-size: var(--font-4xl);
	font-weight: var(--weight-extrabold);
	letter-spacing: -1rpx;
	font-family: var(--font-amount);
	font-variant-numeric: tabular-nums;
	line-height: 1;
}

.stat-decimal {
	font-size: var(--font-xl);
	font-weight: var(--weight-bold);
	letter-spacing: 0;
	font-family: var(--font-amount);
	font-variant-numeric: tabular-nums;
	opacity: 0.65;
	margin-left: 1rpx;
}

.stat-card.compact .stat-amount {
	font-size: var(--font-xl);
}

.stat-card.compact .stat-decimal {
	font-size: var(--font-sm);
}

.stat-card.compact .stat-currency {
	font-size: var(--font-sm);
}

/* 颜色 — 设计稿03：支出墨黑大数字、收入绿、结余墨黑 */
.stat-currency.type-income, .stat-amount.type-income, .stat-decimal.type-income {
	color: var(--color-success);
}
.stat-currency.type-expense, .stat-amount.type-expense, .stat-decimal.type-expense {
	color: var(--color-text);
}
.stat-currency.type-balance, .stat-amount.type-balance, .stat-decimal.type-balance {
	color: var(--color-text);
}
</style>
