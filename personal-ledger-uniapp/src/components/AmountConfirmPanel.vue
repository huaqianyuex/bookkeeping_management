<template>
	<view v-if="visible" class="confirm-mask" @touchmove.stop.prevent @click="handleCancel">
		<view class="confirm-sheet" @click.stop>
			<!-- 头部：标题 + 来源标记 -->
			<view class="confirm-head">
				<view class="head-left">
					<text class="confirm-title">确认记账金额</text>
					<view class="source-tag" :class="'source-tag--' + source">
						<text class="source-tag-text">{{ source === 'voice' ? '语音识别' : '文字输入' }}</text>
					</view>
				</view>
				<text class="confirm-sub">请核对金额，可直接修改后再入账</text>
			</view>

			<!-- 条目列表：每条展示分类/日期 + 可编辑金额 -->
			<scroll-view class="confirm-list" scroll-y :style="{ maxHeight: listMaxHeight }">
				<view
					v-for="(row, i) in rows"
					:key="row.index"
					class="confirm-row"
					:class="{ 'confirm-row--invalid': row.invalid, 'confirm-row--active': activeIndex === i }"
				>
					<view class="row-main">
						<view class="row-title-line">
							<text class="row-category">{{ row.categoryName || '未识别分类' }}</text>
							<view v-if="row.type !== null && row.type !== undefined" class="type-tag" :class="row.type === 1 ? 'type-tag--income' : 'type-tag--expense'">
								<text class="type-tag-text">{{ row.type === 1 ? '收入' : '支出' }}</text>
							</view>
						</view>
						<view class="row-meta">
							<text class="row-date">{{ row.date || row.dateExpr || '今天' }}</text>
							<text v-if="row.amountRaw" class="row-raw">识别为「{{ row.amountRaw }}」</text>
							<text v-if="row.lowConf" class="row-hint">把握不大</text>
						</view>
					</view>

					<!-- 金额编辑区：点按直接改 -->
					<view class="row-amount" :class="{ 'row-amount--invalid': row.invalid }">
						<text class="row-symbol">¥</text>
						<input
							class="row-input"
							type="digit"
							:value="row.amountText"
							placeholder="0.00"
							placeholder-class="row-input-ph"
							:disabled="submitting"
							@input="onAmountInput(i, $event)"
							@focus="activeIndex = i"
							@blur="activeIndex = -1"
						/>
					</view>
				</view>
			</scroll-view>

			<!-- 多笔时显示合计 -->
			<view v-if="rows.length > 1" class="confirm-total">
				<text class="total-label">共 {{ rows.length }} 笔 · 合计</text>
				<text class="total-value">¥{{ totalText }}</text>
			</view>

			<!-- 服务端提示（未识别分类 / 低置信度） -->
			<view v-if="warnings.length" class="confirm-warnings">
				<text v-for="(w, i) in warnings" :key="i" class="warning-line">· {{ w }}</text>
			</view>

			<text v-if="errorText" class="confirm-error">{{ errorText }}</text>

			<!-- 操作 -->
			<view class="confirm-actions">
				<button class="confirm-btn confirm-btn--ghost" :disabled="submitting" @click="handleCancel">取消</button>
				<button
					class="confirm-btn confirm-btn--primary"
					:disabled="!canConfirm || submitting"
					:loading="submitting"
					@click="handleConfirm"
				>
					确认记账
				</button>
			</view>
		</view>
	</view>
</template>

<script setup>
/**
 * 金额确认框（语音 / 文字记账共用）
 *
 * 数据来自 POST /api/ai/bookkeeping 的 dryRun=true 预览：preview.items[]，
 * 每项含 index（覆盖定位键）/ amount / amountRaw / categoryName / date / dateExpr /
 * confidence 等。本组件只做「展示 + 编辑 + 校验」，入账请求由父页面发起。
 *
 * 提交时按下标回传**改过的**字段（overrides=[{index, amount}]）：
 *  - 只有金额发生变化（或原本缺金额被补上）的条目才进 overrides，减少无效覆盖；
 *  - 全部金额非法 / 为空时「确认记账」保持禁用，避免把缺金额的条目静默丢弃。
 */
import { ref, computed, watch } from 'vue'

const props = defineProps({
	/** 是否显示 */
	visible: { type: Boolean, default: false },
	/** 预览条目数组（服务端 preview.items） */
	items: { type: Array, default: () => [] },
	/** 服务端 warnings（未识别分类 / 低置信度提示） */
	warnings: { type: Array, default: () => [] },
	/** 输入来源：text=文字 / voice=语音 */
	source: { type: String, default: 'text' },
	/** 父页面正在提交入账请求 */
	submitting: { type: Boolean, default: false },
})

const emit = defineEmits(['confirm', 'cancel'])

const MAX_AMOUNT = 99999999.99
const LOW_CONFIDENCE = 0.5   // 与后端 config.settings BK_LOW_CONFIDENCE 同值
const listMaxHeight = '40vh'

const rows = ref([])
const activeIndex = ref(-1)

