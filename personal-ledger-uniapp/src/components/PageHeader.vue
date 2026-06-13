<template>
	<view class="page-header">
		<view class="page-header-left">
			<text class="page-header-title">{{ title }}</text>
			<text v-if="subtitle" class="page-header-subtitle">{{ subtitle }}</text>
		</view>
		<view v-if="$slots.action" class="page-header-right">
			<slot name="action"></slot>
		</view>
	</view>
</template>

<script>
export default {
	name: 'PageHeader',
	props: {
		title: {
			type: String,
			required: true,
		},
		subtitle: {
			type: String,
			default: '',
		},
	},
}
</script>

<style scoped>
.page-header {
	display: flex;
	justify-content: space-between;
	align-items: flex-end;
	gap: var(--space-md);
	padding: var(--space-xl) var(--space-xl) var(--space-2xl);
	background: var(--color-surface);
	border-bottom: 1rpx solid var(--color-divider);
	position: relative;
}

/* 左侧装饰竖线 */
.page-header::before {
	content: '';
	position: absolute;
	left: var(--space-xl);
	top: 50%;
	transform: translateY(-50%);
	width: 6rpx;
	height: 48rpx;
	border-radius: 3rpx;
	background: var(--color-primary);
	opacity: 0.8;
}

.page-header-left {
	flex: 1;
	min-width: 0;
	padding-left: calc(6rpx + var(--space-xl));
}

.page-header-title {
	font-size: var(--font-3xl);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	display: block;
	letter-spacing: 1rpx;
	line-height: var(--leading-tight);
}

.page-header-subtitle {
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
	margin-top: var(--space-xs);
	display: block;
	letter-spacing: var(--tracking-caption);
	font-weight: var(--weight-medium);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.page-header-right {
	flex-shrink: 0;
	max-width: 42%;
}
</style>
