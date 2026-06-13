/**
 * AnimatedRoute - Wraps children with a fade-in-up animation on mount.
 *
 * Usage:
 *   <AnimatedRoute>
 *     <YourPageComponent />
 *   </AnimatedRoute>
 *
 * The animation uses CSS @keyframes defined in design-tokens.css.
 * Each route remount triggers the animation from scratch via React key behavior.
 */
export default function AnimatedRoute({ children }) {
  return (
    <div className="animated-route">
      {children}
    </div>
  )
}
