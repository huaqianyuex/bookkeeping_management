<template>
	<view class="skeleton-card">
		<!-- 可选头像骨架 -->
		<view v-if="showAvatar" class="skeleton-avatar"></view>
		<view class="skeleton-lines">
			<view
				v-for="i in lines"
				:key="i"
				class="skeleton-line"
				:class="{ 'is-title': i === 1 }"
				:style="{
					width: getWidth(i),
				}"
			></view>
		</view>
	</view>
</template>

<script>
export default {
	name: 'SkeletonCard',
	props: {
		lines: {
			type: Number,
			default: 3,
		},
		showAvatar: {
			type: Boolean,
			default: false,
		},
	},
	methods: {
		getWidth(index) {
			if (index === 1) return this.showAvatar ? '55%' : '60%'
			if (index === this.lines) return this.showAvatar ? '35%' : '40%'
			return '80%'
		},
	},
}
</script>

<style scoped>
.skeleton-card {
	background-color: var(--color-surface);
	border-radius: var(--radius-2xl);
	padding: var(--space-lg);
	box-shadow: var(--shadow-xs);
	display: flex;
	align-items: flex-start;
	gap: var(--space-lg);
}

.skeleton-avatar {
	width: 76rpx;
	height: 76rpx;
	border-radius: var(--radius-xl);
	background: linear-gradient(
		90deg,
		var(--color-border) 25%,
		var(--color-surface-raised) 37%,
		var(--color-border) 63%
	);
	background-size: 400% 100%;
	animation: shimmer 1.6s ease infinite;
	flex-shrink: 0;
}

.skeleton-lines {
	flex: 1;
	min-width: 0;
}

.skeleton-line {
	height: 24rpx;
	border-radius: var(--radius-sm);
	background: linear-gradient(
		90deg,
		var(--color-border) 25%,
		var(--color-surface-raised) 37%,
		var(--color-border) 63%
	);
	background-size: 400% 100%;
	animation: shimmer 1.6s ease infinite;
	margin-bottom: var(--space-sm);
}

.skeleton-line:last-child {
	margin-bottom: 0;
}

.skeleton-line.is-title {
	height: 36rpx;
	border-radius: var(--radius-md);
}

@keyframes shimmer {
	0% {
		background-position: 200% 0;
	}
	100% {
		background-position: -200% 0;
	}
}
</style>
