<template>
	<view class="empty-state" :class="'mode-' + mode">
		<view class="empty-icon-wrap">
			<!-- 错误态用绘制的警示图标；空态优先用绘制的线性图标，兼容旧 emoji 传参 -->
			<app-icon v-if="mode === 'error'" name="alert" :size="56"></app-icon>
			<app-icon v-else-if="isDrawnIcon" :name="icon" :size="56"></app-icon>
			<text v-else class="empty-icon">{{ icon }}</text>
		</view>
		<text class="empty-title">{{ title }}</text>
		<text v-if="description" class="empty-desc">{{ description }}</text>
		<view v-if="$slots.action" class="empty-action">
			<slot name="action"></slot>
		</view>
	</view>
</template>

<script>
import AppIcon from './AppIcon.vue'

export default {
	name: 'EmptyState',
	components: { AppIcon },
	props: {
		/** AppIcon 图标名（推荐，如 receipt/trend/compose）或旧版 emoji */
		icon: {
			type: String,
			default: 'receipt',
		},
		title: {
			type: String,
			default: '暂无数据',
		},
		description: {
			type: String,
			default: '',
		},
		/** empty=无数据；error=加载失败（配合 action 插槽放「重试」按钮） */
		mode: {
			type: String,
			default: 'empty',
			validator(value) {
				return ['empty', 'error'].includes(value)
			},
		},
	},
	computed: {
		isDrawnIcon() {
			return /^[a-z][a-z-]*$/.test(this.icon)
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
	padding: var(--space-5xl) var(--space-2xl) var(--space-4xl);
}

/* 图标容器：纸面浅盒 + 发丝线 */
.empty-icon-wrap {
	width: 120rpx;
	height: 120rpx;
	border-radius: var(--radius-full);
	background: var(--color-surface-raised);
	border: var(--hairline) solid var(--color-border);
	display: flex;
	align-items: center;
	justify-content: center;
	margin-bottom: var(--space-xl);
}

.empty-icon {
	font-size: var(--font-3xl);
	display: block;
	opacity: 0.9;
}

/* 错误态：警示红浅底，与普通空态明确区分 */
.mode-error .empty-icon-wrap {
	background: var(--color-danger-light);
	border-color: var(--color-danger-light);
}

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

/* slot 内主按钮默认呈琥珀胶囊，页面可用自定义样式覆盖 */
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
