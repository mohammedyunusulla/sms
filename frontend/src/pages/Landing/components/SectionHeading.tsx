import type { ReactNode } from "react";

interface SectionHeadingProps {
  eyebrow: string;
  title: ReactNode;
  description?: ReactNode;
  align?: "center" | "left";
  /** Use on dark backgrounds. */
  inverted?: boolean;
}

export default function SectionHeading({
  eyebrow,
  title,
  description,
  align = "center",
  inverted = false,
}: SectionHeadingProps) {
  return (
    <div className={align === "center" ? "mx-auto max-w-2xl text-center" : "max-w-2xl"}>
      <p
        className={`text-sm font-semibold uppercase tracking-[0.14em] ${
          inverted ? "text-brand-300" : "text-brand-600 dark:text-brand-400"
        }`}
      >
        {eyebrow}
      </p>
      <h2
        className={`mt-3 text-3xl font-bold tracking-tight sm:text-4xl ${
          inverted ? "text-white" : "text-gray-900 dark:text-white"
        }`}
      >
        {title}
      </h2>
      {description && (
        <p
          className={`mt-4 text-lg leading-relaxed ${
            inverted ? "text-gray-300" : "text-gray-600 dark:text-gray-400"
          }`}
        >
          {description}
        </p>
      )}
    </div>
  );
}
