import { View, Text, StyleSheet } from 'react-native'
import { theme } from '../config/theme'

const COLORS = [
  '#e94560', '#0984e3', '#00b894', '#6c5ce7',
  '#fdcb6e', '#e17055', '#00cec9', '#fab1a0',
  '#74b9ff', '#55efc4', '#a29bfe', '#ffeaa7',
]

export default function DonutChart({ data, title }) {
  if (!data || data.length === 0) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyText}>暂无数据</Text>
      </View>
    )
  }

  const total = data.reduce((sum, d) => sum + d.amount, 0)
  if (total === 0) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyText}>暂无数据</Text>
      </View>
    )
  }

  const segments = data.map((item, i) => ({
    ...item,
    pct: (item.amount / total) * 100,
    color: COLORS[i % COLORS.length],
  }))

  return (
    <View style={styles.container}>
      {title && <Text style={styles.title}>{title}</Text>}

      <View style={styles.barRow}>
        {segments.map((seg, i) => (
          <View
            key={i}
            style={[
              styles.barSeg,
              {
                flex: seg.amount,
                backgroundColor: seg.color,
              },
            ]}
          />
        ))}
      </View>

      <View style={styles.grid}>
        {segments.map((seg, i) => (
          <View key={i} style={styles.gridItem}>
            <View style={[styles.dot, { backgroundColor: seg.color }]} />
            <Text style={styles.gridName} numberOfLines={1}>{seg.name}</Text>
            <Text style={styles.gridAmount}>¥{seg.amount.toFixed(2)}</Text>
            <Text style={styles.gridPct}>{seg.pct.toFixed(1)}%</Text>
          </View>
        ))}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    ...theme.shadows.small,
  },
  title: {
    fontSize: 15,
    fontWeight: '700',
    color: theme.colors.primary,
    marginBottom: theme.spacing.md,
  },
  empty: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.xl,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 13,
    color: theme.colors.textLight,
  },
  barRow: {
    flexDirection: 'row',
    height: 14,
    borderRadius: 7,
    overflow: 'hidden',
    marginBottom: theme.spacing.md,
  },
  barSeg: {
    minWidth: 4,
  },
  grid: {},
  gridItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: theme.colors.borderLight,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  gridName: {
    flex: 1,
    fontSize: 13,
    color: theme.colors.text,
    fontWeight: '500',
  },
  gridAmount: {
    fontSize: 13,
    fontWeight: '600',
    color: theme.colors.text,
    marginRight: 8,
    minWidth: 72,
    textAlign: 'right',
  },
  gridPct: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    width: 45,
    textAlign: 'right',
  },
})
