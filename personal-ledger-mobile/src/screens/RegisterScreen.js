import { useState } from 'react'
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, KeyboardAvoidingView, Platform, Alert, ActivityIndicator,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { register } from '../api/user'
import { theme } from '../config/theme'
import FadeInView from '../components/FadeInView'
import ScaleButton from '../components/ScaleButton'

export default function RegisterScreen({ navigation }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleRegister = async () => {
    if (!username || !password) {
      Alert.alert('提示', '请填写完整信息')
      return
    }
    if (username.length < 2 || username.length > 20) {
      Alert.alert('提示', '用户名长度2-20位')
      return
    }
    if (password.length < 6 || password.length > 20) {
      Alert.alert('提示', '密码长度6-20位')
      return
    }
    setSubmitting(true)
    try {
      const res = await register({ username, password })
      if (res.code === 200) {
        Alert.alert('注册成功', '请登录', [
          { text: '确定', onPress: () => navigation.goBack() },
        ])
      } else {
        Alert.alert('注册失败', res.message || '请重试')
      }
    } catch (e) {
      Alert.alert('错误', '网络连接失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.inner}
      >
        <FadeInView>
          <View style={styles.header}>
            <Text style={styles.title}>注册账号</Text>
            <Text style={styles.subtitle}>创建你的个人记账本</Text>
          </View>

          <View style={styles.form}>
            <View style={styles.inputGroup}>
              <Text style={styles.label}>用户名</Text>
              <TextInput
                style={styles.input}
                placeholder="用户名（2-20位）"
                placeholderTextColor={theme.colors.textLight}
                value={username}
                onChangeText={setUsername}
                autoCapitalize="none"
                autoCorrect={false}
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>密码</Text>
              <TextInput
                style={styles.input}
                placeholder="密码（6-20位）"
                placeholderTextColor={theme.colors.textLight}
                value={password}
                onChangeText={setPassword}
                secureTextEntry
              />
            </View>

            <ScaleButton
              style={[styles.button, submitting && styles.buttonDisabled]}
              onPress={handleRegister}
              disabled={submitting}
            >
              {submitting ? (
                <ActivityIndicator color={theme.colors.surface} />
              ) : (
                <Text style={styles.buttonText}>注册</Text>
              )}
            </ScaleButton>

            <ScaleButton
              style={styles.link}
              onPress={() => navigation.goBack()}
            >
              <Text style={styles.linkText}>
                已有账号？<Text style={styles.linkHighlight}>返回登录</Text>
              </Text>
            </ScaleButton>
          </View>
        </FadeInView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  inner: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 32,
  },
  header: {
    alignItems: 'center',
    marginBottom: 48,
  },
  title: {
    ...theme.typography.h1,
    color: theme.colors.primary,
    marginBottom: theme.spacing.sm,
  },
  subtitle: {
    fontSize: 14,
    color: theme.colors.textSecondary,
  },
  form: {
    backgroundColor: theme.colors.surface,
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
  link: {
    alignItems: 'center',
    marginTop: theme.spacing.lg,
  },
  linkText: {
    fontSize: 14,
    color: theme.colors.textSecondary,
  },
  linkHighlight: {
    color: theme.colors.primary,
    fontWeight: '500',
  },
})
