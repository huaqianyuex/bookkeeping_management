<template>
	<view class="container">
		<!-- 加载骨架：与真实版式同构（档位行 / 用量行 / 兑换栏） -->
		<view v-if="loading" class="scroll-content">
			<view class="tier-head">
				<view class="skl skl-chip"></view>
				<view class="tier-main">
					<view class="skl skl-line" style="width: 240rpx"></view>
					<view class="skl skl-line" style="width: 340rpx"></view>
				</view>
			</view>
			<view class="section">
				<view class="skl skl-line" style="width: 180rpx"></view>
				<view v-for="i in 3" :key="i" class="skl-usage">
					<view class="skl skl-line" style="width: 100%"></view>
					<view class="skl skl-track"></view>
				</view>
			</view>
			<view class="section">
				<view class="skl skl-field"></view>
				<view class="skl skl-btn"></view>
			</view>
		</view>

		<!-- 加载失败：显式错误态 + 重试 -->
		<view v-else-if="error" class="scroll-content">
			<empty-state mode="error" icon="alert" title="会员信息加载失败" :description="error">
				<template #action>
					<view class="retry-btn" @click="fetchStatus">
						<text class="retry-text">重试</text>
					</view>
				</template>
			</empty-state>
		</view>

		<view v-else class="scroll-content">
			<!-- ── 档位区：等级 + 状态 + 有效期 ── -->
			<view class="tier-head">
				<view class="tier-chip" :class="isMember ? 'tier-chip--member' : 'tier-chip--free'">
					<app-icon :name="isMember ? 'crown-amber' : 'crown-muted'" :size="44"></app-icon>
				</view>
				<view class="tier-main">
					<view class="tier-row">
						<text class="tier-name">{{ tierName }}</text>
						<view class="chip" :class="stateClass">
							<text class="chip-text">{{ stateLabel }}</text>
						</view>
					</view>
					<text class="tier-validity" :class="{ 'tier-validity--alarm': expired || expiringSoon }">
						{{ validityText }}
					</text>
				</view>
			</view>

			<!-- ── 今日用量：值/上限等宽数字 + 发丝轨道占比条 ── -->
			<view class="section">
				<view class="section-head">
					<text class="section-title">今日用量</text>
					<text class="section-sub">每日零点重置</text>
				</view>
				<view class="usage-list">
					<view v-for="(row, index) in usageRows" :key="row.key" class="usage-row">
						<view class="usage-line">
							<view class="usage-left">
								<app-icon :name="row.icon" :size="32"></app-icon>
								<text class="usage-name">{{ row.label }}</text>
								<view v-if="row.exhausted" class="chip is-danger">
									<text class="chip-text">已用尽</text>
								</view>
							</view>
							<text class="usage-nums">
								{{ row.used }}
								<text class="usage-limit">/ {{ row.limit }} 次</text>
							</text>
						</view>
						<view class="usage-track">
							<view
								class="usage-fill"
								:class="{ 'usage-fill--danger': row.exhausted }"
								:style="{ width: row.pct + '%', animationDelay: index * 55 + 'ms' }"
							></view>
						</view>
					</view>
				</view>
			</view>

			<!-- ── 我的权益：当前档位的具体权益明细（数值全部来自接口） ── -->
			<view class="section">
				<view class="section-head">
					<text class="section-title">我的权益</text>
					<text class="section-sub">{{ tierName }}档位</text>
				</view>
				<view class="benefit-list">
					<view v-for="(row, index) in benefitRows" :key="row.key" class="benefit-row">
						<view class="benefit-left">
							<app-icon :name="row.icon" :size="32"></app-icon>
							<text class="benefit-name">{{ row.label }}</text>
						</view>
						<view v-if="row.key === 'premiumModel'" class="chip" :class="row.enabled ? 'is-ink' : 'is-muted'">
							<text class="chip-text">{{ row.enabled ? '已启用' : '未启用' }}</text>
						</view>
						<text v-else class="benefit-value">{{ row.text }}</text>
					</view>
				</view>
			</view>

			<!-- ── 开通 / 续费：套餐直购（服务端定价，客户端只传套餐 ID）── -->
			<view class="section">
				<view class="section-head">
					<text class="section-title">开通 / 续费</text>
					<view class="section-link" @click="goRecords">
						<app-icon name="history" :size="26"></app-icon>
						<text class="section-link-text">充值记录</text>
					</view>
				</view>
				<!-- 当前账号状态卡：档位 + 今日剩余额度，选套餐时的决策基准 -->
				<view class="account-card">
					<view class="account-head">
						<view class="chip" :class="stateClass">
							<text class="chip-text">当前：{{ tierName }}</text>
						</view>
						<text class="account-validity">{{ accountValidityText }}</text>
					</view>
					<view class="account-quota">
						<view v-for="cell in accountQuotaCells" :key="cell.key" class="quota-cell">
							<view class="quota-cell-head">
								<app-icon :name="cell.icon" :size="24"></app-icon>
								<text class="quota-cell-label">{{ cell.label }}</text>
							</view>
							<view class="quota-nums">
								<text class="quota-remain" :class="{ 'quota-remain--empty': cell.exhausted }">{{ cell.remaining }}</text>
								<text class="quota-total">/ {{ cell.limit }} 次</text>
							</view>
							<text v-if="cell.exhausted" class="quota-exhausted">今日已用尽</text>
							<text v-else class="quota-hint">今日剩余</text>
						</view>
					</view>
				</view>
				<view v-if="plans.length" class="plan-list">
					<view
						v-for="plan in plans"
						:key="plan.planId"
						class="plan-card"
						:class="{ 'plan-card--active': selectedPlanId === plan.planId }"
						@click="selectPlan(plan)"
					>
						<text class="plan-name">{{ plan.name }}</text>
						<view class="plan-price-row">
							<text class="plan-price-symbol">¥</text>
							<text class="plan-price">{{ plan.price }}</text>
						</view>
						<text class="plan-days">{{ plan.days }} 天</text>
					</view>
				</view>
				<view v-else class="plan-empty">
					<text class="plan-empty-text">{{ planError ? '套餐加载失败，下拉重试' : '套餐加载中…' }}</text>
				</view>
				<!-- 选中套餐：用多久 / 折合单价（有效期按叠加语义预计算，仅展示用，入账以服务端为准） -->
				<view v-if="selectedPlanObj" class="plan-summary">
					<view class="plan-summary-row">
						<text class="plan-summary-label">有效期</text>
						<text class="plan-summary-value">支付后至 {{ validUntil }}（{{ selectedPlanObj.days }} 天）</text>
					</view>
					<view class="plan-summary-row">
						<text class="plan-summary-label">折合单价</text>
						<text class="plan-summary-value">≈ ¥{{ perDay }}/天</text>
					</view>
				</view>
				<!-- 充值后可享权益：免费版 vs 会员 对比（数值全部来自接口，不硬编码） -->
				<view v-if="benefitCompare.length" class="cmp">
					<view class="cmp-row cmp-row--head">
						<text class="cmp-cell cmp-cell--name">权益</text>
						<text class="cmp-cell">免费版</text>
						<text class="cmp-cell cmp-cell--member">会员</text>
					</view>
					<view v-for="row in benefitCompare" :key="row.key" class="cmp-row">
						<view class="cmp-cell cmp-cell--name">
							<app-icon :name="row.icon" :size="26"></app-icon>
							<text class="cmp-name">{{ row.label }}</text>
						</view>
						<text class="cmp-cell cmp-cell--free">{{ row.freeText }}</text>
						<text class="cmp-cell cmp-cell--member">{{ row.memberText }}</text>
					</view>
				</view>
				<view v-if="plans.length" class="pay-method">
					<app-icon name="receipt" :size="32"></app-icon>
					<text class="pay-method-name">模拟支付</text>
					<view class="chip is-muted">
						<text class="chip-text">演示环境 · 无真实资金</text>
					</view>
				</view>
				<button
					v-if="plans.length"
					class="redeem-btn"
					:loading="buying"
					:disabled="buying || !selectedPlanId"
					@click="handleBuy"
				>
					{{ isMember ? '立即续费' : '立即开通' }}
				</button>
				<!-- 使用规则：生效时间 / 使用范围 / 限制条件，简洁分条 -->
				<view v-if="plans.length" class="rules">
					<text class="rules-title">使用规则</text>
					<text class="rules-line">· 生效时间：支付成功立即生效；未到期续费在现有到期时间上叠加，剩余天数不清零</text>
					<text class="rules-line">· 使用范围：AI 对话、账单分析、AI 智能记账的每日额度与并发数，每日零点重置</text>
					<text class="rules-line">· 限制条件：大额或异常交易订单支付成功后需人工审核，管理员通过后自动到账</text>
					<text class="rules-line">· 演示环境：模拟支付，不产生真实资金扣款</text>
				</view>
			</view>

			<!-- ── 兑换会员码：开通 / 续费 ── -->
			<view class="section">
				<view class="section-head">
					<text class="section-title">兑换会员码</text>
				</view>
				<view class="redeem-field">
					<app-icon name="gift" :size="32"></app-icon>
					<input
						v-model="code"
						class="redeem-input"
						placeholder="粘贴或输入 16 位兑换码"
						placeholder-class="redeem-placeholder"
						:maxlength="32"
						:disabled="redeeming"
						confirm-type="done"
						@confirm="handleRedeem"
					/>
				</view>
				<button
					class="redeem-btn"
					:loading="redeeming"
					:disabled="redeeming"
					@click="handleRedeem"
				>
					{{ isMember ? '立即续费' : '立即开通' }}
				</button>
				<text class="redeem-note">
					{{ isMember ? '续费天数自动叠加，会员未到期时兑换不损失剩余天数' : '兑换码由管理员发放，开通立即生效，有效期按码内天数累计' }}
				</text>
			</view>
		</view>

		<!-- ── 模拟收银台（演示环境）：走与真实回调完全一致的服务端处理路径 ── -->
		<view v-if="cashier.visible" class="cashier-mask" @touchmove.stop.prevent>
			<view class="cashier-sheet" @click.stop>
				<view class="cashier-head">
					<text class="cashier-title">模拟收银台</text>
					<view class="chip is-muted">
						<text class="chip-text">演示环境</text>
					</view>
				</view>
				<view class="cashier-amount-row">
					<text class="cashier-amount-symbol">¥</text>
					<text class="cashier-amount">{{ cashier.order ? cashier.order.amount : '' }}</text>
				</view>
				<text class="cashier-plan">
					{{ cashier.order ? `${cashier.order.planName} · ${cashier.order.days} 天会员` : '' }}
				</text>
				<text class="cashier-until">开通后有效期至 {{ cashierValidUntil }}</text>
				<text class="cashier-order-no">订单号 {{ cashier.order ? cashier.order.orderNo : '' }}</text>
				<view class="cashier-actions">
					<button class="cashier-btn cashier-btn--ghost" :disabled="cashier.submitting" @click="handleCashierCancel">
						取消
					</button>
					<button
						class="cashier-btn cashier-btn--primary"
						:loading="cashier.submitting"
						:disabled="cashier.submitting"
						@click="handleCashierPay"
					>
						确认支付
					</button>
				</view>
			</view>
		</view>
	</view>
