import React, { useEffect, useRef } from 'react'
import { Animated } from 'react-native'

export default function FadeInView({ children, style, delay = 0 }) {
  const opacity = useRef(new Animated.Value(0)).current

  useEffect(() => {
    Animated.timing(opacity, {
      toValue: 1,
      duration: 400,
      useNativeDriver: true,
      delay,
    }).start()
  }, [delay])

  return (
    <Animated.View style={[{ opacity }, style]}>
      {children}
    </Animated.View>
  )
}
