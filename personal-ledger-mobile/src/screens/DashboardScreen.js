import { useState, useCallback } from 'react'
import {
  View, Text, StyleSheet, ScrollView,
  RefreshControl,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import { useFocusEffect } from '@react-navigation/native'
import dayjs from 'dayjs'
import { getMonthlyStatistics, getCategoryStatistics } from '../api/statistics'
import { theme } from '../config/theme'
import StatCard from '../components/StatCard'
import DonutChart from '../components/DonutChart'
import SkeletonCard from '../components/SkeletonCard'
import EmptyState from '../components/EmptyState'
import FadeInView from '../components/FadeInView'
import ScaleButton from '../components/ScaleButton'

export default function DashboardScreen() {
  const now = dayjs()
  const [year, setYear] = useState(now.year())
  const [month, setMonth] = useState(now.month() + 1)
  const [monthlyData, setMonthlyData] = useState(null)
  const [expenseData, setExpenseData] = useState([])
  const [incomeData, setIncomeData] = useState([])
  const [loading, setLoading] = useState(false)

  const fetchData = useCallback(async (y, m) => {
    setLoading(true)
    try {
      const [monthlyRes, expenseRes, incomeRes] = await Promise.all([
        getMonthlyStatistics({ year: y, month: m }),
        getCategoryStatistics({ year: y, month: m, type: 0 }),
        getCategoryStatistics({ year: y, month: m, type: 1 }),
      ])
      if (monthlyRes.code === 200) setMonthlyData(monthlyRes.data)
      if (expenseRes.code === 200) setExpenseData(expenseRes.data)
      if (incomeRes.code === 200) setIncomeData(incomeRes.data)
    } catch (e) {
    } finally {
      setLoading(false)
    }
  }, [])

  useFocusEffect(
    useCallback(() => {
      fetchData(year, month)
    }, [year, month])
  )

  const prevMonth = () => {
    if (month === 1) {
      setYear(year - 1)
      setMonth(12)
    } else {
      setMonth(month - 1)
    }
  }

  const nextMonth = () => {
    if (month === 12) {
      setYear(year + 1)
      setMonth(1)
    } else {
      setMonth(month + 1)
    }
  }

  const currentMonthLabel = `${year}年${String(month).padStart(2, '0')}月`

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>数据概览</Text>
        <Text style={styles.headerSubtitle}>掌控您的财务状况</Text>
      </View>
      <FadeInView style={{ flex: 1 }}>
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.scrollContent}
          refreshControl={
            <RefreshControl refreshing={loading} onRefresh={() => fetchData(year, month)} />
          }
        >
          <View style={styles.monthSelector}>
            <ScaleButton onPress={prevMonth} style={styles.monthArrow}>
              <Ionicons name="chevron-back" size={20} color={theme.colors.textSecondary} />
            </ScaleButton>
            <View style={styles.monthBadge}>
              <Text style={styles.monthText}>{currentMonthLabel}</Text>
            </View>
            <ScaleButton onPress={nextMonth} style={styles.monthArrow}>
              <Ionicons name="chevron-forward" size={20} color={theme.colors.textSecondary} />
            </ScaleButton>
          </View>

          {loading && !monthlyData ? (
            <SkeletonCard lines={3} />
          ) : monthlyData ? (
            <>
              <View style={styles.statsRow}>
                <View style={styles.statFlex}>
                  <StatCard
                    label="收入"
                    value={`¥${monthlyData.totalIncome.toFixed(2)}`}
                    type="income"
                    icon="arrow-down"
                  />
                </View>
                <View style={styles.statFlex}>
                  <StatCard
                    label="支出"
                    value={`¥${monthlyData.totalExpense.toFixed(2)}`}
                    type="expense"
                    icon="arrow-up"
                  />
                </View>
                <View style={styles.statFlex}>
                  <StatCard
                    label="结余"
                    value={`¥${monthlyData.balance.toFixed(2)}`}
                    type="balance"
                    icon="wallet"
                  />
                </View>
              </View>

              {expenseData.length > 0 && (
                <View style={styles.chartCard}>
                  <View style={styles.chartHeader}>
                    <Ionicons name="pie-chart" size={18} color={theme.colors.error} />
                    <Text style={styles.chartTitle}>支出构成</Text>
                  </View>
                  <DonutChart data={expenseData} />
                </View>
              )}

              {incomeData.length > 0 && (
                <View style={styles.chartCard}>
                  <View style={styles.chartHeader}>
                    <Ionicons name="pie-chart" size={18} color={theme.colors.success} />
                    <Text style={styles.chartTitle}>收入构成</Text>
                  </View>
                  <DonutChart data={incomeData} />
                </View>
              )}

              {expenseData.length === 0 && incomeData.length === 0 && (
                <EmptyState
                  icon="bar-chart-outline"
                  title="暂无数据"
                  description="该月份暂无记账记录"
                />
              )}
            </>
          ) : (
            <EmptyState
              icon="bar-chart-outline"
              title="暂无数据"
              description="该月份暂无记账记录"
            />
          )}
        </ScrollView>
      </FadeInView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  header: {
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.md,
    backgroundColor: theme.colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.borderLight,
  },
  headerTitle: {
    ...theme.typography.h1,
    color: theme.colors.primary,
  },
  headerSubtitle: {
    ...theme.typography.caption,
    color: theme.colors.textSecondary,
    marginTop: 4,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: theme.spacing.md,
    paddingBottom: theme.spacing.xl,
  },
  monthSelector: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.lg,
  },
  monthArrow: {
    width: 40,
    height: 40,
    borderRadius: theme.borderRadius.full,
    backgroundColor: theme.colors.surface,
    justifyContent: 'center',
    alignItems: 'center',
    ...theme.shadows.small,
  },
  monthBadge: {
    backgroundColor: theme.colors.primary,
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.sm,
    borderRadius: theme.borderRadius.full,
    marginHorizontal: theme.spacing.md,
  },
  monthText: {
    fontSize: 16,
    fontWeight: '700',
    color: theme.colors.surface,
  },
  statsRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: theme.spacing.md,
  },
  statFlex: {
    flex: 1,
  },
  chartCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.md,
    ...theme.shadows.small,
  },
  chartHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: theme.spacing.md,
  },
  chartTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: theme.colors.primary,
  },
})
