/**
 * Shared ApexCharts theming bound to the app's design tokens, so every chart
 * matches the shell in light and dark mode. Spread the base into a chart's
 * options and override only the specifics:
 *
 *   const base = getBaseChartOptions(isDark);
 *   const options = { ...base, chart: { ...base.chart, type: 'bar' }, xaxis: { ...base.xaxis, categories } };
 */

// Brand violet + semantic token hexes (kept in sync with src/index.css @theme).
export const CHART_PALETTE = [
  "#6049ea", // brand-500
  "#a892f2", // brand-300
  "#12b76a", // success-500
  "#f79009", // warning-500
  "#f04438", // error-500
  "#0ba5ec", // blue-light-500
  "#ee46bc", // theme-pink-500
  "#7a5af8", // theme-purple-500
];

export function getBaseChartOptions(isDark: boolean): ApexCharts.ApexOptions {
  const axisColor = isDark ? "#98a2b3" : "#667085"; // gray-400 / gray-500
  const gridColor = isDark ? "#1d2939" : "#f2f4f7"; // gray-800 / gray-100

  return {
    chart: {
      toolbar: { show: false },
      background: "transparent",
      fontFamily: "Outfit, sans-serif",
    },
    colors: CHART_PALETTE,
    grid: { borderColor: gridColor, strokeDashArray: 3 },
    dataLabels: { enabled: false },
    legend: { show: false },
    xaxis: {
      labels: { style: { colors: axisColor, fontSize: "12px", fontWeight: 500 } },
      axisBorder: { show: false },
      axisTicks: { show: false },
    },
    yaxis: {
      labels: { style: { colors: axisColor, fontSize: "12px" } },
    },
    tooltip: { theme: isDark ? "dark" : "light" },
    states: {
      hover: { filter: { type: "darken", value: 0.9 } as { type?: string; value?: number } },
    },
  };
}

export default getBaseChartOptions;
