import { useState, useEffect } from 'react'
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, ScrollView, Alert, ActivityIndicator, Platform,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import DateTimePicker from '@react-native-community/datetimepicker'
import dayjs from 'dayjs'
import { addRecord, updateRecord } from '../api/record'
import { getCategoryList } from '../api/category'
import { theme } from '../config/theme'
import FadeInView from '../components/FadeInView'
import ScaleButton from '../components/ScaleButton'

export default function AddEditRecordScreen({ route, navigation }) {
  const record = route.params?.record
  const isEdit = !!record

  const [categories, setCategories] = useState([])
  const [categoryId, setCategoryId] = useState(record?.categoryId || null)
  const [amount, setAmount] = useState(record ? String(record.amount) : '')
  const [remark, setRemark] = useState(record?.remark || '')
  const [recordDate, setRecordDate] = useState(
    record ? dayjs(record.recordDate).toDate() : new Date()
  )
  const [showDatePicker, setShowDatePicker] = useState(false)
  const [showCategoryPicker, setShowCategoryPicker] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const res = await getCategoryList()
        if (res.code === 200) setCategories(res.data)
      } catch (e) {}
    }
    fetchCategories()
  }, [])

  const expenseCategories = categories.filter((c) => c.type === 0)
  const incomeCategories = categories.filter((c) => c.type === 1)

  const selectedCategory = categories.find((c) => c.id === categoryId)

  const handleSave = async () => {
    if (!categoryId) {
      Alert.alert('提示', '请选择分类')
      return
    }
    if (!amount || parseFloat(amount) <= 0) {
      Alert.alert('提示', '请输入有效的金额')
      return
    }
    setSubmitting(true)
    try {
      const payload = {
        categoryId,
        amount: parseFloat(amount),
        remark,
        recordDate: dayjs(recordDate).format('YYYY-MM-DD'),
      }
      let res
      if (isEdit) {
        res = await updateRecord(record.id, payload)
      } else {
        res = await addRecord(payload)
      }
      if (res.code === 200) {
        // 使用 navigate 代替 goBack，携带 refresh 信号通知列表页重新加载
        navigation.navigate('RecordsList', { refresh: Date.now() })
      } else {
        Alert.alert('失败', res.message)
      }
    } catch (e) {
      Alert.alert('错误', '保存失败')
    } finally {
      setSubmitting(false)
    }
  }

  const onDateChange = (event, selectedDate) => {
    setShowDatePicker(Platform.OS === 'ios')
    if (selectedDate) setRecordDate(selectedDate)
  }

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <FadeInView style={{ flex: 1 }}>
        <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
          <View style={styles.form}>
            <Text style={styles.label}>分类</Text>
            <ScaleButton
              style={styles.selectBtn}
              onPress={() => setShowCategoryPicker(!showCategoryPicker)}
            >
              <Text style={selectedCategory ? styles.selectText : styles.selectPlaceholder}>
                {selectedCategory ? selectedCategory.name : '请选择分类'}
              </Text>
              <Text style={styles.selectArrow}>{showCategoryPicker ? '▲' : '▼'}</Text>
            </ScaleButton>

            {showCategoryPicker && (
              <View style={styles.pickerCard}>
                <Text style={styles.pickerGroupTitle}>支出</Text>
                {expenseCategories.map((c) => (
                  <ScaleButton
                    key={c.id}
                    style={[styles.pickerItem, categoryId === c.id && styles.pickerItemActive]}
                    onPress={() => { setCategoryId(c.id); setShowCategoryPicker(false) }}
                  >
                    <Text style={[styles.pickerItemText, categoryId === c.id && styles.pickerItemTextActive]}>
                      {c.name}
                    </Text>
                  </ScaleButton>
                ))}
                <Text style={styles.pickerGroupTitle}>收入</Text>
                {incomeCategories.map((c) => (
                  <ScaleButton
                    key={c.id}
                    style={[styles.pickerItem, categoryId === c.id && styles.pickerItemActive]}
                    onPress={() => { setCategoryId(c.id); setShowCategoryPicker(false) }}
                  >
                    <Text style={[styles.pickerItemText, categoryId === c.id && styles.pickerItemTextActive]}>
                      {c.name}
                    </Text>
                  </ScaleButton>
                ))}
              </View>
            )}

            <Text style={styles.label}>金额</Text>
            <View style={styles.amountInput}>
              <Text style={styles.amountPrefix}>¥</Text>
              <TextInput
                style={styles.amountField}
                placeholder="0.00"
                placeholderTextColor={theme.colors.textLight}
                value={amount}
                onChangeText={setAmount}
                keyboardType="decimal-pad"
              />
            </View>

            <Text style={styles.label}>备注</Text>
            <TextInput
              style={styles.textarea}
              placeholder="可选"
              placeholderTextColor={theme.colors.textLight}
              value={remark}
              onChangeText={setRemark}
              multiline
              numberOfLines={3}
              textAlignVertical="top"
            />

            <Text style={styles.label}>日期</Text>
            <ScaleButton
              style={styles.selectBtn}
              onPress={() => setShowDatePicker(true)}
            >
              <Text style={styles.selectText}>
                {dayjs(recordDate).format('YYYY-MM-DD')}
              </Text>
              <Text style={styles.selectArrow}>📅</Text>
            </ScaleButton>

            {showDatePicker && (
              <DateTimePicker
                value={recordDate}
                mode="date"
                display={Platform.OS === 'ios' ? 'spinner' : 'default'}
                onChange={onDateChange}
              />
            )}

            <ScaleButton
              style={[styles.saveBtn, submitting && styles.saveBtnDisabled]}
              onPress={handleSave}
              disabled={submitting}
            >
              {submitting ? (
                <ActivityIndicator color={theme.colors.surface} />
              ) : (
                <Text style={styles.saveBtnText}>{isEdit ? '保存修改' : '保存'}</Text>
              )}
            </ScaleButton>
          </View>
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
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: theme.spacing.lg,
  },
  form: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.lg,
    ...theme.shadows.small,
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    color: theme.colors.primary,
    marginBottom: theme.spacing.sm,
    marginTop: theme.spacing.md,
  },
  selectBtn: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    height: 48,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.borderRadius.sm,
    paddingHorizontal: theme.spacing.md,
    backgroundColor: theme.colors.background,
  },
  selectText: {
    fontSize: 16,
    color: theme.colors.text,
  },
  selectPlaceholder: {
    fontSize: 16,
    color: theme.colors.textLight,
  },
  selectArrow: {
    fontSize: 12,
    color: theme.colors.textSecondary,
  },
  pickerCard: {
    marginTop: theme.spacing.sm,
    backgroundColor: theme.colors.background,
    borderRadius: theme.borderRadius.sm,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing.md,
  },
  pickerGroupTitle: {
    fontSize: 12,
    fontWeight: '600',
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.sm,
    marginBottom: 6,
    marginLeft: 4,
  },
  pickerItem: {
    paddingVertical: 10,
    paddingHorizontal: theme.spacing.md,
    borderRadius: 6,
    marginBottom: 2,
  },
  pickerItemActive: {
    backgroundColor: theme.colors.primary,
  },
  pickerItemText: {
    fontSize: 15,
    color: theme.colors.text,
  },
  pickerItemTextActive: {
    color: theme.colors.surface,
    fontWeight: '500',
  },
  amountInput: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 48,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.borderRadius.sm,
    paddingHorizontal: theme.spacing.md,
    backgroundColor: theme.colors.background,
  },
  amountPrefix: {
    fontSize: 18,
    fontWeight: '600',
    color: theme.colors.primary,
    marginRight: theme.spacing.sm,
  },
  amountField: {
    flex: 1,
    fontSize: 18,
    color: theme.colors.text,
  },
  textarea: {
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.borderRadius.sm,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.md,
    fontSize: 16,
    color: theme.colors.text,
    backgroundColor: theme.colors.background,
    minHeight: 80,
  },
  saveBtn: {
    height: 48,
    backgroundColor: theme.colors.primary,
    borderRadius: theme.borderRadius.sm,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: theme.spacing.xl,
  },
  saveBtnDisabled: {
    opacity: 0.6,
  },
  saveBtnText: {
    color: theme.colors.surface,
    fontSize: 16,
    fontWeight: '600',
  },
})
