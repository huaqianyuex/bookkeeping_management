<template>
	<!-- 设计稿03/10 底栏：白色悬浮胶囊 + 选中黑色圆胶囊；「+」为独立悬浮按钮（fab 控制显示） -->
	<view class="tab-bar-wrap" :style="'padding-bottom: ' + safeBottom + 'px'">
		<view v-if="fab" class="fab-add" :style="{ bottom: 'calc(100% + ' + fabGap + 'rpx)' }" @click="goAddRecord">
			<text class="fab-plus">+</text>
		</view>
		<view class="tab-bar">
			<view class="tab-list">
				<view
					v-for="t in tabs"
					:key="t.page"
					class="tab-item"
					:class="{ active: currentPage === t.page }"
					@click="switchTab(t.page)"
				>
					<view class="tab-icon">
						<image
							class="tab-img"
							:class="{ 'tab-img--inverse': currentPage === t.page }"
							:src="currentPage === t.page ? t.activeIcon : t.icon"
							mode="aspectFit"
						/>
					</view>
					<text class="tab-label" :class="{ active: currentPage === t.page }">{{ t.label }}</text>
				</view>
			</view>
		</view>
	</view>
</template>

<script>
export default {
	props: {
		currentPage: {
			type: String,
			default: ''
		},
		// 是否显示悬浮「新增账单」按钮（「我的」页不显示）
		fab: {
			type: Boolean,
			default: false
		},
		// 悬浮按钮相对 TabBar 顶部的间距（rpx），AI 页需抬过输入条时传入更大值
		fabGap: {
			type: [Number, String],
			default: 24
		}
	},
	data() {
		return {
			safeBottom: 0,
			tabs: [
				{ page: 'pages/dashboard/index', label: '概览', icon: '/static/tabbar/dashboard.png', activeIcon: '/static/tabbar/dashboard-active.png' },
				{ page: 'pages/records/index', label: '账单', icon: '/static/tabbar/records.png', activeIcon: '/static/tabbar/records-active.png' },
				{ page: 'pages/ai-chat/index', label: 'AI助手', icon: '/static/tabbar/chat.png', activeIcon: '/static/tabbar/chat-active.png' },
				{ page: 'pages/categories/index', label: '分类', icon: '/static/tabbar/categories.png', activeIcon: '/static/tabbar/categories-active.png' },
				{ page: 'pages/user/index', label: '我的', icon: '/static/tabbar/user.png', activeIcon: '/static/tabbar/user-active.png' },
			],
		}
	},
	mounted() {
		const systemInfo = uni.getSystemInfoSync()
		const safeAreaBottom = systemInfo.safeAreaInsets?.bottom || 0
		this.safeBottom = safeAreaBottom
	},
	methods: {
		switchTab(page) {
			if (this.currentPage === page) return
			uni.reLaunch({ url: '/' + page })
		},
		// 悬浮「+」：进入已有的记账页（新增入口，不改动任何既有导航）
		goAddRecord() {
			uni.navigateTo({ url: '/pages/records/add-edit' })
		}
	}
}
</script>

<style scoped>
/* 悬浮胶囊容器：左右留边、圆角满、弥散阴影（设计稿03 底栏） */
.tab-bar-wrap {
	position: fixed;
	bottom: 0;
	left: 0;
	right: 0;
	z-index: 999;
	pointer-events: none;
}

.tab-bar {
	pointer-events: auto;
	margin: 0 var(--space-lg);
	background-color: var(--color-surface);
	border-radius: var(--radius-full);
	box-shadow: var(--shadow-tabbar);
	padding: 10rpx;
}

/* 5 个 tab 等宽等高对齐 */
.tab-list {
	display: flex;
	align-items: stretch;
}

.tab-item {
	flex: 1;
	height: 104rpx;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 4rpx;
	border-radius: var(--radius-full);
	-webkit-tap-highlight-color: transparent;
	transition: background-color var(--transition-fast);
}

.tab-item:active {
	opacity: 0.75;
}

/* 选中态：黑色圆胶囊，图标/文字反白（设计稿03「账单」选中样式） */
.tab-item.active {
	background-color: var(--color-primary);
}

/* 悬浮「新增账单」按钮：黄色圆形，悬于 TabBar 右上方（设计稿03 中央加号语义） */
.fab-add {
	pointer-events: auto;
	position: absolute;
	right: 40rpx;
	width: 108rpx;
	height: 108rpx;
	border-radius: 50%;
	background-color: var(--color-accent);
	box-shadow: var(--shadow-accent);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 2;
	transition: transform var(--transition-fast);
}

.fab-add:active {
	transform: scale(0.92);
}

.fab-plus {
	font-size: 60rpx;
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	line-height: 1;
}

.tab-icon {
	width: 48rpx;
	height: 48rpx;
	display: flex;
	align-items: center;
	justify-content: center;
}

.tab-img {
	width: 44rpx;
	height: 44rpx;
}

/* 选中胶囊内的 PNG 图标反白（CSS 滤镜，避免更换图标资源） */
.tab-img--inverse {
	filter: brightness(0) invert(1);
}

.tab-label {
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
	font-weight: var(--weight-medium);
	line-height: 1;
}

.tab-label.active {
	color: var(--color-text-inverse);
	font-weight: var(--weight-semibold);
}
</style>
