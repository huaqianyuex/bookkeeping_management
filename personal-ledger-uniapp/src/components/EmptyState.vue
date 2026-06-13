<template>
	<view class="empty-state">
		<view class="empty-icon-wrap">
			<text class="empty-icon">{{ icon }}</text>
		</view>
		<text class="empty-title">{{ title }}</text>
		<text v-if="description" class="empty-desc">{{ description }}</text>
		<view v-if="$slots.action" class="empty-action">
			<slot name="action"></slot>
		</view>
	</view>
</template>

<script>
export default {
	name: 'EmptyState',
	props: {
		icon: {
			type: String,
			default: '📄',
		},
		title: {
			type: String,
			default: '暂无数据',
		},
		description: {
			type: String,
			default: '',
		},
	},
}
</script>

<style scoped>
.empty-state {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	padding: 100rpx var(--space-2xl) 80rpx;
}

/* 图标容器：渐变圆形 */
.empty-icon-wrap {
	width: 120rpx;
	height: 120rpx;
	border-radius: var(--radius-full);
	background: var(--color-bg);
	display: flex;
	align-items: center;
	justify-content: center;
	margin-bottom: var(--space-xl);
}

.empty-icon {
	font-size: 56rpx;
	display: block;
	opacity: 0.9;
}

.empty-title {
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
	color: var(--color-text-heading);
	display: block;
	margin-bottom: var(--space-sm);
	letter-spacing: var(--tracking-heading);
	line-height: var(--leading-tight);
}

.empty-desc {
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
	display: block;
	margin-bottom: var(--space-xl);
	text-align: center;
	line-height: var(--leading-relaxed);
	max-width: 440rpx;
}

.empty-action {
	margin-top: var(--space-sm);
}
</style>
