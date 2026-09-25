// 视觉验收用 mock 服务：模拟 fast_backend 的 /api 接口。
// 所有数据为合成的演示数据，仅用于截图验收，不代表真实用户数据。
import http from 'node:http'

const PORT = 8000

// ── 分类（id 决定功能色板取色，与 utils/category.js 一致） ──
const CATEGORIES = [
	{ id: 1, name: '餐饮', type: 0 },
	{ id: 2, name: '交通', type: 0 },
	{ id: 3, name: '购物', type: 0 },
	{ id: 4, name: '娱乐', type: 0 },
	{ id: 5, name: '医疗', type: 0 },
	{ id: 6, name: '教育', type: 0 },
	{ id: 7, name: '住房', type: 0 },
	{ id: 8, name: '通讯', type: 0 },
	{ id: 9, name: '服饰', type: 0 },
	{ id: 10, name: '运动', type: 0 },
	{ id: 11, name: '旅行', type: 0 },
	{ id: 12, name: '礼物', type: 0 },
	{ id: 13, name: '居家', type: 0 },
	{ id: 14, name: '宠物', type: 0 },
	{ id: 15, name: '工资', type: 1 },
	{ id: 16, name: '奖金', type: 1 },
	{ id: 17, name: '兼职', type: 1 },
	{ id: 18, name: '投资收益', type: 1 },
	{ id: 19, name: '其他收入', type: 1 },
]
const catName = (id) => CATEGORIES.find(c => c.id === id)?.name || '其他'
const catType = (id) => CATEGORIES.find(c => c.id === id)?.type ?? 0

// ── 月度汇总（六个月序列，用于趋势与环比） ──
const MONTHLY = {
	'2026-4': { income: 12000, expense: 4200 },
	'2026-5': { income: 12000, expense: 5350 },
	'2026-6': { income: 12500, expense: 4800 },
	'2026-7': { income: 12300, expense: 6100 },
	'2026-8': { income: 11800, expense: 4230 },
	'2026-9': { income: 12300, expense: 3879.5 },
	'2026-10': { income: 0, expense: 0 },
	'2026-12': { income: 0, expense: 0 },
}

// ── 分类占比（2026-09，与月度汇总口径一致） ──
const CATEGORY_STATS = {
	'0-2026-9': [
		{ categoryId: 1, categoryName: '餐饮', amount: 1287.5, percentage: 33.2 },
		{ categoryId: 3, categoryName: '购物', amount: 986.0, percentage: 25.4 },
		{ categoryId: 2, categoryName: '交通', amount: 425.0, percentage: 11.0 },
		{ categoryId: 4, categoryName: '娱乐', amount: 358.0, percentage: 9.2 },
		{ categoryId: 13, categoryName: '居家', amount: 320.0, percentage: 8.2 },
		{ categoryId: 6, categoryName: '教育', amount: 300.0, percentage: 7.7 },
		{ categoryId: 5, categoryName: '医疗', amount: 104.5, percentage: 2.7 },
		{ categoryId: 8, categoryName: '通讯', amount: 98.5, percentage: 2.5 },
	],
	'1-2026-9': [
		{ categoryId: 15, categoryName: '工资', amount: 11000.0, percentage: 89.4 },
		{ categoryId: 17, categoryName: '兼职', amount: 800.0, percentage: 6.5 },
		{ categoryId: 18, categoryName: '投资收益', amount: 500.0, percentage: 4.1 },
	],
}

