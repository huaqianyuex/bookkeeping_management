import { ActivityIndicator, View, StyleSheet } from 'react-native'
import { NavigationContainer } from '@react-navigation/native'
import { createNativeStackNavigator } from '@react-navigation/native-stack'
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs'
import { Ionicons } from '@expo/vector-icons'
import { useAuth } from '../context/AuthContext'

import LoginScreen from '../screens/LoginScreen'
import RegisterScreen from '../screens/RegisterScreen'
import DashboardScreen from '../screens/DashboardScreen'
import RecordsScreen from '../screens/RecordsScreen'
import AddEditRecordScreen from '../screens/AddEditRecordScreen'
import CategoriesScreen from '../screens/CategoriesScreen'
import UserInfoScreen from '../screens/UserInfoScreen'
import ChangePasswordScreen from '../screens/ChangePasswordScreen'

const Stack = createNativeStackNavigator()
const Tab = createBottomTabNavigator()
const RecordStack = createNativeStackNavigator()
const ProfileStack = createNativeStackNavigator()
const AuthStack = createNativeStackNavigator()

function AuthNavigator() {
  return (
    <AuthStack.Navigator screenOptions={{ headerShown: false }}>
      <AuthStack.Screen name="Login" component={LoginScreen} />
      <AuthStack.Screen name="Register" component={RegisterScreen} />
    </AuthStack.Navigator>
  )
}

function RecordStackNavigator() {
  return (
    <RecordStack.Navigator>
      <RecordStack.Screen
        name="RecordsList"
        component={RecordsScreen}
        options={{ headerShown: false }}
      />
      <RecordStack.Screen
        name="AddEditRecord"
        component={AddEditRecordScreen}
        options={({ route }) => ({
          title: route.params?.record ? '编辑账单' : '新增账单',
          headerTintColor: '#18181b',
        })}
      />
    </RecordStack.Navigator>
  )
}

function ProfileStackNavigator() {
  return (
    <ProfileStack.Navigator>
      <ProfileStack.Screen
        name="UserInfo"
        component={UserInfoScreen}
        options={{ headerShown: false }}
      />
      <ProfileStack.Screen
        name="ChangePassword"
        component={ChangePasswordScreen}
        options={{ title: '修改密码', headerTintColor: '#18181b' }}
      />
    </ProfileStack.Navigator>
  )
}

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName
          if (route.name === 'Dashboard') {
            iconName = focused ? 'stats-chart' : 'stats-chart-outline'
          } else if (route.name === 'RecordsTab') {
            iconName = focused ? 'receipt' : 'receipt-outline'
          } else if (route.name === 'CategoriesTab') {
            iconName = focused ? 'grid' : 'grid-outline'
          } else if (route.name === 'ProfileTab') {
            iconName = focused ? 'person' : 'person-outline'
          }
          return <Ionicons name={iconName} size={size} color={color} />
        },
        tabBarActiveTintColor: '#18181b',
        tabBarInactiveTintColor: '#8c8c8c',
        headerShown: false,
        tabBarStyle: {
          borderTopColor: '#f0f0f0',
          paddingBottom: 4,
          height: 56,
        },
        tabBarLabelStyle: {
          fontSize: 11,
        },
      })}
    >
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{ tabBarLabel: '数据概览' }}
      />
      <Tab.Screen
        name="RecordsTab"
        component={RecordStackNavigator}
        options={{ tabBarLabel: '账单' }}
      />
      <Tab.Screen
        name="CategoriesTab"
        component={CategoriesScreen}
        options={{ tabBarLabel: '分类' }}
      />
      <Tab.Screen
        name="ProfileTab"
        component={ProfileStackNavigator}
        options={{ tabBarLabel: '我的' }}
      />
    </Tab.Navigator>
  )
}

export default function AppNavigator() {
  const { user, initializing } = useAuth()

  if (initializing) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" color="#18181b" />
      </View>
    )
  }

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {user ? (
          <Stack.Screen name="Main" component={MainTabs} />
        ) : (
          <Stack.Screen name="Auth" component={AuthNavigator} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  )
}

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
})
