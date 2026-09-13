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
					{{ record.categoryType === 0 ? '−' : '+' }}<text class="record-currency">¥</text><text class="record-num">{{ integerPart }}</text><text class="record-dot">.</text><text class="record-cent">{{ decimalPart }}</text>
				</text>
			</view>
		</view>

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
		record: { type: Object, required: true },
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
		parts() {
			const num = Number(this.record.amount) || 0
			const p = num.toFixed(2).split('.')
			return { integer: p[0], decimal: p[1] }
		},
		integerPart() { return this.parts.integer },
		decimalPart() { return this.parts.decimal },
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
	transition: transform 0.35s var(--ease-out-back), box-shadow 0.2s ease;
	border-radius: var(--radius-xl);
	box-shadow: var(--shadow-card);
	width: 100%;
	box-sizing: border-box;
}

.record-main:active {
	box-shadow: var(--shadow-sm);
}

/* 左侧色条 — 设计稿03 列表行无色条，隐藏（保留结构兼容） */
.record-accent {
	display: none;
}

.record-accent.type-expense { background: var(--color-danger); }
.record-accent.type-income { background: var(--color-success); }

/* 图标区 — 设计稿03：粉彩圆角方块图标 */
.record-icon-wrap {
	width: 72rpx;
	height: 72rpx;
	border-radius: var(--radius-lg);
	display: flex;
	align-items: center;
	justify-content: center;
	margin-right: var(--space-lg);
	flex-shrink: 0;
}

.record-icon-wrap.type-expense { background: var(--color-danger-light); }
.record-icon-wrap.type-income { background: var(--color-success-light); }

.record-icon-text {
	font-size: var(--font-lg);
	font-weight: var(--weight-bold);
	line-height: 1;
}
.record-icon-wrap.type-expense .record-icon-text { color: var(--color-danger); }
.record-icon-wrap.type-income .record-icon-text { color: var(--color-success); }


/* 信息区 */
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

/* ── 金额财务排版 ── */
.record-amount-wrap {
	margin-left: var(--space-lg);
	flex: none;
	overflow: visible;
}

.record-amount {
	font-size: var(--font-lg);
	font-weight: var(--weight-bold);
	letter-spacing: -0.5rpx;
	line-height: var(--leading-tight);
	white-space: nowrap;
	font-family: var(--font-amount);
	font-variant-numeric: tabular-nums;
}

/* 金额颜色 — 设计稿03：支出墨黑、收入绿 */
.record-amount.type-expense { color: var(--color-text); }
.record-amount.type-income { color: var(--color-success); }

.record-currency {
	font-size: var(--font-sm);
	opacity: 0.7;
	font-weight: var(--weight-medium);
}

.record-num {
	font-size: var(--font-lg);
}

.record-dot {
	font-size: var(--font-sm);
	opacity: 0.7;
}

.record-cent {
	font-size: var(--font-sm);
	opacity: 0.6;
}

/* 删除按钮 */
.record-delete {
	position: absolute;
	right: 0;
	top: 0;
	bottom: 0;
	width: 140rpx;
	background: var(--color-danger);
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
