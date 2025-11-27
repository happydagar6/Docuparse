import * as React from "react"

const MOBILE_BREAKPOINT = 768

export function useIsMobile() {
  const [isMobile, setIsMobile] = React.useState(undefined)

  // React 19.2: useEffectEvent for media query handler without dependencies
  const handleChange = React.useEffectEvent(() => {
    const newIsMobile = window.innerWidth < MOBILE_BREAKPOINT
    React.startTransition(() => {
      setIsMobile(newIsMobile)
    })
  })

  // React 19.2: Use useLayoutEffect for synchronous DOM measurements
  React.useLayoutEffect(() => {
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
    
    // Set initial value immediately
    setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)
    
    // Listen for changes
    mql.addEventListener("change", handleChange)
    return () => mql.removeEventListener("change", handleChange)
  }, []) // 🎉 No dependencies needed!

  return !!isMobile
}
