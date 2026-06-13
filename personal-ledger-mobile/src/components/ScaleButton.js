import React, { useRef } from 'react'
import { TouchableOpacity, Animated } from 'react-native'

export default function ScaleButton({ children, style, onPress, onLongPress, ...props }) {
  const scale = useRef(new Animated.Value(1)).current

  const handlePressIn = () => {
    Animated.spring(scale, {
      toValue: 0.97,
      useNativeDriver: true,
      friction: 5,
    }).start()
  }

  const handlePressOut = () => {
    Animated.spring(scale, {
      toValue: 1,
      useNativeDriver: true,
      friction: 5,
    }).start()
  }

  return (
    <TouchableOpacity
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      onPress={onPress}
      onLongPress={onLongPress}
      activeOpacity={0.9}
      {...props}
    >
      <Animated.View style={[{ transform: [{ scale }] }, style]}>
        {children}
      </Animated.View>
    </TouchableOpacity>
  )
}