</template>

<script>
import AppIcon from '../../components/AppIcon.vue'
import EmptyState from '../../components/EmptyState.vue'
import { getMembershipStatus, redeemMembership } from '../../api/membership'
import {
	cancelRechargeOrder,
	createRechargeOrder,
	getRechargePlans,
	listMyRechargeOrders,
	mockPayOrder,
} from '../../api/recharge'

/** 剩余不超过该天数时状态徽章转为「即将到期」提醒 */
const EXPIRING_SOON_DAYS = 7

/** 兑换码前端归一化（与服务端一致）：去空格/连字符、转大写，粘贴友好 */
const normalizeCode = (raw) => (raw || '').replace(/[\s-]/g, '').toUpperCase()

const USAGE_ROWS = [
	{ key: 'chat', icon: 'chat', label: 'AI 对话' },
	{ key: 'analyze', icon: 'chart', label: '账单分析' },
	{ key: 'bookkeeping', icon: 'edit', label: 'AI 记账' },
]

/** 权益明细行：render 只做格式化，数值全部来自接口 benefits，不硬编码档位额度 */
const BENEFIT_ROWS = [
	{ key: 'dailyChat', icon: 'chat', label: 'AI 对话', render: (v) => `${v} 次 / 日` },
	{ key: 'dailyAnalyze', icon: 'chart', label: '账单智能分析', render: (v) => `${v} 次 / 日` },
	{ key: 'dailyBookkeeping', icon: 'edit', label: 'AI 智能记账', render: (v) => `${v} 次 / 日` },
	{ key: 'concurrency', icon: 'bolt', label: '并发请求', render: (v) => `${v} 路` },
	{ key: 'premiumModel', icon: 'bot', label: '高级 AI 模型' },
]