// ── 账单流水（2026-09，覆盖多日期多分类） ──
let rid = 100
const mk = (date, cid, amount, remark) => ({
	id: ++rid,
	categoryId: cid,
	categoryName: catName(cid),
	categoryType: catType(cid),
	amount,
	remark: remark || '',
	recordDate: `${date}T${String(8 + (rid % 12)).padStart(2, '0')}:${String((rid * 7) % 60).padStart(2, '0')}:00`,
})
const RECORDS = [
	mk('2026-09-25', 1, 32.5, '午餐 · 沙县小吃'),
	mk('2026-09-25', 2, 8.0, '地铁'),
	mk('2026-09-25', 3, 199.0, '秋季外套'),
	mk('2026-09-24', 1, 45.0, '晚餐 · 麻辣香锅'),
	mk('2026-09-24', 4, 88.0, '电影票 ×2'),
	mk('2026-09-24', 15, 11000.0, '9月工资'),
	mk('2026-09-23', 1, 28.0, '早餐 + 咖啡'),
	mk('2026-09-23', 6, 300.0, '线上课程季费'),
	mk('2026-09-22', 2, 25.5, '打车回家'),
	mk('2026-09-22', 13, 320.0, '纸巾洗衣液等日百'),
	mk('2026-09-21', 1, 56.0, '火锅 · 周末聚餐'),
	mk('2026-09-21', 4, 120.0, '桌游吧'),
	mk('2026-09-20', 5, 104.5, '感冒药 + 挂号'),
	mk('2026-09-20', 1, 36.0, '外卖 · 黄焖鸡'),
	mk('2026-09-19', 3, 452.0, '球鞋'),
	mk('2026-09-19', 2, 12.0, '公交充值'),
	mk('2026-09-18', 1, 42.5, '日料定食'),
	mk('2026-09-18', 17, 800.0, '稿费 · 兼职'),
	mk('2026-09-17', 8, 98.5, '话费 + 流量包'),
	mk('2026-09-16', 1, 33.0, '午餐 · 食堂'),
	mk('2026-09-15', 4, 150.0, 'livehouse 门票'),
	mk('2026-09-14', 1, 51.0, '超市晚餐食材'),
	mk('2026-09-12', 3, 335.0, '购物 · 日用补给'),
	mk('2026-09-10', 1, 29.5, '午餐 · 面馆'),
	mk('2026-09-08', 18, 500.0, '基金收益'),
	mk('2026-09-05', 1, 66.0, '烤肉 · 朋友聚会'),
	mk('2026-09-03', 2, 156.0, '高铁票 · 短途'),
	mk('2026-09-01', 1, 24.0, '午餐 · 盖浇饭'),
]

const ok = (data) => JSON.stringify({ code: 200, message: 'ok', data })
const err = (message, code = 400) => JSON.stringify({ code, message, data: null })

const TOKEN = 'mock-token-for-review'

const server = http.createServer((req, res) => {
	const url = new URL(req.url, `http://127.0.0.1:${PORT}`)
	const path = url.pathname.replace(/^\/api/, '')
	const auth = req.headers.authorization || ''

	// 登录/注册不校验 token
	if (path === '/user/login' || path === '/user/register') {
		res.writeHead(200, { 'Content-Type': 'application/json' })
		res.end(ok({ token: TOKEN, user: { id: 1, username: '简小记', avatar: '' } }))
		return
	}

	if (auth !== `Bearer ${TOKEN}`) {
		res.writeHead(200, { 'Content-Type': 'application/json' })
		res.end(err('未登录或登录已过期', 401))
		return
	}

	res.writeHead(200, { 'Content-Type': 'application/json' })

	if (path === '/user/info') {
		res.end(ok({ id: 1, username: '简小记', avatar: '' }))
		return
	}

	if (path === '/statistics/monthly') {
		const year = url.searchParams.get('year')
		const month = url.searchParams.get('month')
		const m = MONTHLY[`${year}-${Number(month)}`] || { income: 0, expense: 0 }
		res.end(ok({ year: Number(year), month: Number(month), totalIncome: m.income, totalExpense: m.expense, balance: m.income - m.expense }))
		return
	}

	if (path === '/statistics/category') {
		const year = url.searchParams.get('year')
		const month = url.searchParams.get('month')
		const type = url.searchParams.get('type') || '0'
		res.end(ok(CATEGORY_STATS[`${type}-${year}-${Number(month)}`] || []))
		return
	}

	if (path === '/records') {
		const page = Number(url.searchParams.get('page') || 1)
		const size = Number(url.searchParams.get('size') || 20)
		const cid = url.searchParams.get('categoryId')
		const filtered = cid ? RECORDS.filter(r => String(r.categoryId) === String(cid)) : RECORDS
		const slice = filtered.slice((page - 1) * size, page * size)
		res.end(ok({
			records: slice,
			total: filtered.length,
			pages: Math.max(1, Math.ceil(filtered.length / size)),
			current: page,
			size,
		}))
		return
	}

	if (path === '/categories') {
		res.end(ok(CATEGORIES))
		return
	}

	// AI 相关：验收只覆盖空态页面，统一返回成功空实现
	if (path.startsWith('/ai/')) {
		res.end(ok({ id: 'mock-session' }))
		return
	}

	res.end(err('not found', 404))
})

server.listen(PORT, '127.0.0.1', () => {
	console.log(`[mock] listening on http://127.0.0.1:${PORT} (synthetic demo data)`)
})
