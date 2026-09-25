<template>
	<view class="page">
		<!-- 可滚动内容区 -->
		<scroll-view scroll-y class="scroll-area">
			<!-- 设计稿02：支出/收入 胶囊分段切换 -->
			<view class="type-tabs">
				<view class="type-tab" :class="{ active: formType === 0 }" @click="switchType(0)">
					<text class="type-tab-text" :class="{ active: formType === 0 }">支出</text>
				</view>
				<view class="type-tab" :class="{ active: formType === 1 }" @click="switchType(1)">
					<text class="type-tab-text" :class="{ active: formType === 1 }">收入</text>
				</view>
			</view>

			<!-- 设计稿02：左对齐大金额 + 黄色光标 -->
			<view class="amount-display">
				<view class="amount-row">
					<text class="amount-currency">¥</text>
					<text class="amount-integer">{{ displayInteger }}</text>
					<text class="amount-dot" v-if="displayDecimal">.</text>
					<text class="amount-decimal" v-if="displayDecimal">{{ displayDecimal }}</text>
					<view class="amount-cursor" :class="{ blink: !displayAmount }"></view>
				</view>
				<!-- 设计稿02：金额下方已选分类提示（仅展示已有状态） -->
				<text v-if="form.categoryId" class="amount-category-hint">已选分类 · {{ (categories.find(c => c.id === form.categoryId) || {}).name }}</text>
			</view>

			<!-- 设计稿02：粉彩四列分类网格，选中黄底 -->
			<view class="section category-section">
				<view class="category-grid">
						<view
							v-for="(c, idx) in filteredCategories"
							:key="c.id"
							class="category-item stagger-item"
							:class="{ active: form.categoryId === c.id }"
							:style="{ animationDelay: idx * 0.03 + 's' }"
							@click="selectCategory(c.id)"
						>
							<!-- 底色按分类 id 取模，同一分类永远同色，不随排序漂移 -->
							<view class="category-icon" :class="['cat-palette-' + (c.id % 7), { selected: form.categoryId === c.id }]">
								<text class="category-icon-text">{{ getCategoryEmoji(c.name) }}</text>
							</view>
							<text class="category-name" :class="{ active: form.categoryId === c.id }">{{ c.name }}</text>
						</view>
				</view>
			</view>

			<!-- 日期 + 备注（日期用原生 picker，支持补记任意日期） -->
			<view class="section">
				<picker class="date-picker" mode="date" :value="form.recordDate" @change="onDateChange">
					<view class="form-row">
						<text class="form-label">日期</text>
						<view class="form-value-row">
							<text class="form-value">{{ form.recordDate || '选择日期' }}</text>
							<text class="form-arrow">›</text>
						</view>
					</view>
				</picker>
				<view class="form-divider"></view>
				<view class="form-row">
					<text class="form-label">备注</text>
					<input class="form-input" v-model="form.remark" placeholder="添加备注（可选）" :placeholder-style="'color: var(--color-text-tertiary);'" />
				</view>
			</view>
			<view class="scroll-bottom-spacer"></view>
		</scroll-view>

		<!-- 键盘固定在底部 -->
		<view class="keyboard-wrap">
			<view class="keyboard">
				<view class="keyboard-row" v-for="(row, ri) in keyboardLayout" :key="ri">
					<view
						v-for="key in row"
						:key="key"
						class="key"
						:class="{ 'key-delete': key === 'del' }"
						@click="onKeyPress(key)"
					>
						<text class="key-text">{{ key === 'del' ? '⌫' : key }}</text>
					</view>
				</view>
			</view>
			<view class="confirm-area" :style="{ paddingBottom: safeBottom + 'px' }">
				<text v-if="!canSubmit && missingHint" class="confirm-hint">{{ missingHint }}</text>
				<view class="confirm-btn" :class="{ disabled: !canSubmit || submitting }" @click="onKeyPress('ok')">
					<text class="confirm-text">{{ submitLabel }}</text>
				</view>
			</view>
		</view>

		<!-- 成功动画 -->
		<SuccessAnimation :visible="showSuccess" :message="isEdit ? '修改成功' : '记账成功'" @done="onSuccessDone" />
	</view>
</template>

<script>
import { getRecordDetail, addRecord, updateRecord } from '../../api/record'
import { getCategoryList } from '../../api/category'
import SuccessAnimation from '../../components/SuccessAnimation.vue'