/** 充值前权益对比行（免费版 vs 会员）：数值来自 GET /recharge/plans 的 benefits 矩阵 */
const COMPARE_ROWS = [
	{ key: 'dailyChat', icon: 'chat', label: 'AI 对话', fmt: (v) => `${v} 次/日` },
	{ key: 'dailyAnalyze', icon: 'chart', label: '账单分析', fmt: (v) => `${v} 次/日` },
	{ key: 'dailyBookkeeping', icon: 'edit', label: 'AI 记账', fmt: (v) => `${v} 次/日` },
	{ key: 'concurrency', icon: 'bolt', label: '并发请求', fmt: (v) => `${v} 路` },
	{ key: 'premiumModel', icon: 'bot', label: '高级 AI 模型' },
]

const startOfDay = (date) => {
	const d = new Date(date)
	d.setHours(0, 0, 0, 0)
	return d
}

export default {
	components: { AppIcon, EmptyState },
	data() {
		return {
			status: null,
			loading: true,
			error: '',
			code: '',
			redeeming: false,
			// ── 套餐直购 ──
			plans: [],
			benefits: null,
			planError: false,
			selectedPlanId: '',
			buying: false,
			// ── 模拟收银台 ──
			cashier: { visible: false, order: null, submitting: false },
		}
	},
	computed: {
		/** 后端 tier=1 必带 expiresAt；万一天段数据缺失，按免费展示，避免 Invalid Date */
		isMember() {
			return !!this.status && this.status.tier === 1 && !!this.status.expiresAt
		},
		tierName() {
			return this.status?.tierName || '免费版'
		},
		daysLeft() {
			if (!this.status?.expiresAt) return null
			const exp = new Date(String(this.status.expiresAt).replace('T', ' '))
			if (isNaN(exp.getTime())) return null
			return Math.round((startOfDay(exp) - startOfDay(new Date())) / 86400000)
		},
		expiringSoon() {
			return this.isMember && this.daysLeft !== null && this.daysLeft >= 0 && this.daysLeft <= EXPIRING_SOON_DAYS
		},
		expired() {
			return this.isMember && this.daysLeft !== null && this.daysLeft < 0
		},
		stateLabel() {
			if (!this.isMember) return '未开通'
			if (this.expired) return '已到期'
			if (this.expiringSoon) return '即将到期'
			return '生效中'
		},
		stateClass() {
			if (!this.isMember) return 'is-muted'
			if (this.expired || this.expiringSoon) return 'is-danger'
			return 'is-amber'
		},
		validityText() {
			if (!this.isMember) return '兑换会员码，解锁更高 AI 额度与高级模型'
			const date = String(this.status.expiresAt).slice(0, 10)
			if (this.expired) return `已于 ${date} 到期，兑换续费码即可恢复会员权益`
			if (this.daysLeft === 0) return `${date} 到期 · 剩余不足 1 天`
			return `${date} 到期 · 剩余 ${this.daysLeft} 天`
		},
		usageRows() {
			return USAGE_ROWS.map((row) => {
				const item = this.status?.usage?.[row.key] ?? {}
				const used = Number(item.used ?? 0)
				const limit = Number(item.limit ?? 0)
				const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0
				return { ...row, used, limit, pct, exhausted: limit > 0 && used >= limit }
			})
		},
		benefitRows() {
			const benefits = this.status?.benefits
			if (!benefits) return []
			return BENEFIT_ROWS.filter((row) => Object.prototype.hasOwnProperty.call(benefits, row.key)).map((row) => ({
				...row,
				text: row.render ? row.render(benefits[row.key]) : '',
				enabled: row.key === 'premiumModel' ? !!benefits[row.key] : null,
			}))
		},
		// ── 充值决策信息：花多少钱（卡片）/ 用多久（有效期+单价）/ 享什么（对比表）──
		selectedPlanObj() {
			return this.plans.find((p) => p.planId === this.selectedPlanId) || null
		},
		/** 按叠加语义预览：base = max(现在, 现有到期时间)，与后端入账口径一致（展示用） */
		validUntil() {
			return this.computeValidUntil(this.selectedPlanObj?.days)
		},
		cashierValidUntil() {
			return this.computeValidUntil(this.cashier.order?.days)
		},
		perDay() {
			const plan = this.selectedPlanObj
			if (!plan || !plan.days) return ''
			// 仅展示格式化，价格权威值仍是服务端字符串
			return (parseFloat(plan.price) / plan.days).toFixed(2)
		},
		benefitCompare() {
			const b = this.benefits
			if (!b || !b.free || !b.member) return []
			return COMPARE_ROWS.map((row) => {
				if (row.key === 'premiumModel') {
					return {
						...row,
						freeText: b.free.premiumModel ? '已启用' : '—',
						memberText: b.member.premiumModel ? '已启用' : '—',
					}
				}
				return {
					...row,
					freeText: row.fmt(b.free[row.key]),
					memberText: row.fmt(b.member[row.key]),
				}
			})
		},
		// ── 当前账号卡：直接回答"我现在什么档位、今天还能用几次" ──
		accountQuotaCells() {
			const usage = this.status?.usage
			if (!usage) return []
			return USAGE_ROWS.map((row) => {
				const item = usage[row.key] ?? {}
				const used = Number(item.used ?? 0)
				const limit = Number(item.limit ?? 0)
				return {
					key: row.key,
					icon: row.icon,
					label: row.label,
					limit,
					remaining: Math.max(0, limit - used),
					exhausted: limit > 0 && used >= limit,
				}
			})
		},
		accountValidityText() {
			if (!this.isMember) return '未开通会员'
			if (this.expired) return '已到期'
			if (this.daysLeft === null) return this.stateLabel
			return `剩余 ${this.daysLeft} 天`
		},
	},
	onLoad() {
		this.fetchStatus()
		this.fetchPlans()
	},
	methods: {
		/** 有效期预览：base = max(现在, 现有到期时间 且 tier==1) + days，与后端 UPSERT 同口径 */
		computeValidUntil(days) {
			if (!days) return ''
			let base = new Date()
			if (this.isMember && this.status?.expiresAt) {
				const exp = new Date(String(this.status.expiresAt).replace('T', ' '))
				if (!isNaN(exp.getTime()) && exp > base) base = exp
			}
			const until = new Date(base.getTime() + days * 86400000)
			const y = until.getFullYear()
			const m = String(until.getMonth() + 1).padStart(2, '0')
			const d = String(until.getDate()).padStart(2, '0')
			return `${y}-${m}-${d}`
		},

		async fetchStatus() {
			this.loading = true
			this.error = ''
			try {
				const res = await getMembershipStatus()
				if (res?.code === 200 && res.data) {
					this.status = res.data
				} else {
					this.error = res?.message || '会员服务返回为空'
				}
			} catch (e) {
				this.error = e?.message || '请求失败，请检查网络后重试'
			} finally {
				this.loading = false
			}
		},

		// ── 套餐直购：价格全部来自接口（服务端唯一定价源），前端不硬编码 ──
		async fetchPlans() {
			this.planError = false
			try {
				const res = await getRechargePlans()
				if (res?.code === 200 && Array.isArray(res.data?.plans)) {
					this.plans = res.data.plans
					this.benefits = res.data.benefits || null
					if (!this.selectedPlanId && this.plans.length) {
						this.selectedPlanId = this.plans[0].planId
					}
				} else {
					this.planError = true
				}
			} catch (e) {
				this.planError = true
			}
		},

		selectPlan(plan) {
			if (!this.buying && !this.cashier.visible) this.selectedPlanId = plan.planId
		},

		goRecords() {
			uni.navigateTo({ url: '/pages/recharge/index' })
		},

		async handleBuy() {
			if (!this.selectedPlanId) {
				uni.showToast({ title: '请先选择套餐', icon: 'none' })
				return
			}
			if (this.buying) return
			this.buying = true
			try {
				const res = await createRechargeOrder(this.selectedPlanId)
				if (res?.code === 200 && res.data) {
					this.openCashier(res.data)
				} else if (res?.message && res.message.includes('待支付')) {
					// 已有进行中订单（幂等上限）：找到它继续支付，而不是让用户干等 15 分钟超时
					const pending = await this.findPendingOrder()
					if (pending) {
						this.openCashier(pending)
					} else {
						uni.showToast({ title: res.message, icon: 'none' })
					}
				} else {
					uni.showToast({ title: res?.message || '下单失败，请稍后重试', icon: 'none' })
				}
			} catch (e) {
				// 网络层失败 request.js 已 toast，这里兜底业务提示
				if (!e?.errMsg) {
					uni.showToast({ title: e?.message || '下单失败，请稍后重试', icon: 'none' })
				}
			} finally {
				this.buying = false
			}
		},

		async findPendingOrder() {
			try {
				const res = await listMyRechargeOrders({ page: 1, size: 20 })
				const records = res?.code === 200 ? res.data?.records || [] : []
				return records.find((r) => r.status === 0) || null
			} catch (e) {
				return null
			}
		},

		openCashier(order) {
			this.cashier = { visible: true, order, submitting: false }
		},

		async handleCashierPay() {
			if (this.cashier.submitting || !this.cashier.order) return
			this.cashier.submitting = true
			try {
				const res = await mockPayOrder(this.cashier.order.orderNo, 'success')
				if (res?.code === 200) {
					this.cashier.visible = false
					// 服务端文案区分两种成功：直接到账 / 进入人工审核
					uni.showToast({ title: res.message || '支付成功', icon: 'none' })
					this.fetchStatus()
				} else {
					uni.showToast({ title: res?.message || '支付失败，请稍后重试', icon: 'none' })
					// 超时关闭等终态：收银台没有继续支付的意义，直接收起
					const msg = res?.message || ''
					if (msg.includes('超时') || msg.includes('已处理') || msg.includes('已关闭')) {
						this.cashier.visible = false
					}
				}
			} catch (e) {
				if (!e?.errMsg) {
					uni.showToast({ title: e?.message || '支付失败，请稍后重试', icon: 'none' })
				}
			} finally {
				this.cashier.submitting = false
			}
		},

		async handleCashierCancel() {
			const orderNo = this.cashier.order ? this.cashier.order.orderNo : ''
			this.cashier.visible = false
			if (!orderNo) return
			try {
				// 取消即释放「进行中订单」名额（服务端写 CANCEL 审计），失败不阻断交互
				await cancelRechargeOrder(orderNo)
			} catch (e) {
				/* 静默：订单可能已被超时懒关闭 */
			}
		},

		async handleRedeem() {
			const normalized = normalizeCode(this.code)
			if (!normalized) {
				uni.showToast({ title: '请输入兑换码', icon: 'none' })
				return
			}
			if (this.redeeming) return
			this.redeeming = true
			try {
				const res = await redeemMembership(normalized)
				if (res?.code === 200) {
					uni.showToast({ title: res.message || '兑换成功', icon: 'none' })
					this.code = ''
					this.fetchStatus()
				} else {
					uni.showToast({ title: res?.message || '兑换失败，请稍后重试', icon: 'none' })
				}
			} catch (e) {
				// 网络层失败 request.js 已 toast，这里兜底业务提示
				if (!e?.errMsg) {
					uni.showToast({ title: e?.message || '兑换失败，请稍后重试', icon: 'none' })
				}
			} finally {
				this.redeeming = false
			}
		},
	},
}
</script>