/** 把服务端预览条目转成可编辑行（金额统一成字符串，便于输入框双向处理） */
function buildRows(items) {
	return (items || []).map((it) => {
		const original = it.amount === null || it.amount === undefined ? null : Number(it.amount)
		const conf = Number(it.confidence) || 0
		return {
			index: it.index,
			originalAmount: original,
			amountText: original === null ? '' : String(original),
			categoryName: it.categoryName || null,
			date: it.date || null,
			dateExpr: it.dateExpr || null,
			amountRaw: it.amountRaw || null,
			type: it.type === null || it.type === undefined ? null : it.type,
			lowConf: conf > 0 && conf < LOW_CONFIDENCE,
			invalid: false,
		}
	})
}

// 每次弹出（items 变化）都重建编辑态，避免残留上一次的修改
watch(
	() => [props.visible, props.items],
	() => {
		if (props.visible) {
			rows.value = buildRows(props.items)
			activeIndex.value = -1
		}
	},
	{ immediate: true }
)

/** 输入清洗：只留数字与一个小数点，整数位 ≤8、小数位 ≤2 */
function sanitizeAmount(raw) {
	let s = String(raw == null ? '' : raw).replace(/[^\d.]/g, '')
	const firstDot = s.indexOf('.')
	if (firstDot !== -1) {
		const intPart = s.slice(0, firstDot).slice(0, 8)
		const decPart = s.slice(firstDot + 1).replace(/\./g, '').slice(0, 2)
		s = intPart + '.' + decPart
	} else {
		s = s.slice(0, 8)
	}
	return s
}

/** 金额合法性：非空、>0、≤ 上限 */
function isValidAmount(text) {
	if (text === '' || text === '.') return false
	const n = Number(text)
	return Number.isFinite(n) && n > 0 && n <= MAX_AMOUNT
}

function onAmountInput(i, e) {
	const cleaned = sanitizeAmount(e && e.detail ? e.detail.value : '')
	rows.value[i].amountText = cleaned
	rows.value[i].invalid = cleaned !== '' && !isValidAmount(cleaned)
}

const invalidRows = computed(() => rows.value.filter((r) => !isValidAmount(r.amountText)))

const canConfirm = computed(() => rows.value.length > 0 && invalidRows.value.length === 0)

const totalText = computed(() => {
	const sum = rows.value.reduce((acc, r) => acc + (isValidAmount(r.amountText) ? Number(r.amountText) : 0), 0)
	return sum.toFixed(2)
})

const errorText = computed(() => {
	if (rows.value.length === 0) return '没有可确认的记账条目'
	if (invalidRows.value.length > 0) {
		return invalidRows.value.some((r) => r.amountText === '')
			? '请补全每笔金额后再确认'
			: '金额需大于 0 且不超过 99,999,999.99'
	}
	return ''
})

/** 只回传发生变化的金额（含原本缺金额被补上的条目） */
function buildOverrides() {
	return rows.value
		.filter((r) => {
			if (!isValidAmount(r.amountText)) return false
			return r.originalAmount === null || Number(r.amountText) !== r.originalAmount
		})
		.map((r) => ({ index: r.index, amount: Number(r.amountText) }))
}

function handleConfirm() {
	if (!canConfirm.value || props.submitting) return
	emit('confirm', { overrides: buildOverrides() })
}

function handleCancel() {
	if (props.submitting) return
	emit('cancel')
}
</script>

<style scoped>
/* ── 遮罩：底部弹层锚点 ──
   z-index 必须**高于**悬浮 TabBar（TabBar.vue 的 .tab-bar-wrap 是 999）：
   两者同为 999 且 TabBar 在 DOM 中更靠后，会把面板与 FAB 一起压在下面。
   底部留出 TabBar 高度 + 安全区，把整块面板抬到悬浮导航栏之上。 */
.confirm-mask {
	position: fixed;
	inset: 0;
	z-index: 1000;
	display: flex;
	align-items: flex-end;
	padding: 0 var(--space-lg) calc(var(--tabbar-height) + var(--space-lg) + env(safe-area-inset-bottom));
	background-color: var(--color-overlay);
	box-sizing: border-box;
}

/* ── 面板：悬浮卡片（四角同圆角，脱离屏幕底边） ── */
.confirm-sheet {
	width: 100%;
	background-color: var(--color-surface);
	border-radius: var(--radius-3xl);
	padding: var(--space-2xl);
	box-sizing: border-box;
	animation: sheet-rise var(--transition-slow) var(--ease-out-back);
}

@keyframes sheet-rise {
	from { transform: translateY(100%); }
	to { transform: translateY(0); }
}

.confirm-head {
	display: flex;
	flex-direction: column;
	gap: var(--space-2xs);
	margin-bottom: var(--space-lg);
}

.head-left {
	display: flex;
	align-items: center;
	gap: var(--space-md);
}

.confirm-title {
	font-size: var(--font-lg);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
}

.source-tag {
	padding: 4rpx var(--space-md);
	border-radius: var(--radius-full);
}

