export const formatAmount = (amount) => {
	return Number(amount).toFixed(2)
}

export const formatDate = (dateStr) => {
	if (!dateStr) return ''
	return dateStr.replace('T', ' ')
}

export const getDayOfWeek = (dateStr) => {
	const days = ['日', '一', '二', '三', '四', '五', '六']
	const d = new Date(dateStr)
	return '周' + days[d.getDay()]
}