<style scoped>
.container {
	min-height: 100vh;
	background-color: var(--color-bg);
}

.scroll-content {
	padding: var(--space-lg) var(--space-xl) var(--space-4xl);
	box-sizing: border-box;
}

/* ── 骨架 ── */
.skl {
	background-color: var(--color-surface-raised);
	border-radius: var(--radius-md);
	animation: sklPulse 1.6s ease-in-out infinite;
}

@keyframes sklPulse {
	0%,
	100% {
		opacity: 1;
	}
	50% {
		opacity: 0.55;
	}
}

.skl-chip {
	width: 88rpx;
	height: 88rpx;
	border-radius: var(--radius-lg);
	flex-shrink: 0;
}

.skl-line {
	height: 28rpx;
}

.skl-track {
	height: 12rpx;
	border-radius: var(--radius-full);
	margin-top: var(--space-md);
}

.skl-usage {
	margin-top: var(--space-xl);
}

.skl-field {
	height: 96rpx;
	border-radius: var(--radius-lg);
	margin-bottom: var(--space-lg);
}

.skl-btn {
	height: 96rpx;
	border-radius: var(--radius-full);
}

/* ── 档位区：报告封面的抬头行 ── */
.tier-head {
	display: flex;
	align-items: center;
	gap: var(--space-xl);
	padding: var(--space-lg) 0 var(--space-2xl);
	border-bottom: var(--hairline) solid var(--color-border);
}

