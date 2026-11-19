import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge conditional class names and resolve Tailwind conflicts.
 *
 * `clsx` handles conditional/array/object inputs; `twMerge` ensures that a
 * caller-supplied class (e.g. `className="px-2"`) wins over a built-in default
 * (`px-4`) instead of both being emitted and the outcome depending on CSS order.
 *
 *   cn("px-4 py-2", isActive && "bg-brand-500", className)
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export default cn;
