<template>
	<view class="stat-card" :class="[typeClass, { compact: compact }]">
		<!-- 顶部色条 -->
		<view class="stat-accent" :class="typeClass"></view>
		<view class="stat-icon-wrap" :class="typeClass">
			<text class="stat-icon-text">{{ icon }}</text>
		</view>
		<view class="stat-body">
			<text class="stat-label">{{ label }}</text>
			<text class="stat-value" :class="typeClass">{{ prefix }}{{ formattedValue }}</text>
		</view>
	</view>
</template>

<script>
export default {
	name: 'StatCard',
	props: {
		label: {
			type: String,
			required: true,
		},
		value: {
			type: [Number, String],
			default: 0,
		},
		type: {
			type: String,
			default: 'balance',
			validator(value) {
				return ['income', 'expense', 'balance'].includes(value)
			},
		},
		icon: {
			type: String,
			default: '',
		},
		compact: {
			type: Boolean,
			default: false,
		},
		prefix: {
			type: String,
			default: '¥',
		},
	},
	computed: {
		typeClass() {
			return `type-${this.type}`
		},
		formattedValue() {
			return Number(this.value).toFixed(2)
		},
	},
}
</script>

<style scoped>
.stat-card {
	position: relative;
	background-color: var(--color-surface);
	border-radius: var(--radius-xl);
	padding: var(--space-xl);
	box-shadow: var(--shadow-xs);
	display: flex;
	flex-direction: column;
	align-items: center;
	overflow: hidden;
	transition:
		transform var(--transition-spring),
		box-shadow var(--transition-normal);
}

/* 顶部色条 */
.stat-accent {
	position: absolute;
	top: 0;
	left: 0;
	right: 0;
	height: 4rpx;
	opacity: 0.9;
}

.stat-accent.type-income {
	background: var(--color-success);
}

.stat-accent.type-expense {
	background: var(--color-danger);
}

.stat-accent.type-balance {
	background: var(--color-primary);
}

/* 按压反馈 */
.stat-card:active {
	transform: scale(0.97);
	box-shadow: var(--shadow-md);
}

.stat-card.compact {
	flex-direction: row;
	align-items: center;
	padding: var(--space-lg);
}

/* 图标区：渐变底 + 圆角 */
.stat-icon-wrap {
	width: 72rpx;
	height: 72rpx;
	border-radius: var(--radius-lg);
	display: flex;
	align-items: center;
	justify-content: center;
	margin-bottom: var(--space-md);
	font-size: var(--font-xl);
	flex-shrink: 0;
	position: relative;
	overflow: hidden;
}

.stat-icon-text {
	display: block;
	line-height: 1;
	font-weight: var(--weight-bold);
	transform: translateY(-1rpx);
}

/* 给图标区加一层微妙的渐变叠加 */
.stat-icon-wrap.type-income {
	background: var(--color-success-light);
}

.stat-icon-wrap.type-expense {
	background: var(--color-danger-light);
}

.stat-icon-wrap.type-balance {
	background: var(--color-accent-light);
}

.stat-card.compact .stat-icon-wrap {
	width: 56rpx;
	height: 56rpx;
	border-radius: var(--radius-md);
	margin-bottom: 0;
	margin-right: var(--space-lg);
	font-size: var(--font-base);
}

.stat-body {
	flex: 1;
	text-align: center;
}

.stat-label {
	font-size: var(--font-2xs);
	color: var(--color-text-tertiary);
	font-weight: var(--weight-medium);
	display: block;
	margin-bottom: var(--space-xs);
	letter-spacing: 1rpx;
}

.stat-value {
	font-size: var(--font-3xl);
	font-weight: var(--weight-extrabold);
	display: block;
	color: var(--color-text-heading);
	letter-spacing: -1rpx;
	line-height: var(--leading-tight);
}

.stat-card.compact .stat-value {
	font-size: var(--font-xl);
}

.stat-value.type-income {
	color: var(--color-success);
}

.stat-value.type-expense {
	color: var(--color-danger);
}

.stat-value.type-balance {
	color: var(--color-primary);
}
</style>
