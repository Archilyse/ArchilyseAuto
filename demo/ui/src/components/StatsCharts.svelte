<script lang="ts">
  import { Bar } from "svelte-chartjs";
  import {
    Chart as ChartJS,
    Title,
    Tooltip,
    Legend,
    BarElement,
    CategoryScale,
    LinearScale,
  } from "chart.js";
  import { COLORS_PER_FEATURE } from "../constants";
  import type { RetrieveStatsResponse } from "../types";
  import { statUtils } from "../utils";
  ChartJS.register(
    Title,
    Tooltip,
    Legend,
    BarElement,
    LinearScale,
    CategoryScale
  );

  export let stats: RetrieveStatsResponse;

  const countStats = statUtils.getCountStats(stats.statistics);
  const areaStats = statUtils.getAreaStats(stats.statistics);

  const countData = {
    labels: Object.keys(countStats),
    datasets: [
      {
        label: "Count",
        data: Object.values(countStats),
        backgroundColor: COLORS_PER_FEATURE.SUBTOTAL,
        hoverBackgroundColor: Object.keys(areaStats).map(
          (label) => COLORS_PER_FEATURE[label.toUpperCase()]
        ),
        borderColor: COLORS_PER_FEATURE.SUBTOTAL,

        borderWidth: 1,
      },
    ],
  };

  const areaWaterfallData = {
    labels: Object.keys(areaStats),
    datasets: [
      {
        label: "Count",
        data: Object.values(areaStats),
        backgroundColor: COLORS_PER_FEATURE.SUBTOTAL,
        hoverBackgroundColor: Object.keys(areaStats).map(
          (label) => COLORS_PER_FEATURE[label.toUpperCase()]
        ),
        borderColor: COLORS_PER_FEATURE.SUBTOTAL,
        borderWidth: 1,
      },
    ],
  };

  const font = {
    family: "'Barlow', sans-serif",
  };
  // @TODO: Consider hiding grids altogether
  const chartColor = "rgb(140,141, 146)"; // A kind of lightgrey
  const secondaryGridColor = "rgb(140,141, 146, 0.1)";
  const horizontalChartOptions = {
    plugins: {
      legend: { display: false },
      title: {
        text: "Element Distribution",
        display: true,
        align: "start",
        padding: 18,
        font,
      },
    },
    scales: {
      y: {
        ticks: {
          color: chartColor,
          font,
        },
        grid: { color: chartColor },
        border: { display: false },
      },
      x: {
        ticks: {
          color: chartColor,
          font,
        },
        grid: { color: secondaryGridColor },
        border: { display: false },
      },
    },
  };

  const waterFallChartOptions = {
    plugins: {
      legend: { display: false },
      title: {
        text: "Area Distribution",
        display: true,
        align: "start",
        padding: 18,
        font,
      },
    },
    scales: {
      y: {
        ticks: {
          color: chartColor,
          font,
        },
        grid: { color: chartColor },
        border: { display: false },
      },
      x: {
        ticks: {
          color: chartColor,
          font,
        },
        grid: { color: secondaryGridColor },
        border: { display: false },
      },
    },
  };
</script>

<div class="stats-charts">
  <div class="chart">
    <Bar
      data={countData}
      options={{ indexAxis: "y", ...horizontalChartOptions }}
    />
  </div>

  <div class="chart">
    <Bar data={areaWaterfallData} options={{ ...waterFallChartOptions }} />
  </div>
</div>

<style>
  .stats-charts {
    font-family: sans-serif;
    display: flex;
    justify-content: center;
    width: 100%;
    gap: 40px;
  }
  .chart {
    font-family: sans-serif;

    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 250px;
    width: 500px;
  }

  @media only screen and (max-width: 600px) {
    .stats-charts {
      display: flex;
      flex-direction: column;
    }
    .chart {
      height: 150px;
      flex: initial;
    }
  }
</style>