export default {
	components: { SuccessAnimation },
	data() {
		return {
			isEdit: false,
			recordId: null,
			formType: 0,
			form: {
				amount: '',
				categoryId: null,
				recordDate: '',
				remark: '',
			},
			categories: [],
			showKeyboard: true,
			showSuccess: false,
			submitting: false,
			safeBottom: 0,
			keyboardLayout: [
				['1', '2', '3'],
				['4', '5', '6'],
				['7', '8', '9'],
				['.', '0', 'del'],
			],
		}
	},
	computed: {
		filteredCategories() {
			return this.categories.filter(c => c.type === this.formType)
		},
		canSubmit() {
			return this.form.amount && Number(this.form.amount) > 0 && this.form.categoryId && this.form.recordDate
		},
		/** 置灰确认键的缺项原因，让「不能提交」可被理解 */
		missingHint() {
			if (!this.form.amount || Number(this.form.amount) <= 0) return '请输入金额'
			if (!this.form.categoryId) return '请选择分类'
			if (!this.form.recordDate) return '请选择日期'
			return ''
		},
		submitLabel() {
			if (this.submitting) return '保存中…'
			return this.isEdit ? '保存修改' : '记一笔'
		},
		displayAmount() {
			return this.form.amount || ''
		},
		displayInteger() {
			if (!this.displayAmount) return '0'
			const parts = this.displayAmount.split('.')
			return parts[0] || '0'
		},
		displayDecimal() {
			if (!this.displayAmount) return ''
			const parts = this.displayAmount.split('.')
			return parts[1] || ''
		},
	},
	onLoad(options) {
		const sys = uni.getSystemInfoSync()
		this.safeBottom = sys.safeAreaInsets?.bottom || 0
		if (options.id) {
			this.isEdit = true
			this.recordId = options.id
			uni.setNavigationBarTitle({ title: '编辑账单' })
		} else {
			// 恢复上次未提交的记账草稿（切出去回消息、误退出的场景不再丢内容）
			const draft = uni.getStorageSync('record_draft')
			if (draft) {
				try {
					const d = JSON.parse(draft)
					if (d && typeof d === 'object') {
						this.formType = d.formType === 1 ? 1 : 0
						this.form.amount = d.amount || ''
						this.form.categoryId = d.categoryId || null
						this.form.recordDate = d.recordDate || ''
						this.form.remark = d.remark || ''
					}
				} catch (e) {}
			}
			if (!this.form.recordDate) this.form.recordDate = this.getToday()
		}
		this.fetchCategories()
	},
	watch: {
		// 新增模式随时落草稿；编辑模式不落（避免覆盖成编辑中的旧账数据）
		form: {
			handler() {
				if (this.isEdit) return
				uni.setStorageSync('record_draft', JSON.stringify({ ...this.form, formType: this.formType }))
			},
			deep: true,
		},
	},
	methods: {
		getToday() {
			const d = new Date()
			return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
		},
		switchType(type) {
			this.formType = type
			if (this.form.categoryId) {
				const cat = this.categories.find(c => c.id === this.form.categoryId)
				if (cat && cat.type !== type) {
					this.form.categoryId = null
				}
			}
		},
		selectCategory(id) {
			this.form.categoryId = id
		},
		onKeyPress(key) {
			if (key === 'del') {
				this.form.amount = this.form.amount.slice(0, -1)
			} else if (key === 'ok') {
				if (this.canSubmit) this.handleSubmit()
			} else if (key === '.') {
				// 只允许一个小数点
				if (!this.form.amount.includes('.')) {
					this.form.amount += '.'
				}
			} else {
				// 限制小数点后两位
				const parts = this.form.amount.split('.')
				if (parts.length === 2 && parts[1].length >= 2) return
				// 限制总长度
				if (this.form.amount.replace('.', '').length >= 10) return
				this.form.amount += key
			}
		},
		onDateChange(e) {
			this.form.recordDate = e.detail.value
		},
		getCategoryEmoji(name) {
			const map = {
				'餐饮': '🍜', '交通': '🚗', '购物': '🛒', '娱乐': '🎮', '医疗': '💊',
				'教育': '📚', '住房': '🏠', '通讯': '📱', '服饰': '👔', '运动': '⚽',
				'旅行': '✈️', '礼物': '🎁', '其他': '📦',
				'工资': '💰', '奖金': '🏆', '兼职': '💼', '投资': '📈', '红包': '🧧',
				'其他收入': '💵',
			}
			return map[name] || '📝'
		},
		async fetchCategories() {
			try {
				const res = await getCategoryList()
				if (res.code === 200) {
					this.categories = res.data
					// 草稿里存的分类可能已被删除，避免提交到不存在的分类
					if (!this.isEdit && this.form.categoryId) {
						const exists = this.categories.some(c => c.id === this.form.categoryId)
						if (!exists) this.form.categoryId = null
					}
					if (this.isEdit) this.fetchRecord()
				}
			} catch (e) {
				console.error(e)
			}
		},
		async fetchRecord() {
			try {
				const res = await getRecordDetail(this.recordId)
				if (res.code === 200) {
					const d = res.data
					this.formType = d.categoryType
					this.form.amount = String(d.amount)
					this.form.categoryId = d.categoryId
					this.form.recordDate = d.recordDate
					this.form.remark = d.remark || ''
				}
			} catch (e) {
				console.error(e)
			}
		},
		async handleSubmit() {
			// 防重：请求在途时忽略再次点击，避免慢网双击记两笔
			if (!this.canSubmit || this.submitting) return
			this.submitting = true
			const data = {
				amount: this.form.amount,
				categoryId: this.form.categoryId,
				recordDate: this.form.recordDate,
				remark: this.form.remark,
			}
			try {
				const res = this.isEdit
					? await updateRecord(this.recordId, data)
					: await addRecord(data)
				if (res.code === 200) {
					if (!this.isEdit) uni.removeStorageSync('record_draft')
					this.showSuccess = true
				} else {
					uni.showToast({ title: res.message, icon: 'none' })
				}
			} catch (e) {
				uni.showToast({ title: '操作失败', icon: 'none' })
			} finally {
				this.submitting = false
			}
		},
		onSuccessDone() {
			this.showSuccess = false
			uni.navigateBack()
		},
	},
}
</script>

