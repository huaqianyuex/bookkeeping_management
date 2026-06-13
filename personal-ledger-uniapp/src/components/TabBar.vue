<template>
	<view class="tab-bar" :style="'padding-bottom: ' + safeBottom + 'px'">
		<view class="tab-list">
			<view
				v-for="tab in tabs"
				:key="tab.page"
				class="tab-item"
				:class="{ active: currentPage === tab.page }"
				@click="switchTab(tab.page)"
			>
				<view class="tab-icon">
					<image
						class="tab-img"
						:src="currentPage === tab.page ? tab.selectedIcon : tab.icon"
						mode="aspectFit"
					/>
				</view>
				<text class="tab-label">{{ tab.text }}</text>
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
		}
	},
	data() {
		return {
			safeBottom: 0,
			tabs: [
				{ id: 'dashboard', page: 'pages/dashboard/index', text: '概览',   icon: '/static/tabbar/dashboard.png',       selectedIcon: '/static/tabbar/dashboard-active.png' },
				{ id: 'records',   page: 'pages/records/index',   text: '账单',   icon: '/static/tabbar/records.png',         selectedIcon: '/static/tabbar/records-active.png' },
				{ id: 'categories',page: 'pages/categories/index',text: '分类',   icon: '/static/tabbar/categories.png',     selectedIcon: '/static/tabbar/categories-active.png' },
				{ id: 'user',      page: 'pages/user/index',      text: '我的',   icon: '/static/tabbar/user.png',           selectedIcon: '/static/tabbar/user-active.png' },
			]
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
		}
	}
}
</script>

<style scoped>
.tab-bar {
	position: fixed;
	bottom: 0;
	left: 0;
	right: 0;
	background-color: #ffffff;
	border-top: 1rpx solid #e8e6e1;
	z-index: 999;
	box-shadow: 0 -2rpx 12rpx rgba(30, 45, 61, 0.06);
}

.tab-list {
	display: flex;
	align-items: center;
	height: 100rpx;
}

.tab-item {
	flex: 1;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 6rpx;
	height: 100%;
	-webkit-tap-highlight-color: transparent;
}

.tab-item:active {
	opacity: 0.7;
}

.tab-icon {
	width: 48rpx;
	height: 48rpx;
	display: flex;
	align-items: center;
	justify-content: center;
}

.tab-img {
	width: 48rpx;
	height: 48rpx;
}

.tab-label {
	font-size: 18rpx;
	color: #b2bec3;
	font-weight: 500;
	line-height: 1;
}

.tab-item.active .tab-label {
	color: #1a1a2e;
	font-weight: 600;
}
</style>
