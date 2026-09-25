<template>
	<view v-if="visible" class="success-overlay" @click.stop>
		<view class="success-panel anim-scale-in">
			<!-- 纯 CSS 打勾：内联 <svg> 在微信小程序端不渲染，改用边框画勾保证跨端 -->
			<view class="success-medal">
				<view class="success-check-clip">
					<view class="success-check"></view>
				</view>
			</view>
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
	background: var(--color-overlay);
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
	padding: var(--space-4xl) var(--space-5xl);
	box-shadow: var(--shadow-xl);
}

/* 圆章：先弹入，再从中间揭示对勾 */
.success-medal {
	position: relative;
	width: 150rpx;
	height: 150rpx;
	border-radius: var(--radius-full);
	border: 8rpx solid var(--color-success);
	background: var(--color-success-light);
	box-sizing: border-box;
	margin-bottom: var(--space-xl);
	animation: medalPop 0.5s var(--ease-out-back) both;
}

.success-check-clip {
	position: absolute;
	left: 50%;
	top: 50%;
	width: 0;
	height: 90rpx;
	margin: -45rpx 0 0 -45rpx;
	overflow: hidden;
	animation: checkReveal 0.35s 0.4s var(--ease-out-expo) forwards;
}

.success-check {
	position: absolute;
	left: 24rpx;
	top: 30rpx;
	width: 42rpx;
	height: 22rpx;
	border-left: 8rpx solid var(--color-success);
	border-bottom: 8rpx solid var(--color-success);
	border-radius: 2rpx;
	transform: rotate(-45deg);
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

@keyframes medalPop {
	from {
		transform: scale(0.4);
		opacity: 0;
	}
	to {
		transform: scale(1);
		opacity: 1;
	}
}

@keyframes checkReveal {
	to {
		width: 90rpx;
	}
}
</style>