<style scoped>
.page {
	/* H5 端 100vh 含原生导航栏高度，会裁掉底部确认键；--window-top 由 uni-app 注入，小程序端缺省回退 0 */
	height: calc(100vh - var(--window-top, 0px));
	background-color: var(--color-bg);
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.scroll-area {
	flex: 1;
	overflow: hidden;
}

/* 设计稿02：灰底胶囊分段控件，选中墨黑胶囊 */
.type-tabs {
	display: flex;
	margin: var(--space-lg) var(--space-xl) 0;
	padding: var(--space-xs);
	gap: var(--space-xs);
	border-radius: var(--radius-full);
	background-color: var(--color-surface-raised);
}

.type-tab {
	flex: 1;
	height: 72rpx;
	border-radius: var(--radius-full);
	background-color: transparent;
	display: flex;
	align-items: center;
	justify-content: center;
	transition: all 0.2s var(--ease-out-expo);
}

.type-tab.active {
	background-color: var(--color-primary);
}

.type-tab-text {
	font-size: var(--font-base);
	font-weight: var(--weight-medium);
	color: var(--color-text-secondary);
	transition: color 0.2s ease;
}

.type-tab-text.active {
	color: var(--color-text-inverse);
	font-weight: var(--weight-semibold);
}

/* 设计稿02：金额左对齐、¥ 缩小、黄色光标 */
.amount-display {
	padding: var(--space-2xl) var(--space-xl) var(--space-lg);
}

.amount-row {
	display: flex;
	align-items: baseline;
	justify-content: flex-start;
	line-height: 1;
}

.amount-currency {
	font-size: var(--font-2xl);
	font-weight: var(--weight-semibold);
	color: var(--color-text-tertiary);
	margin-right: 6rpx;
	font-family: var(--font-amount);
}

.amount-integer {
	font-size: var(--font-keypad);
	font-weight: var(--weight-extrabold);
	color: var(--color-text-heading);
	letter-spacing: -2rpx;
	font-family: var(--font-amount);
	font-variant-numeric: tabular-nums;
}

.amount-dot {
	font-size: var(--font-3xl);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	margin: 0 2rpx;
	font-family: var(--font-amount);
}

.amount-decimal {
	font-size: var(--font-3xl);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	font-family: var(--font-amount);
	font-variant-numeric: tabular-nums;
}

.amount-cursor {
	width: 6rpx;
	height: 88rpx;
	background-color: var(--color-accent);
	border-radius: var(--radius-full);
	margin-left: var(--space-xs);
}

.amount-cursor.blink {
	animation: cursorBlink 1s step-end infinite;
}

@keyframes cursorBlink {
	50% { opacity: 0; }
}

/* 设计稿02：金额下方灰色已选分类提示 */
.amount-category-hint {
	display: block;
	margin-top: var(--space-md);
	font-size: var(--font-sm);
	color: var(--color-text-tertiary);
}

/* 设计稿02：分类网格白卡区域 */
.section {
	background-color: var(--color-surface);
	margin: var(--space-md) var(--space-lg) 0;
	padding: var(--space-lg);
	border-radius: var(--radius-2xl);
	box-shadow: var(--shadow-card);
}

.category-section {
	margin: var(--space-md) var(--space-xl) 0;
	padding: var(--space-md) 0;
	background-color: transparent;
	box-shadow: none;
}

/* 四列网格 + 底色透明（设计稿02 图标直接落在页面底色上） */
.category-grid {
	display: flex;
	flex-wrap: wrap;
}

.category-item {
	display: flex;
	flex-direction: column;
	align-items: center;
	width: 25%;
	padding: var(--space-md) 0;
	border-radius: var(--radius-lg);
	background-color: transparent;
	transition: background-color 0.15s ease;
}

.category-item:active {
	opacity: 0.85;
}

.category-item.active {
	background-color: transparent;
}

/* 粉彩圆角方块图标（设计稿02/05/08 色板），选中转黄 */
.category-icon {
	width: 96rpx;
	height: 96rpx;
	border-radius: var(--radius-2xl);
	display: flex;
	align-items: center;
	justify-content: center;
	margin-bottom: var(--space-sm);
	transition: background-color 0.15s ease;
}

.category-icon.cat-palette-0 { background-color: var(--cat-yellow); }
.category-icon.cat-palette-1 { background-color: var(--cat-pink); }
.category-icon.cat-palette-2 { background-color: var(--cat-blue); }
.category-icon.cat-palette-3 { background-color: var(--cat-orange); }
.category-icon.cat-palette-4 { background-color: var(--cat-green); }
.category-icon.cat-palette-5 { background-color: var(--cat-purple); }
.category-icon.cat-palette-6 { background-color: var(--cat-gray); }

.category-icon.selected {
	background-color: var(--color-accent);
	box-shadow: var(--shadow-accent);
}

.category-icon-text { font-size: var(--font-2xl); }

.category-name {
	font-size: var(--font-sm);
	color: var(--color-text-secondary);
	text-align: center;
	transition: color 0.2s ease;
}

.category-item.active .category-name {
	color: var(--color-text-heading);
	font-weight: var(--weight-bold);
}

.date-picker {
	display: block;
}

.form-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: var(--space-lg) 0;
}