.tier-chip {
	width: 88rpx;
	height: 88rpx;
	border-radius: var(--radius-lg);
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
}

.tier-chip--member {
	background-color: var(--color-accent-light);
}

.tier-chip--free {
	background-color: var(--color-surface-raised);
}

.tier-main {
	flex: 1;
	min-width: 0;
}

.tier-row {
	display: flex;
	align-items: center;
	gap: var(--space-md);
	margin-bottom: var(--space-xs);
}

.tier-name {
	font-size: var(--font-3xl);
	font-weight: var(--weight-extrabold);
	color: var(--color-text-heading);
	line-height: var(--leading-tight);
}

.tier-validity {
	display: block;
	font-family: var(--font-numeric-mixed);
	font-variant-numeric: tabular-nums;
	font-size: var(--font-md);
	color: var(--color-text-secondary);
}

.tier-validity--alarm {
	color: var(--color-danger);
}

/* ── 状态徽章（mom-chip 同语言） ── */
.chip {
	display: inline-flex;
	align-items: center;
	padding: var(--space-2xs) var(--space-md);
	border-radius: var(--radius-full);
	flex-shrink: 0;
}

.chip-text {
	font-size: var(--font-xs);
	font-weight: var(--weight-semibold);
	line-height: 1.4;
}

.chip.is-amber {
	background-color: var(--color-accent-light);
}

