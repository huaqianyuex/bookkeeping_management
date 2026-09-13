<script>
export default {
	onLaunch() {
		console.log('App Launch')
		// 启动时检查登录态，未登录则跳转到登录页。
		// 注意：dashboard 页面的 onShow 也会做同样的检查，但启动瞬间只会有一个页面被加载，
		// 这里负责首次进入时的全局跳转，避免与子页面跳转冲突导致"do not operate continuously"。
		const token = uni.getStorageSync('token')
		if (!token) {
			uni.reLaunch({ url: '/pages/login/index' })
		}
		// 有 token 则正常进入 tabBar 首页（pages.json 第一个页面即 dashboard）
	},
	onShow() {
		console.log('App Show')
	},
	onHide() {
		console.log('App Hide')
	}
}
</script>

<style>
@import '@/styles/theme.css';
@import '@/styles/animations.css';

/* ============================
   Global Base Styles
   ============================ */
/* 设计稿全局基调：浅灰底 + 近黑正文，标题加粗（设计稿01-11） */
page {
	background-color: var(--color-bg);
	font-family: var(--font-body);
	font-size: var(--font-base);
	color: var(--color-text);
	line-height: var(--leading-normal);
	-webkit-font-smoothing: antialiased;
	-moz-osx-font-smoothing: grayscale;
}

view, scroll-view, input, button, text {
	box-sizing: border-box;
}

h1, h2, h3, h4 {
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	letter-spacing: var(--tracking-heading);
	line-height: var(--leading-tight);
}

:focus-visible {
	outline: 3rpx solid var(--color-accent);
	outline-offset: 4rpx;
	border-radius: var(--radius-sm);
}

::-webkit-scrollbar {
	width: 0;
	display: none;
}

page, .scroll-content {
	scroll-behavior: smooth;
}

/* 全局过渡 */
.fade-enter-active, .fade-leave-active {
	transition: opacity 0.25s ease;
}
.fade-enter-from, .fade-leave-to {
	opacity: 0;
}

.slide-up-enter-active, .slide-up-leave-active {
	transition: all 0.3s var(--ease-out-expo);
}
.slide-up-enter-from {
	opacity: 0;
	transform: translateY(40rpx);
}
.slide-up-leave-to {
	opacity: 0;
	transform: translateY(-20rpx);
}
</style>