.form-divider {
	height: 1rpx;
	background-color: var(--color-divider);
}

.form-label {
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
	color: var(--color-text);
}

.form-value-row {
	display: flex;
	align-items: center;
	gap: var(--space-xs);
}

.form-value {
	font-size: var(--font-base);
	color: var(--color-text-secondary);
}

.form-arrow {
	font-size: var(--font-xl);
	color: var(--color-text-tertiary);
}

.form-input {
	flex: 1;
	text-align: right;
	font-size: var(--font-base);
	color: var(--color-text);
	margin-left: var(--space-lg);
}

.scroll-bottom-spacer {
	height: 40rpx;
}

/* ── 键盘固定底部（设计稿02：极简数字键盘，无按键底色） ── */
.keyboard-wrap {
	flex-shrink: 0;
	background-color: var(--color-bg);
}

.keyboard {
	padding: var(--space-md) var(--space-xl) var(--space-sm);
}

.keyboard-row {
	display: flex;
	gap: 12rpx;
	margin-bottom: 12rpx;
}

.keyboard-row:last-child {
	margin-bottom: 0;
}

.key {
	flex: 1;
	height: 108rpx;
	border-radius: var(--radius-lg);
	background-color: transparent;
	display: flex;
	align-items: center;
	justify-content: center;
	transition: all 0.15s ease;
}

.key:active {
	transform: scale(0.94);
	background-color: var(--color-surface-raised);
	border-radius: var(--radius-full);
}

.key-delete {
	background-color: transparent;
}

.key-text {
	font-size: var(--font-2xl);
	font-weight: var(--weight-normal);
	color: var(--color-text);
	font-family: var(--font-amount);
}

.confirm-area {
	padding: var(--space-sm) var(--space-xl) var(--space-md);
}

.confirm-hint {
	display: block;
	text-align: center;
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
	margin-bottom: var(--space-xs);
}

/* 设计稿02：黑色胶囊「完成」按钮 */
.confirm-btn {
	height: 104rpx;
	border-radius: var(--radius-full);
	background: var(--color-primary);
	box-shadow: var(--shadow-primary);
	display: flex;
	align-items: center;
	justify-content: center;
	transition: opacity 0.15s ease;
}

.confirm-btn:active {
	opacity: 0.88;
}

.confirm-btn.disabled {
	opacity: 0.35;
	box-shadow: none;
}

.confirm-text {
	font-size: var(--font-lg);
	font-weight: var(--weight-semibold);
	color: var(--color-text-inverse);
	letter-spacing: 2rpx;
}
</style>
