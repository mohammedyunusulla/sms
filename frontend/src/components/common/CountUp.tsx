import { FC } from "react";
import { useCountUp } from "../../hooks/useCountUp";

interface CountUpProps {
  /** Numbers animate; anything else (e.g. "12 / 30", "-") renders verbatim. */
  value: number | string;
  className?: string;
  duration?: number;
}

/**
 * Renders a stat value with a count-up animation when it is numeric.
 * The hook is always called (before any early return) to satisfy rules-of-hooks.
 */
const CountUp: FC<CountUpProps> = ({ value, className, duration }) => {
  const numeric = typeof value === "number" ? value : Number.NaN;
  const animated = useCountUp(isFinite(numeric) ? numeric : 0, duration);

  if (typeof value !== "number" || !isFinite(numeric)) {
    return <span className={className}>{value}</span>;
  }
  return <span className={className}>{animated.toLocaleString("en-IN")}</span>;
};

export default CountUp;
