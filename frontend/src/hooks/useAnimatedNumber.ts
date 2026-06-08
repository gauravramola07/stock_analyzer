import { useState, useEffect, useRef } from 'react';

export function useAnimatedNumber(
  target: number | null | undefined,
  duration = 800,
  decimals = 2
): string {
  const [display, setDisplay] = useState<string>(
    target !== null && target !== undefined && !Number.isNaN(target)
      ? Number(target).toFixed(decimals)
      : '—'
  );
  const startTime = useRef<number | null>(null);
  const startVal = useRef(0);
  const targetVal = useRef(0);

  useEffect(() => {
    if (target === null || target === undefined || Number.isNaN(Number(target))) {
      setDisplay('—');
      return;
    }

    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (prefersReducedMotion) {
      setDisplay(Number(target).toFixed(decimals));
      return;
    }

    targetVal.current = Number(target);
    startVal.current = 0;
    startTime.current = null;

    let raf: number;

    const easeOutExpo = (t: number): number => {
      return t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
    };

    const tick = (timestamp: number) => {
      if (startTime.current === null) startTime.current = timestamp;
      const elapsed = timestamp - startTime.current;
      const progress = Math.min(elapsed / duration, 1);
      const eased = easeOutExpo(progress);
      const current = startVal.current + (targetVal.current - startVal.current) * eased;
      setDisplay(current.toFixed(decimals));

      if (progress < 1) {
        raf = requestAnimationFrame(tick);
      }
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration, decimals]);

  return display;
}
