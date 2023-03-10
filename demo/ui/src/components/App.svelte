<script lang="ts">
  import { onMount } from "svelte";
  import FileDropzone from "./FileDropzone.svelte";
  import Sidebar from "./Sidebar.svelte";
  import { fetchStats, localUrlToBlob, uploadPlan } from "../utils";
  import { UploadStatus, type RetrieveStatsResponse } from "../types";
  import { auth } from "../providers";
  import {
    authError,
    processedWalls,
    processedIcons,
    processedSpaces,
    processedBackground,
  } from "../stores";
  import InitialInfo from "./InitialInfo.svelte";
  import Snackbar from "./Snackbar.svelte";
  import FloorplanImages from "./FloorplanImages.svelte";
  import StatsCharts from "./StatsCharts.svelte";
  import LoadingProgress from "./LoadingProgress.svelte";

  const CANCELLED_REQUEST_ERROR = "ERR_CANCELED";

  let original;
  let isAuthenticated = false;
  let uploadStatus: UploadStatus | "" = "";
  let checkingAuth;
  let stats: RetrieveStatsResponse | null = null;

  let isDisplayingAPlan = false;

  $: isDisplayingAPlan = original || uploadStatus === UploadStatus.SUCCESS;

  let preloadedPlans: string[] = Object.values(
    import.meta.glob(
      ["../assets/preloaded-plans/*.jpg", "../assets/preloaded-plans/*.png"],
      { eager: true, import: "default" }
    )
  );

  onMount(async () => {
    checkingAuth = true;
    isAuthenticated = await auth.authenticate();
    checkingAuth = false;
  });

  const processAndUploadPlan = async (fileToUpload: File) => {
    try {
      $processedWalls = null;
      $processedIcons = null;
      $processedSpaces = null;
      $processedBackground = null;
      stats = null;

      uploadStatus = UploadStatus.LOADING;
      original = URL.createObjectURL(fileToUpload);

      const taskIds = await uploadPlan(fileToUpload);

      try {
        stats = await fetchStats(taskIds);
      } catch (error) {
        console.error(`Error pulling stats, ${error}`);
      }

      uploadStatus = UploadStatus.SUCCESS;
    } catch (error) {
      if (error.code === CANCELLED_REQUEST_ERROR) {
        console.debug(
          "A new upload has begun, previous one has been cancelled."
        );
        return;
      }
      uploadStatus = UploadStatus.FAILED;
      console.log("Error uploading the file", error);
    }
  };

  const onLoadPreloadedPlan = async (fileUrl) => {
    const fileToUpload = await localUrlToBlob(fileUrl);
    await processAndUploadPlan(fileToUpload);
  };

  const onClickReset = () => {
    original = null;
    $processedWalls = null;
    $processedIcons = null;
    $processedSpaces = null;
    $processedBackground = null;
    uploadStatus = "";
    $authError = null;
    stats = null;
  };
</script>

<main class="main">
  <Sidebar
    {isAuthenticated}
    {onClickReset}
    onSelectFile={processAndUploadPlan}
  />
  <div class={"plan-area"}>
    {#if isDisplayingAPlan}
      <div class={`results ${stats ? "finished" : ""}`}>
        <FloorplanImages {original} {uploadStatus} />
        {#if stats}
          <StatsCharts {stats} />
        {:else}
          <LoadingProgress />
        {/if}
      </div>
    {:else}
      <h2>Archilyse Auto-Annotation</h2>
      <InitialInfo
        {preloadedPlans}
        onClickExample={onLoadPreloadedPlan}
        onDropExample={onLoadPreloadedPlan}
      />
      <FileDropzone
        {uploadStatus}
        {isAuthenticated}
        {onClickReset}
        onSelectFile={processAndUploadPlan}
      />
    {/if}
    <Snackbar {isAuthenticated} />
  </div>
</main>

<style>
  .results {
    display: grid;
    grid-template-columns: 1fr;
    grid-template-rows: minmax(70%, 1fr) minmax(20%, 1fr);
    height: 90%;
    width: 85%;
    padding: 20px;
  }
  .results.finished {
    justify-items: center;
  }
  .main {
    display: grid;
    height: 100%;
    grid-template-columns: 0.59fr 4fr;
    grid-template-rows: minmax(0, 1fr);
  }

  .plan-area {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }
  @media only screen and (max-width: 600px) {
    .results {
      display: grid;
      grid-template-columns: 1fr;
      grid-template-rows: 1fr;
    }

    .plan-area {
      overflow-y: scroll;
      height: 100%;
      width: 100%;
    }
    .main {
      display: flex;
      flex-direction: column-reverse;
    }
  }
</style>
