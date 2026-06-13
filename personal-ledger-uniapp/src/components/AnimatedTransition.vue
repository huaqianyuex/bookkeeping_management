<template>
	<view class="animated-transition" :class="transitionClass">
		<slot></slot>
	</view>
</template>

<script>
export default {
	name: 'AnimatedTransition',
	props: {
		name: {
			type: String,
			default: 'fade',
			validator(value) {
				return ['fade', 'slide-up', 'slide-right'].includes(value)
			},
		},
	},
	data() {
		return {
			visible: false,
		}
	},
	computed: {
		transitionClass() {
			return `transition-${this.name}${this.visible ? ' transition-active' : ''}`
		},
	},
	mounted() {
		setTimeout(() => {
			this.visible = true
		}, 50)
	},
}
</script>

<style scoped>
/* Fade transition */
.transition-fade {
	opacity: 0;
	transition: opacity var(--transition-normal);
}

.transition-fade.transition-active {
	opacity: 1;
}

/* Slide-up transition */
.transition-slide-up {
	opacity: 0;
	transform: translateY(40rpx);
	transition: opacity var(--transition-normal), transform var(--transition-normal);
}

.transition-slide-up.transition-active {
	opacity: 1;
	transform: translateY(0);
}

/* Slide-right transition */
.transition-slide-right {
	opacity: 0;
	transform: translateX(-40rpx);
	transition: opacity var(--transition-normal), transform var(--transition-normal);
}

.transition-slide-right.transition-active {
	opacity: 1;
	transform: translateX(0);
}
</style>
