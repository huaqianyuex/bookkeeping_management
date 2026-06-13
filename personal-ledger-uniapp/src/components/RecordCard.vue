<template>
	<view
		class="record-card"
		:class="typeClass"
		@click="handleClick"
		@touchstart="onTouchStart"
		@touchmove="onTouchMove"
		@touchend="onTouchEnd"
	>
		<view class="record-main" :style="{ transform: 'translateX(' + moveX + 'rpx)' }">
			<view class="record-accent" :class="typeClass"></view>
			<view class="record-icon-wrap" :class="typeClass">
				<text class="record-icon-text">{{ record.categoryType === 0 ? '−' : '+' }}</text>
			</view>
			<view class="record-info">
				<text class="record-category">{{ record.categoryName }}</text>
				<text v-if="record.remark" class="record-remark">{{ record.remark }}</text>
			</view>
			<view class="record-amount-wrap">
				<text class="record-amount" :class="typeClass">
					{{ record.categoryType === 0 ? '−' : '+' }}¥{{ formattedAmount }}
				</text>
			</view>
		</view>

		<!-- 滑动删除按钮 -->
		<view class="record-delete" @click.stop="handleDelete">
			<text class="record-delete-icon">✕</text>
			<text class="record-delete-text">删除</text>
		</view>
	</view>
</template>

<script>
export default {
	name: 'RecordCard',
	props: {
		record: {
			type: Object,
			required: true,
		},
	},
	data() {
		return {
			startX: 0,
			moveX: 0,
			currentX: 0,
			isSwiping: false,
		}
	},
	computed: {
		typeClass() {
			return this.record.categoryType === 0 ? 'type-expense' : 'type-income'
		},
		formattedAmount() {
			return Number(this.record.amount).toFixed(2)
		},
	},
	methods: {
		handleClick() {
			if (Math.abs(this.moveX) < 10) {
				this.$emit('edit', this.record)
			}
		},
		handleDelete() {
			this.$emit('delete', this.record.id)
			this.resetSwipe()
		},
		onTouchStart(e) {
			this.startX = e.touches[0].clientX
			this.currentX = this.moveX
			this.isSwiping = true
		},
		onTouchMove(e) {
			if (!this.isSwiping) return
			const deltaX = (e.touches[0].clientX - this.startX) * 2
			let newX = this.currentX + deltaX
			if (newX > 0) newX = 0
			if (newX < -160) newX = -160
			this.moveX = newX
		},
		onTouchEnd() {
			this.isSwiping = false
			if (this.moveX < -60) {
				this.moveX = -140
			} else {
				this.moveX = 0
			}
		},
		resetSwipe() {
			this.moveX = 0
		},
	},
}
</script>

<style scoped>
.record-card {
	position: relative;
	overflow: hidden;
	margin-bottom: var(--space-sm);
	border-radius: var(--radius-xl);
}

.record-main {
	display: flex;
	align-items: center;
	justify-content: space-between;
	background-color: var(--color-surface);
	padding: var(--space-lg);
	position: relative;
	z-index: 1;
	transition:
		transform var(--transition-spring),
		box-shadow var(--transition-fast);
	border-radius: var(--radius-xl);
	box-shadow: var(--shadow-xs);
	width: 100%;
	box-sizing: border-box;
}

/* 按压时轻微浮起 */
.record-main:active {
	box-shadow: var(--shadow-sm);
}

/* 左侧色条 */
.record-accent {
	position: absolute;
	left: 0;
	top: 0;
	bottom: 0;
	width: 6rpx;
	border-radius: 6rpx 0 0 6rpx;
}

.record-accent.type-expense {
	background: linear-gradient(180deg, var(--color-danger), #ff6b6b);
}

.record-accent.type-income {
	background: linear-gradient(180deg, var(--color-success), #2ecc71);
}

/* 图标区：圆形渐变背景 */
.record-icon-wrap {
	width: 62rpx;
	height: 62rpx;
	border-radius: var(--radius-full);
	display: flex;
	align-items: center;
	justify-content: center;
	margin-right: var(--space-md);
	flex-shrink: 0;
}

.record-icon-wrap.type-expense {
	background: linear-gradient(145deg, var(--color-danger-light), #ffd6d6);
}

.record-icon-wrap.type-income {
	background: linear-gradient(145deg, var(--color-success-light), #d4f5e3);
}

.record-icon-text {
	font-size: var(--font-base);
	font-weight: var(--weight-bold);
	line-height: 1;
}

.record-icon-wrap.type-expense .record-icon-text {
	color: var(--color-danger);
}

.record-icon-wrap.type-income .record-icon-text {
	color: var(--color-success);
}

.record-info {
	flex: 1;
	min-width: 0;
}

.record-category {
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
	color: var(--color-text);
	display: block;
	line-height: var(--leading-tight);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.record-remark {
	font-size: var(--font-xs);
	color: var(--color-text-secondary);
	margin-top: var(--space-2xs);
	display: block;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.record-amount-wrap {
	margin-left: var(--space-md);
	flex: none;
	overflow: visible;
}

.record-amount {
	font-size: var(--font-lg);
	font-weight: var(--weight-bold);
	letter-spacing: -0.5rpx;
	line-height: var(--leading-tight);
	white-space: nowrap;
}

.record-amount.type-expense {
	color: var(--color-danger);
}

.record-amount.type-income {
	color: var(--color-success);
}

/* 删除按钮：渐变背景 + 弹簧动画 */
.record-delete {
	position: absolute;
	right: 0;
	top: 0;
	bottom: 0;
	width: 140rpx;
	background: linear-gradient(135deg, var(--color-danger), #ff6b6b);
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	z-index: 0;
	border-radius: 0 var(--radius-xl) var(--radius-xl) 0;
}

.record-delete-icon {
	font-size: var(--font-sm);
	display: block;
	margin-bottom: var(--space-2xs);
	color: var(--color-text-inverse);
	opacity: 0.9;
}

.record-delete-text {
	font-size: var(--font-xs);
	color: var(--color-text-inverse);
	font-weight: var(--weight-medium);
	opacity: 0.9;
}
</style>
