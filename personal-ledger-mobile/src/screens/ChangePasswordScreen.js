import { useState } from 'react'
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, Alert, ActivityIndicator,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { updatePassword } from '../api/user'
import { theme } from '../config/theme'
import FadeInView from '../components/FadeInView'
import ScaleButton from '../components/ScaleButton'

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
      <FadeInView style={{ flex: 1 }}>
        <View style={styles.form}>
          <View style={styles.inputGroup}>
            <Text style={styles.label}>原密码</Text>
            <TextInput
              style={styles.input}
              placeholder="请输入原密码"
              placeholderTextColor={theme.colors.textLight}
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
              placeholderTextColor={theme.colors.textLight}
              value={newPassword}
              onChangeText={setNewPassword}
              secureTextEntry
            />
          </View>

          <ScaleButton
            style={[styles.button, submitting && styles.buttonDisabled]}
            onPress={handleSubmit}
            disabled={submitting}
          >
            {submitting ? (
              <ActivityIndicator color={theme.colors.surface} />
            ) : (
              <Text style={styles.buttonText}>确认修改</Text>
            )}
          </ScaleButton>
        </View>
      </FadeInView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  form: {
    backgroundColor: theme.colors.surface,
    margin: theme.spacing.lg,
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.lg,
    ...theme.shadows.small,
  },
  inputGroup: {
    marginBottom: theme.spacing.lg,
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    color: theme.colors.primary,
    marginBottom: theme.spacing.sm,
  },
  input: {
    height: 48,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.borderRadius.sm,
    paddingHorizontal: theme.spacing.md,
    fontSize: 16,
    color: theme.colors.text,
    backgroundColor: theme.colors.background,
  },
  button: {
    height: 48,
    backgroundColor: theme.colors.primary,
    borderRadius: theme.borderRadius.sm,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: theme.spacing.sm,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: theme.colors.surface,
    fontSize: 16,
    fontWeight: '600',
  },
})