.chip.is-amber .chip-text {
	color: var(--color-accent-deep);
}

.chip.is-danger {
	background-color: var(--color-danger-light);
}

.chip.is-danger .chip-text {
	color: var(--color-danger);
}

.chip.is-muted {
	background-color: var(--color-surface-raised);
}

.chip.is-muted .chip-text {
	color: var(--color-text-tertiary);
}

.chip.is-ink {
	background-color: var(--color-surface-raised);
}

.chip.is-ink .chip-text {
	color: var(--color-text);
}

/* ── 区块：发丝线与留白分区，无卡片盒 ── */
.section {
	margin-top: 96rpx;
}

.section-head {
	display: flex;
	justify-content: space-between;
	align-items: baseline;
	gap: var(--space-md);
	margin-bottom: var(--space-lg);
}

.section-title {
	font-size: var(--font-base);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	letter-spacing: var(--tracking-heading);
}

.section-sub {
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
	font-variant-numeric: tabular-nums;
}

/* ── 今日用量行 ── */
.usage-list {
	display: flex;
	flex-direction: column;
	gap: var(--space-xl);
}

.usage-line {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--space-md);
	margin-bottom: var(--space-sm);
}

.usage-left {
	display: flex;
	align-items: center;
	gap: var(--space-md);
	min-width: 0;
	flex: 1;
}

.usage-name {
	font-size: var(--font-sm);
	color: var(--color-text);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.usage-nums {
	font-family: var(--font-amount);
	font-variant-numeric: tabular-nums;
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
	color: var(--color-text);
	letter-spacing: var(--tracking-amount);
	flex-shrink: 0;
}

.usage-limit {
	font-size: var(--font-sm);
	font-weight: var(--weight-normal);
	color: var(--color-text-tertiary);
}

.usage-track {
	height: 12rpx;
	border-radius: var(--radius-full);
	background: var(--color-surface-raised);
	overflow: hidden;
}

.usage-fill {
	height: 100%;
	border-radius: var(--radius-full);
	background: var(--color-primary);
	animation: usageGrowX 0.7s var(--ease-out-expo) backwards;
}

.usage-fill--danger {
	background: var(--color-danger);
}

@keyframes usageGrowX {
	from {
		transform: scaleX(0);
		transform-origin: left;
	}
	to {
		transform: scaleX(1);
		transform-origin: left;
	}
}

/* ── 我的权益行 ── */
.benefit-list {
	display: flex;
	flex-direction: column;
}

.benefit-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--space-md);
	padding: var(--space-lg) 0;
	border-bottom: var(--hairline) solid var(--color-divider);
}

.benefit-row:last-child {
	border-bottom: none;
}

.benefit-row:first-child {
	padding-top: 0;
}

.benefit-left {
	display: flex;
	align-items: center;
	gap: var(--space-md);
	min-width: 0;
	flex: 1;
}

