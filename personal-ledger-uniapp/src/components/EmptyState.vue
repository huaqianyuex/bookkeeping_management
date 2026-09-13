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

/* 设计稿10 空态：灰色主文案 + 灰色说明 + 黄色胶囊 action 按钮 */
.empty-title {
	font-size: var(--font-md);
	font-weight: var(--weight-medium);
	color: var(--color-text-secondary);
	display: block;
	margin-bottom: var(--space-sm);
	letter-spacing: var(--tracking-heading);
	line-height: var(--leading-tight);
}

.empty-desc {
	font-size: var(--font-sm);
	color: var(--color-text-tertiary);
	display: block;
	margin-bottom: var(--space-xl);
	text-align: center;
	line-height: var(--leading-relaxed);
	max-width: 440rpx;
}

.empty-action {
	margin-top: var(--space-lg);
}

/* slot 内主按钮默认呈黄色胶囊（设计稿10「去记一笔」），页面可用自定义样式覆盖 */
.empty-action :deep(button),
.empty-action :deep(.btn-primary) {
	background-color: var(--color-accent);
	color: var(--color-text-heading);
	border-radius: var(--radius-full);
	font-weight: var(--weight-semibold);
	box-shadow: var(--shadow-accent);
	padding: 0 var(--space-3xl);
}
</style>
