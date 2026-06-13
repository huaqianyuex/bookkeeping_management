<template>
	<view class="container">
		<view class="type-tabs">
			<view class="type-tab" :class="{ active: formType === 0 }" @click="switchType(0)">
				<text class="type-tab-text" :class="{ active: formType === 0 }">支出</text>
			</view>
			<view class="type-tab" :class="{ active: formType === 1 }" @click="switchType(1)">
				<text class="type-tab-text" :class="{ active: formType === 1 }">收入</text>
			</view>
		</view>

		<view class="amount-section">
			<text class="amount-label">¥</text>
			<input class="amount-input" type="digit" v-model="form.amount" placeholder="0.00" :placeholder-style="'color: var(--color-text-tertiary); font-weight: 300;'" />
		</view>

		<view class="section">
			<text class="section-title">选择分类</text>
			<view class="category-grid">
				<view v-for="c in filteredCategories" :key="c.id" class="category-item" :class="{ active: form.categoryId === c.id }" @click="form.categoryId = c.id">
					<view class="category-icon" :class="c.type === 0 ? 'type-expense' : 'type-income'">
						<text class="category-icon-text">{{ getCategoryEmoji(c.name) }}</text>
					</view>
					<text class="category-name" :class="{ active: form.categoryId === c.id }">{{ c.name }}</text>
				</view>
			</view>
		</view>

		<view class="section">
			<text class="section-title">日期</text>
			<picker mode="date" :value="form.recordDate" @change="onDateChange">
				<view class="date-picker">
					<text class="date-text">{{ form.recordDate || '选择日期' }}</text>
					<text class="date-arrow">›</text>
				</view>
			</picker>
		</view>

		<view class="section">
			<text class="section-title">备注</text>
			<input class="remark-input" v-model="form.remark" placeholder="添加备注（可选）" :placeholder-style="'color: var(--color-text-tertiary);'" />
		</view>

		<view class="submit-btn" :class="{ disabled: !canSubmit }" @click="handleSubmit">
			<text class="submit-text">{{ isEdit ? '保存修改' : '添加记录' }}</text>
		</view>
	</view>
</template>

<script>
import { getRecordDetail, addRecord, updateRecord } from '../../api/record'
import { getCategoryList } from '../../api/category'

export default {
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
		}
	},
	computed: {
		filteredCategories() {
			return this.categories.filter(c => c.type === this.formType)
		},
		canSubmit() {
			return this.form.amount && this.form.amount > 0 && this.form.categoryId && this.form.recordDate
		},
	},
	onLoad(options) {
		if (options.id) {
			this.isEdit = true
			this.recordId = options.id
			uni.setNavigationBarTitle({ title: '编辑账单' })
		} else {
			const today = new Date().toISOString().split('T')[0]
			this.form.recordDate = today
		}
		this.fetchCategories()
	},
	methods: {
		switchType(type) {
			this.formType = type
			if (this.form.categoryId) {
				const cat = this.categories.find(c => c.id === this.form.categoryId)
				if (cat && cat.type !== type) {
					this.form.categoryId = null
				}
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
			if (!this.canSubmit) return
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
					uni.showToast({ title: this.isEdit ? '修改成功' : '添加成功', icon: 'success' })
					setTimeout(() => uni.navigateBack(), 1000)
				} else {
					uni.showToast({ title: res.message, icon: 'none' })
				}
			} catch (e) {
				uni.showToast({ title: '操作失败', icon: 'none' })
			}
		},
	},
}
</script>

<style scoped>
.container {
	min-height: 100vh;
	background-color: var(--color-bg);
	padding-bottom: 160rpx;
}

.type-tabs {
	display: flex;
	padding: var(--space-lg) var(--space-3xl) 0;
	gap: 20rpx;
}

.type-tab {
	flex: 1;
	height: 88rpx;
	border-radius: var(--radius-lg);
	background-color: var(--color-surface);
	display: flex;
	align-items: center;
	justify-content: center;
	transition: all var(--transition-fast);
}

.type-tab.active {
	background-color: var(--color-primary);
}

.type-tab-text {
	font-size: var(--font-lg);
	font-weight: var(--weight-semibold);
	color: var(--color-text-secondary);
}

.type-tab-text.active {
	color: var(--color-text-inverse);
}

.amount-section {
	display: flex;
	align-items: baseline;
	padding: var(--space-xl) var(--space-xl) var(--space-lg);
	background-color: var(--color-surface);
	margin: var(--space-lg) var(--space-lg) 0;
	border-radius: var(--radius-2xl);
	box-shadow: var(--shadow-xs);
	min-width: 0;
}

.amount-label {
	font-size: var(--font-5xl);
	font-weight: var(--weight-bold);
	color: var(--color-text);
	margin-right: var(--space-sm);
	line-height: 1;
}

.amount-input {
	flex: 1;
	font-size: var(--font-4xl);
	font-weight: var(--weight-bold);
	color: var(--color-text);
	min-width: 0;
}

.section {
	background-color: var(--color-surface);
	margin: var(--space-lg) var(--space-lg) 0;
	padding: var(--space-lg);
	border-radius: var(--radius-2xl);
	box-shadow: var(--shadow-xs);
}

.section-title {
	font-size: var(--font-base);
	font-weight: var(--weight-bold);
	color: var(--color-text);
	margin-bottom: var(--space-xl);
	display: block;
}

.category-grid {
	display: grid;
	grid-template-columns: repeat(4, 1fr);
	gap: 20rpx;
}

.category-item {
	display: flex;
	flex-direction: column;
	align-items: center;
	padding: var(--space-lg) 0;
	border-radius: var(--radius-xl);
	background-color: var(--color-bg);
	transition: all var(--transition-fast);
}

.category-item.active {
	background-color: #eef0f2;
}

.category-icon {
	width: 80rpx;
	height: 80rpx;
	border-radius: var(--radius-2xl);
	display: flex;
	align-items: center;
	justify-content: center;
	margin-bottom: var(--space-sm);
}

.category-icon.type-expense {
	background-color: var(--color-danger-light);
}

.category-icon.type-income {
	background-color: var(--color-success-light);
}

.category-icon-text {
	font-size: var(--font-xl);
}

.category-name {
	font-size: var(--font-xs);
	color: var(--color-text-secondary);
	text-align: center;
}

.category-name.active {
	color: var(--color-text);
	font-weight: var(--weight-bold);
}

.date-picker {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: var(--space-lg);
	background-color: var(--color-bg);
	border-radius: var(--radius-lg);
}

.date-text {
	font-size: var(--font-base);
	color: var(--color-primary-light);
}

.date-arrow {
	font-size: var(--font-2xl);
	color: var(--color-text-tertiary);
}

.remark-input {
	padding: var(--space-lg);
	background-color: var(--color-bg);
	border-radius: var(--radius-lg);
	font-size: var(--font-base);
	color: var(--color-primary-light);
}

.submit-btn {
	position: fixed;
	bottom: 0;
	left: 0;
	right: 0;
	margin: var(--space-3xl);
	height: 100rpx;
	background-color: var(--color-primary);
	border-radius: var(--radius-2xl);
	display: flex;
	align-items: center;
	justify-content: center;
	box-shadow: var(--shadow-primary);
}

.submit-btn.disabled {
	opacity: 0.5;
}

.submit-text {
	font-size: var(--font-xl);
	font-weight: var(--weight-bold);
	color: var(--color-text-inverse);
}
</style>