.benefit-name {
	font-size: var(--font-base);
	color: var(--color-text);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.benefit-value {
	font-family: var(--font-amount);
	font-variant-numeric: tabular-nums;
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
	color: var(--color-text);
	letter-spacing: var(--tracking-amount);
	flex-shrink: 0;
}

/* ── 兑换区 ── */
.redeem-field {
	display: flex;
	align-items: center;
	gap: var(--space-md);
	height: 96rpx;
	border-radius: var(--radius-lg);
	background-color: var(--color-surface-raised);
	padding: 0 var(--space-xl);
}

.redeem-input {
	flex: 1;
	height: 100%;
	font-size: var(--font-base);
	color: var(--color-text);
	font-family: var(--font-amount);
	letter-spacing: var(--tracking-amount);
}

.redeem-placeholder {
	color: var(--color-text-tertiary);
	font-family: var(--font-body);
	letter-spacing: var(--tracking-body);
}

.redeem-btn {
	margin-top: var(--space-lg);
	height: 96rpx;
	border-radius: var(--radius-full);
	background-color: var(--color-primary);
	color: var(--color-text-inverse);
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
	display: flex;
	align-items: center;
	justify-content: center;
	border: none;
	line-height: 1;
}

.redeem-btn::after {
	border: none;
}

.redeem-btn[disabled] {
	opacity: 0.4;
	color: var(--color-text-inverse);
	background-color: var(--color-primary);
}

.redeem-note {
	display: block;
	margin-top: var(--space-md);
	font-size: var(--font-xs);
	line-height: var(--leading-relaxed);
	color: var(--color-text-tertiary);
}

/* ── 套餐直购区 ── */
.section-link {
	display: inline-flex;
	align-items: center;
	gap: var(--space-2xs);
}

.section-link-text {
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
}

.plan-list {
	display: flex;
	gap: var(--space-md);
}

.plan-card {
	flex: 1;
	min-width: 0;
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: var(--space-2xs);
	padding: var(--space-xl) var(--space-sm);
	border-radius: var(--radius-lg);
	background-color: var(--color-surface-raised);
	border: 3rpx solid transparent;
	transition: border-color 0.2s ease, transform 0.2s var(--ease-out-expo);
}

.plan-card--active {
	border-color: var(--color-accent);
	transform: translateY(-4rpx);
}

.plan-name {
	font-size: var(--font-sm);
	font-weight: var(--weight-semibold);
	color: var(--color-text);
}

.plan-price-row {
	display: flex;
	align-items: baseline;
	gap: 2rpx;
}

.plan-price-symbol {
	font-size: var(--font-sm);
	font-weight: var(--weight-semibold);
	color: var(--color-text-heading);
}

.plan-price {
	font-family: var(--font-amount);
	font-variant-numeric: tabular-nums;
	font-size: var(--font-2xl);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	letter-spacing: var(--tracking-amount);
}

.plan-days {
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
}

.plan-empty {
	display: flex;
	align-items: center;
	justify-content: center;
	height: 120rpx;
	border-radius: var(--radius-lg);
	background-color: var(--color-surface-raised);
}

.plan-empty-text {
	font-size: var(--font-sm);
	color: var(--color-text-tertiary);
}

/* ── 选中套餐摘要：用多久 / 折合单价 ── */
.plan-summary {
	margin-top: var(--space-lg);
	padding: var(--space-lg) var(--space-xl);
	border-radius: var(--radius-lg);
	background-color: var(--color-surface-raised);
	display: flex;
	flex-direction: column;
	gap: var(--space-sm);
}

.plan-summary-row {
	display: flex;
	align-items: baseline;
	justify-content: space-between;
	gap: var(--space-md);
}

.plan-summary-label {
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
	flex-shrink: 0;
}

.plan-summary-value {
	font-size: var(--font-xs);
	font-weight: var(--weight-semibold);
	color: var(--color-text);
	font-variant-numeric: tabular-nums;
	text-align: right;
}

/* ── 权益对比表：免费版 vs 会员 ── */
.cmp {
	margin-top: var(--space-xl);
	border: var(--hairline) solid var(--color-border);
	border-radius: var(--radius-lg);
	overflow: hidden;
}

.cmp-row {
	display: flex;
	align-items: center;
	padding: var(--space-md) var(--space-lg);
	border-bottom: var(--hairline) solid var(--color-divider);
}

.cmp-row:last-child {
	border-bottom: none;
}

.cmp-row--head {
	background-color: var(--color-surface-raised);
}

.cmp-cell {
	flex: 1;
	text-align: center;
	font-size: var(--font-xs);
	color: var(--color-text);
	font-variant-numeric: tabular-nums;
}

.cmp-cell--name {
	flex: 1.6;
	display: flex;
	align-items: center;
	gap: var(--space-sm);
	justify-content: flex-start;
	text-align: left;
}

.cmp-name {
	font-size: var(--font-xs);
	color: var(--color-text);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.cmp-cell--free {
	color: var(--color-text-tertiary);
}

.cmp-cell--member {
	color: var(--color-accent-deep);
	font-weight: var(--weight-semibold);
}

.cmp-row--head .cmp-cell {
	color: var(--color-text-tertiary);
	font-weight: var(--weight-normal);
}

.cmp-row--head .cmp-cell--member {
	color: var(--color-accent-deep);
	font-weight: var(--weight-semibold);
}

/* ── 使用规则 ── */
.rules {
	margin-top: var(--space-lg);
}

.rules-title {
	display: block;
	font-size: var(--font-xs);
	font-weight: var(--weight-semibold);
	color: var(--color-text-secondary);
	margin-bottom: var(--space-2xs);
}

.rules-line {
	display: block;
	font-size: var(--font-xs);
	line-height: var(--leading-relaxed);
	color: var(--color-text-tertiary);
}

/* ── 当前账号状态卡 ── */
.account-card {
	margin-bottom: var(--space-lg);
	padding: var(--space-lg) var(--space-xl);
	border-radius: var(--radius-lg);
	background-color: var(--color-surface-raised);
}

.account-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--space-md);
	margin-bottom: var(--space-lg);
}

