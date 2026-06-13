<script>
export default {
	onLaunch() {
		console.log('App Launch')
		// 启动时检查登录态，未登录则跳转到登录页
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

/* ============================
   Global Base Styles
   ============================ */
page {
	background-color: var(--color-bg);
	font-family:
		"PingFang SC",
		"Hiragino Sans GB",
		"Microsoft YaHei",
		"Noto Sans SC",
		-apple-system,
		BlinkMacSystemFont,
		"Segoe UI",
		Roboto,
		"Helvetica Neue",
		Arial,
		sans-serif;
	font-size: var(--font-base);
	color: var(--color-text);
	line-height: var(--leading-normal);
	-webkit-font-smoothing: antialiased;
	-moz-osx-font-smoothing: grayscale;
}

view,
scroll-view,
input,
button,
text {
	box-sizing: border-box;
}

/* Heading defaults */
h1, h2, h3, h4 {
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	letter-spacing: var(--tracking-heading);
	line-height: var(--leading-tight);
}

/* Focus ring for keyboard navigation */
:focus-visible {
	outline: 3rpx solid var(--color-primary);
	outline-offset: 4rpx;
	border-radius: var(--radius-sm);
}

/* Scrollbar (H5) */
::-webkit-scrollbar {
	width: 0;
	display: none;
}

/* SMOoth scroll (H5) */
page,
.scroll-content {
	scroll-behavior: smooth;
}
</style>
