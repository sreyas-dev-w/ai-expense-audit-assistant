"use client"

import { useSyncExternalStore } from "react"
import DotField from "@/components/landing/dot-field"

const subscribeReducedMotion = (onChange: () => void) => {
  const mq = window.matchMedia("(prefers-reduced-motion: reduce)")
  mq.addEventListener("change", onChange)
  return () => mq.removeEventListener("change", onChange)
}

function usePrefersReducedMotion() {
  return useSyncExternalStore(
    subscribeReducedMotion,
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    () => false
  )
}

export function HeroDotField() {
  const reduceMotion = usePrefersReducedMotion()

  if (reduceMotion) return null

  return (
    <DotField
      dotRadius={1.5}
      dotSpacing={16}
      cursorRadius={460}
      bulgeOnly
      bulgeStrength={64}
      glowRadius={210}
      sparkle={false}
      waveAmplitude={0}
      gradientFrom="rgba(0, 88, 96, 0.62)"
      gradientTo="rgba(96, 165, 178, 0.36)"
      glowColor="rgba(1, 110, 116, 0.14)"
    />
  )
}