.account-validity {
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
	font-variant-numeric: tabular-nums;
}

.account-quota {
	display: flex;
	gap: var(--space-md);
}

.quota-cell {
	flex: 1;
	min-width: 0;
	padding: var(--space-md);
	border-radius: var(--radius-md);
	background-color: var(--color-surface);
	display: flex;
	flex-direction: column;
	gap: var(--space-2xs);
}

.quota-cell-head {
	display: flex;
	align-items: center;
	gap: var(--space-2xs);
	min-width: 0;
}

.quota-cell-label {
	font-size: var(--font-xs);
	color: var(--color-text-secondary);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.quota-nums {
	display: flex;
	align-items: baseline;
	gap: 2rpx;
}

.quota-remain {
	font-family: var(--font-amount);
	font-variant-numeric: tabular-nums;
	font-size: var(--font-xl);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
	letter-spacing: var(--tracking-amount);
}

.quota-remain--empty {
	color: var(--color-danger);
}

.quota-total {
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
}

.quota-hint {
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
}

.quota-exhausted {
	font-size: var(--font-xs);
	color: var(--color-danger);
}

.pay-method {
	display: flex;
	align-items: center;
	gap: var(--space-md);
	margin-top: var(--space-xl);
	padding: var(--space-lg) var(--space-xl);
	border-radius: var(--radius-lg);
	background-color: var(--color-surface-raised);
}

.pay-method-name {
	flex: 1;
	font-size: var(--font-base);
	color: var(--color-text);
}

/* ── 模拟收银台弹层 ── */
.cashier-mask {
	position: fixed;
	inset: 0;
	z-index: 999;
	display: flex;
	align-items: center;
	justify-content: center;
	padding: var(--space-3xl);
	background-color: rgba(0, 0, 0, 0.45);
}

.cashier-sheet {
	width: 100%;
	max-width: 560rpx;
	border-radius: var(--radius-xl);
	background-color: var(--color-surface);
	padding: var(--space-2xl);
	box-sizing: border-box;
}

.cashier-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: var(--space-xl);
}

.cashier-title {
	font-size: var(--font-lg);
	font-weight: var(--weight-bold);
	color: var(--color-text-heading);
}

.cashier-amount-row {
	display: flex;
	align-items: baseline;
	gap: var(--space-2xs);
	justify-content: center;
	margin-top: var(--space-lg);
}

.cashier-amount-symbol {
	font-size: var(--font-xl);
	font-weight: var(--weight-semibold);
	color: var(--color-text-heading);
}

.cashier-amount {
	font-family: var(--font-amount);
	font-variant-numeric: tabular-nums;
	font-size: 72rpx;
	font-weight: var(--weight-extrabold);
	color: var(--color-text-heading);
	letter-spacing: var(--tracking-amount);
}

.cashier-plan {
	display: block;
	text-align: center;
	margin-top: var(--space-sm);
	font-size: var(--font-sm);
	color: var(--color-text);
}

.cashier-until {
	display: block;
	text-align: center;
	margin-top: var(--space-2xs);
	font-size: var(--font-xs);
	font-weight: var(--weight-semibold);
	color: var(--color-accent-deep);
}

.cashier-order-no {
	display: block;
	text-align: center;
	margin-top: var(--space-2xs);
	font-size: var(--font-xs);
	color: var(--color-text-tertiary);
	word-break: break-all;
}

.cashier-actions {
	display: flex;
	gap: var(--space-lg);
	margin-top: var(--space-2xl);
}

.cashier-btn {
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

.cashier-btn::after {
	border: none;
}

.cashier-btn--ghost {
	background-color: var(--color-surface-raised);
	color: var(--color-text);
}

.cashier-btn--primary {
	background-color: var(--color-primary);
	color: var(--color-text-inverse);
}

.cashier-btn--primary[disabled] {
	opacity: 0.4;
	color: var(--color-text-inverse);
	background-color: var(--color-primary);
}

/* ── 错误态重试 ── */
.retry-btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	height: 88rpx;
	padding: 0 var(--space-3xl);
	border-radius: var(--radius-full);
	background-color: var(--color-primary);
}

.retry-text {
	font-size: var(--font-base);
	font-weight: var(--weight-semibold);
	color: var(--color-text-inverse);
}
</style>
