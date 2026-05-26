import { useState, useEffect, useCallback } from 'react'
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, RefreshControl, Platform,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import dayjs from 'dayjs'
import { getMonthlyStatistics, getCategoryStatistics } from '../api/statistics'

export default function DashboardScreen() {
  const now = dayjs()
  const [year, setYear] = useState(now.year())
  const [month, setMonth] = useState(now.month() + 1)
  const [monthlyData, setMonthlyData] = useState(null)
  const [expenseData, setExpenseData] = useState([])
  const [incomeData, setIncomeData] = useState([])
  const [loading, setLoading] = useState(false)
  const [showMonthPicker, setShowMonthPicker] = useState(false)

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
      // silent
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData(year, month)
  }, [year, month, fetchData])

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

  const renderCategoryTable = (data, title, color) => (
    <View style={styles.tableCard}>
      <View style={[styles.tableHeader, { borderLeftColor: color }]}>
        <Text style={styles.tableTitle}>{title}</Text>
      </View>
      {data.length === 0 ? (
        <Text style={styles.emptyText}>暂无数据</Text>
      ) : (
        data.map((item) => (
          <View key={item.categoryId} style={styles.tableRow}>
            <Text style={styles.categoryName}>{item.categoryName}</Text>
            <View style={styles.barContainer}>
              <View
                style={[
                  styles.bar,
                  {
                    width: `${Math.min(item.percentage, 100)}%`,
                    backgroundColor: color,
                  },
                ]}
              />
            </View>
            <Text style={[styles.amount, { color }]}>
              ¥{item.amount.toFixed(2)}
            </Text>
            <Text style={styles.percentage}>{item.percentage}%</Text>
          </View>
        ))
      )}
    </View>
  )

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>数据概览</Text>
      </View>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={loading} onRefresh={() => fetchData(year, month)} />
        }
      >
        <View style={styles.monthSelector}>
          <TouchableOpacity onPress={prevMonth} style={styles.monthArrow}>
            <Ionicons name="chevron-back" size={22} color="#18181b" />
          </TouchableOpacity>
          <Text style={styles.monthText}>{currentMonthLabel}</Text>
          <TouchableOpacity onPress={nextMonth} style={styles.monthArrow}>
            <Ionicons name="chevron-forward" size={22} color="#18181b" />
          </TouchableOpacity>
        </View>

        {loading && !monthlyData ? (
          <ActivityIndicator size="large" color="#18181b" style={{ marginTop: 40 }} />
        ) : monthlyData ? (
          <>
            <View style={styles.statsRow}>
              <View style={[styles.statCard, { borderTopColor: '#3f8600' }]}>
                <Text style={styles.statLabel}>收入</Text>
                <Text style={[styles.statValue, { color: '#3f8600' }]}>
                  ¥{monthlyData.totalIncome.toFixed(2)}
                </Text>
              </View>
              <View style={[styles.statCard, { borderTopColor: '#cf1322' }]}>
                <Text style={styles.statLabel}>支出</Text>
                <Text style={[styles.statValue, { color: '#cf1322' }]}>
                  ¥{monthlyData.totalExpense.toFixed(2)}
                </Text>
              </View>
              <View style={[styles.statCard, { borderTopColor: monthlyData.balance >= 0 ? '#3f8600' : '#cf1322' }]}>
                <Text style={styles.statLabel}>结余</Text>
                <Text
                  style={[
                    styles.statValue,
                    { color: monthlyData.balance >= 0 ? '#3f8600' : '#cf1322' },
                  ]}
                >
                  ¥{monthlyData.balance.toFixed(2)}
                </Text>
              </View>
            </View>

            {renderCategoryTable(expenseData, '支出分类统计', '#cf1322')}
            {renderCategoryTable(incomeData, '收入分类统计', '#3f8600')}
          </>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fafafa',
  },
  header: {
    paddingHorizontal: 20,
    paddingVertical: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#18181b',
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 32,
  },
  monthSelector: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
  },
  monthArrow: {
    padding: 8,
  },
  monthText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#18181b',
    marginHorizontal: 24,
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  statCard: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 14,
    marginHorizontal: 4,
    borderTopWidth: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  statLabel: {
    fontSize: 12,
    color: '#8c8c8c',
    marginBottom: 6,
  },
  statValue: {
    fontSize: 16,
    fontWeight: '700',
  },
  tableCard: {
    backgroundColor: '#fff',
    borderRadius: 10,
    marginBottom: 16,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  tableHeader: {
    padding: 14,
    borderLeftWidth: 3,
    backgroundColor: '#fafafa',
  },
  tableTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#18181b',
  },
  tableRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderTopWidth: 1,
    borderTopColor: '#f5f5f5',
  },
  categoryName: {
    width: 70,
    fontSize: 13,
    color: '#18181b',
  },
  barContainer: {
    flex: 1,
    height: 8,
    backgroundColor: '#f0f0f0',
    borderRadius: 4,
    marginHorizontal: 8,
    overflow: 'hidden',
  },
  bar: {
    height: '100%',
    borderRadius: 4,
  },
  amount: {
    width: 90,
    fontSize: 13,
    fontWeight: '500',
    textAlign: 'right',
  },
  percentage: {
    width: 40,
    fontSize: 12,
    color: '#8c8c8c',
    textAlign: 'right',
  },
  emptyText: {
    padding: 20,
    textAlign: 'center',
    color: '#8c8c8c',
    fontSize: 13,
  },
})
