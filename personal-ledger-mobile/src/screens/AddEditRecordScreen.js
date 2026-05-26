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
        Alert.alert('成功', isEdit ? '修改成功' : '新增成功', [
          { text: '确定', onPress: () => navigation.goBack() },
        ])
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
      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
        <View style={styles.form}>
          <Text style={styles.label}>分类</Text>
          <TouchableOpacity
            style={styles.selectBtn}
            onPress={() => setShowCategoryPicker(!showCategoryPicker)}
          >
            <Text style={selectedCategory ? styles.selectText : styles.selectPlaceholder}>
              {selectedCategory ? selectedCategory.name : '请选择分类'}
            </Text>
            <Text style={styles.selectArrow}>{showCategoryPicker ? '▲' : '▼'}</Text>
          </TouchableOpacity>

          {showCategoryPicker && (
            <View style={styles.pickerCard}>
              <Text style={styles.pickerGroupTitle}>支出</Text>
              {expenseCategories.map((c) => (
                <TouchableOpacity
                  key={c.id}
                  style={[styles.pickerItem, categoryId === c.id && styles.pickerItemActive]}
                  onPress={() => { setCategoryId(c.id); setShowCategoryPicker(false) }}
                >
                  <Text style={[styles.pickerItemText, categoryId === c.id && styles.pickerItemTextActive]}>
                    {c.name}
                  </Text>
                </TouchableOpacity>
              ))}
              <Text style={styles.pickerGroupTitle}>收入</Text>
              {incomeCategories.map((c) => (
                <TouchableOpacity
                  key={c.id}
                  style={[styles.pickerItem, categoryId === c.id && styles.pickerItemActive]}
                  onPress={() => { setCategoryId(c.id); setShowCategoryPicker(false) }}
                >
                  <Text style={[styles.pickerItemText, categoryId === c.id && styles.pickerItemTextActive]}>
                    {c.name}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          )}

          <Text style={styles.label}>金额</Text>
          <View style={styles.amountInput}>
            <Text style={styles.amountPrefix}>¥</Text>
            <TextInput
              style={styles.amountField}
              placeholder="0.00"
              placeholderTextColor="#bfbfbf"
              value={amount}
              onChangeText={setAmount}
              keyboardType="decimal-pad"
            />
          </View>

          <Text style={styles.label}>备注</Text>
          <TextInput
            style={styles.textarea}
            placeholder="可选"
            placeholderTextColor="#bfbfbf"
            value={remark}
            onChangeText={setRemark}
            multiline
            numberOfLines={3}
            textAlignVertical="top"
          />

          <Text style={styles.label}>日期</Text>
          <TouchableOpacity
            style={styles.selectBtn}
            onPress={() => setShowDatePicker(true)}
          >
            <Text style={styles.selectText}>
              {dayjs(recordDate).format('YYYY-MM-DD')}
            </Text>
            <Text style={styles.selectArrow}>📅</Text>
          </TouchableOpacity>

          {showDatePicker && (
            <DateTimePicker
              value={recordDate}
              mode="date"
              display={Platform.OS === 'ios' ? 'spinner' : 'default'}
              onChange={onDateChange}
            />
          )}

          <TouchableOpacity
            style={[styles.saveBtn, submitting && styles.saveBtnDisabled]}
            onPress={handleSave}
            disabled={submitting}
            activeOpacity={0.8}
          >
            {submitting ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.saveBtnText}>{isEdit ? '保存修改' : '保存'}</Text>
            )}
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fafafa',
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
  },
  form: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    color: '#18181b',
    marginBottom: 8,
    marginTop: 16,
  },
  selectBtn: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    height: 48,
    borderWidth: 1,
    borderColor: '#e8e8e8',
    borderRadius: 8,
    paddingHorizontal: 16,
    backgroundColor: '#fafafa',
  },
  selectText: {
    fontSize: 16,
    color: '#18181b',
  },
  selectPlaceholder: {
    fontSize: 16,
    color: '#bfbfbf',
  },
  selectArrow: {
    fontSize: 12,
    color: '#8c8c8c',
  },
  pickerCard: {
    marginTop: 8,
    backgroundColor: '#fafafa',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e8e8e8',
    padding: 12,
  },
  pickerGroupTitle: {
    fontSize: 12,
    fontWeight: '600',
    color: '#8c8c8c',
    marginTop: 8,
    marginBottom: 6,
    marginLeft: 4,
  },
  pickerItem: {
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 6,
    marginBottom: 2,
  },
  pickerItemActive: {
    backgroundColor: '#18181b',
  },
  pickerItemText: {
    fontSize: 15,
    color: '#18181b',
  },
  pickerItemTextActive: {
    color: '#fff',
    fontWeight: '500',
  },
  amountInput: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 48,
    borderWidth: 1,
    borderColor: '#e8e8e8',
    borderRadius: 8,
    paddingHorizontal: 16,
    backgroundColor: '#fafafa',
  },
  amountPrefix: {
    fontSize: 18,
    fontWeight: '600',
    color: '#18181b',
    marginRight: 8,
  },
  amountField: {
    flex: 1,
    fontSize: 18,
    color: '#18181b',
  },
  textarea: {
    borderWidth: 1,
    borderColor: '#e8e8e8',
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    color: '#18181b',
    backgroundColor: '#fafafa',
    minHeight: 80,
  },
  saveBtn: {
    height: 48,
    backgroundColor: '#18181b',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 28,
  },
  saveBtnDisabled: {
    opacity: 0.6,
  },
  saveBtnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
})