.source-tag--voice {
	background-color: var(--color-accent-light);
}

.source-tag--text {
	background-color: var(--color-surface-raised);
}

.source-tag-text {
	font-size: var(--font-2xs);
	font-weight: var(--weight-semibold);
	color: var(--color-text-secondary);
}

.source-tag--voice .source-tag-text {
	color: var(--color-accent-deep);
}

.confirm-sub {
	font-size: var(--font-sm);
	color: var(--color-text-tertiary);
}

/* ── 条目行 ── */
.confirm-list {
	width: 100%;
}

.confirm-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--space-lg);
	padding: var(--space-lg) 0;
	border-bottom: var(--hairline) solid var(--color-divider);
}

.confirm-row:last-child {
	border-bottom: none;
}

/* 正在编辑的行：左侧加一条琥珀色标记，弱提示当前焦点 */
.confirm-row--active .row-category {
	color: var(--color-accent-deep);
}

.confirm-row--invalid .row-category {
	color: var(--color-danger);
}

.row-main {
	flex: 1;
	min-width: 0;
	display: flex;
	flex-direction: column;
	gap: var(--space-2xs);
}

.row-title-line {
	display: flex;
	align-items: center;
	gap: var(--space-sm);
}

.row-category {
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
	color: var(--color-text);
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.type-tag {
	padding: 2rpx var(--space-sm);
	border-radius: var(--radius-sm);
	flex-shrink: 0;
}

.type-tag--expense {
	background-color: var(--color-danger-light);
}

.type-tag--income {
	background-color: var(--color-success-light);
}

.type-tag-text {
	font-size: var(--font-2xs);
	font-weight: var(--weight-semibold);
}

.type-tag--expense .type-tag-text {
	color: var(--color-danger);
}

.type-tag--income .type-tag-text {
	color: var(--color-success);
}

.row-meta {
	display: flex;
	align-items: center;
	gap: var(--space-sm);
	flex-wrap: wrap;
}

.row-date {
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
}

.row-raw {
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	max-width: 280rpx;
}

.row-hint {
	font-size: var(--font-xs);
	color: var(--color-warning-text);
}

/* ── 金额编辑区 ── */
.row-amount {
	display: flex;
	align-items: center;
	gap: var(--space-2xs);
	flex-shrink: 0;
	min-width: 220rpx;
	padding: var(--space-sm) var(--space-md);
	border-radius: var(--radius-md);
	background-color: var(--color-surface-raised);
	border: var(--hairline) solid transparent;
	transition: border-color var(--transition-fast), background-color var(--transition-fast);
}

.row-amount--invalid {
	border-color: var(--color-danger);
	background-color: var(--color-danger-light);
}

.row-symbol {
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
	color: var(--color-text-heading);
}

.row-input {
	flex: 1;
	min-width: 0;
	height: 56rpx;
	font-family: var(--font-amount);
	font-variant-numeric: tabular-nums;
	font-size: var(--font-lg);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	text-align: right;
	letter-spacing: var(--tracking-amount);
}

.row-input-ph {
	color: var(--color-disabled-text);
	font-weight: var(--weight-normal);
}

/* ── 合计 ── */
.confirm-total {
	display: flex;
	align-items: baseline;
	justify-content: space-between;
	margin-top: var(--space-lg);
	padding-top: var(--space-lg);
	border-top: var(--hairline) solid var(--color-border);
}

.total-label {
	font-size: var(--font-sm);
	color: var(--color-text-secondary);
}

.total-value {
	font-family: var(--font-amount);
	font-variant-numeric: tabular-nums;
	font-size: var(--font-xl);
	font-weight: var(--weight-extrabold);
	color: var(--color-text-heading);
	letter-spacing: var(--tracking-amount);
}

/* ── 提示 / 错误 ── */
.confirm-warnings {
	margin-top: var(--space-md);
	display: flex;
	flex-direction: column;
	gap: var(--space-2xs);
}

.warning-line {
	font-size: var(--font-xs);
	color: var(--color-warning-text);
	line-height: var(--leading-normal);
}

.confirm-error {
	display: block;
	margin-top: var(--space-md);
	font-size: var(--font-xs);
	color: var(--color-danger);
}

/* ── 操作按钮 ── */
.confirm-actions {
	display: flex;
	gap: var(--space-lg);
	margin-top: var(--space-2xl);
}

.confirm-btn {
	flex: 1;
	height: 88rpx;
	border-radius: var(--radius-full);
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
	display: flex;
	align-items: center;
	justify-content: center;
	line-height: 1;
}

.confirm-btn::after {
	border: none;
}

.confirm-btn--ghost {
	background-color: var(--color-surface-raised);
	color: var(--color-text);
}

.confirm-btn--primary {
	background-color: var(--color-primary);
	color: var(--color-text-inverse);
}

.confirm-btn--primary[disabled] {
	opacity: 0.4;
	color: var(--color-text-inverse);
	background-color: var(--color-primary);
}
</style>
