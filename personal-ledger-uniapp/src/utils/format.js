export const formatAmount = (amount) => {
	const num = Number(amount) || 0
	const [int, dec] = Math.abs(num).toFixed(2).split('.')
	const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
	return (num < 0 ? '-' : '') + grouped + '.' + dec
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
