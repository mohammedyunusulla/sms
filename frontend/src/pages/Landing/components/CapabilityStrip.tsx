import Reveal from "./Reveal";

const ITEMS = [
  { value: "7", label: "user roles, each with tailored access" },
  { value: "15+", label: "connected school modules" },
  { value: "1", label: "dedicated database per school" },
  { value: "100%", label: "browser-based, nothing to install" },
];

export default function CapabilityStrip() {
  return (
    <section aria-label="EduSpyre at a glance" className="px-5 sm:px-8">
      <Reveal className="mx-auto max-w-6xl">
        <ul className="grid grid-cols-2 gap-px overflow-hidden rounded-3xl border border-gray-200 bg-gray-200 shadow-sm lg:grid-cols-4 dark:border-white/10 dark:bg-white/10">
          {ITEMS.map((item) => (
            <li
              key={item.label}
              className="flex flex-col items-center gap-1 bg-white px-4 py-7 text-center dark:bg-gray-950"
            >
              <span className="landing-gradient-text text-3xl font-bold tracking-tight sm:text-4xl">{item.value}</span>
              <span className="text-sm text-gray-600 dark:text-gray-400">{item.label}</span>
            </li>
          ))}
        </ul>
      </Reveal>
    </section>
  );
}
