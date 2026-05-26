import { useState } from 'react'
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, Alert, ActivityIndicator,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { updatePassword } from '../api/user'

export default function ChangePasswordScreen() {
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    if (!oldPassword) {
      Alert.alert('提示', '请输入原密码')
      return
    }
    if (!newPassword) {
      Alert.alert('提示', '请输入新密码')
      return
    }
    if (newPassword.length < 6 || newPassword.length > 20) {
      Alert.alert('提示', '新密码长度6-20位')
      return
    }
    setSubmitting(true)
    try {
      const res = await updatePassword({ oldPassword, newPassword })
      if (res.code === 200) {
        Alert.alert('成功', '密码修改成功')
        setOldPassword('')
        setNewPassword('')
      } else {
        Alert.alert('修改失败', res.message)
      }
    } catch (e) {
      Alert.alert('错误', '修改失败，请检查网络')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <View style={styles.form}>
        <View style={styles.inputGroup}>
          <Text style={styles.label}>原密码</Text>
          <TextInput
            style={styles.input}
            placeholder="请输入原密码"
            placeholderTextColor="#bfbfbf"
            value={oldPassword}
            onChangeText={setOldPassword}
            secureTextEntry
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>新密码</Text>
          <TextInput
            style={styles.input}
            placeholder="请输入新密码（6-20位）"
            placeholderTextColor="#bfbfbf"
            value={newPassword}
            onChangeText={setNewPassword}
            secureTextEntry
          />
        </View>

        <TouchableOpacity
          style={[styles.button, submitting && styles.buttonDisabled]}
          onPress={handleSubmit}
          disabled={submitting}
          activeOpacity={0.8}
        >
          {submitting ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>确认修改</Text>
          )}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fafafa',
  },
  form: {
    backgroundColor: '#fff',
    margin: 20,
    borderRadius: 12,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  inputGroup: {
    marginBottom: 20,
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    color: '#18181b',
    marginBottom: 8,
  },
  input: {
    height: 48,
    borderWidth: 1,
    borderColor: '#e8e8e8',
    borderRadius: 8,
    paddingHorizontal: 16,
    fontSize: 16,
    color: '#18181b',
    backgroundColor: '#fafafa',
  },
  button: {
    height: 48,
    backgroundColor: '#18181b',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 8,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
})
