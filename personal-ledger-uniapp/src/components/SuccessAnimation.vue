<template>
	<view v-if="visible" class="success-overlay" @click.stop>
		<view class="success-panel anim-scale-in">
			<svg class="success-svg" viewBox="0 0 100 100">
				<circle class="success-check-circle" cx="50" cy="50" r="45" fill="none" stroke="#2E7D52" stroke-width="4" stroke-linecap="round" />
				<path class="success-check-mark" d="M30 52 L44 66 L70 38" fill="none" stroke="#2E7D52" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" />
			</svg>
			<text class="success-text anim-fade-in-up">{{ message }}</text>
			<text class="success-sub anim-fade-in-up" style="animation-delay: 0.2s">{{ subMessage }}</text>
		</view>
	</view>
</template>

<script>
export default {
	name: 'SuccessAnimation',
	props: {
		visible: { type: Boolean, default: false },
		message: { type: String, default: '记账成功' },
		subMessage: { type: String, default: '' },
		duration: { type: Number, default: 1500 },
	},
	watch: {
		visible(val) {
			if (val) {
				setTimeout(() => {
					this.$emit('done')
				}, this.duration)
			}
		}
	}
}
</script>

<style scoped>
.success-overlay {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background: rgba(0, 0, 0, 0.45);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 2000;
}

.success-panel {
	display: flex;
	flex-direction: column;
	align-items: center;
	background: var(--color-surface);
	border-radius: var(--radius-3xl);
	padding: 64rpx 80rpx;
	box-shadow: var(--shadow-xl);
}

.success-svg {
	width: 160rpx;
	height: 160rpx;
	margin-bottom: var(--space-xl);
}

.success-check-circle {
	stroke-dasharray: 314;
	stroke-dashoffset: 314;
	animation: checkCircle 0.6s 0.1s var(--ease-out-expo) forwards;
}

.success-check-mark {
	stroke-dasharray: 100;
	stroke-dashoffset: 100;
	animation: checkDraw 0.4s 0.5s var(--ease-out-expo) forwards;
}

.success-text {
	font-size: var(--font-xl);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	margin-bottom: var(--space-xs);
	text-align: center;
}

.success-sub {
	font-size: var(--font-sm);
	color: var(--color-text-secondary);
	text-align: center;
}

@keyframes checkCircle {
  to { stroke-dashoffset: 0; }
}

@keyframes checkDraw {
  to { stroke-dashoffset: 0; }
}
</style>
