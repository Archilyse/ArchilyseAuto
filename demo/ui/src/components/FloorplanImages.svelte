<script lang="ts">
  import { fade } from "svelte/transition";
  import { UploadStatus } from "../types";
  import { beforeUpdate } from "svelte";
  import {
    processedWalls,
    processedIcons,
    processedSpaces,
    processedBackground,
  } from "../stores";

  export let original;
  export let uploadStatus;

  const OPACITY = 0.5;
  const STILL_LOADING_MS = 20 * 1000;

  let processedImgClass;
  let stillLoading;
  $: processedImgClass = `processed-img ${
    uploadStatus !== UploadStatus.SUCCESS ? "blur" : ""
  }`;

  beforeUpdate(() => {
    setTimeout(() => {
      if (uploadStatus === UploadStatus.LOADING) {
        stillLoading = true;
      }
    }, STILL_LOADING_MS);
  });
</script>

{#if original}
  <div class="floorplan-images ">
    <img
      class="original"
      src={original}
      alt="Preview of the uploaded plan without processing"
    />
    {#if $processedBackground}
      <img
        in:fade
        class={processedImgClass}
        style={`opacity: ${OPACITY}`}
        src={$processedBackground}
        alt="Processed background of the uploaded plan"
      />
    {/if}
    {#if $processedSpaces}
      <img
        in:fade
        class={processedImgClass}
        style={`opacity: ${OPACITY}`}
        src={$processedSpaces}
        alt="Processed spaces of the uploaded plan"
      />
    {/if}
    {#if $processedIcons}
      <img
        in:fade
        class={processedImgClass}
        style={`opacity: ${OPACITY}`}
        src={$processedIcons}
        alt="Processed features of the uploaded plan"
      />
    {/if}
    {#if $processedWalls}
      <img
        in:fade
        class={processedImgClass}
        style={`opacity: ${OPACITY}`}
        src={$processedWalls}
        alt="Processed walls of the uploaded plan"
      />
    {/if}
    {#if uploadStatus === UploadStatus.LOADING}
      <div class="loading slide-in-left" />
      <p class="loading-text">
        Loading...
        {#if stillLoading}
          <p in:fade>(Still processing, this may take some time...)</p>
        {/if}
      </p>
    {:else if uploadStatus === UploadStatus.FAILED}
      <div class="loading" />
      <p class="loading-text">
        Error uploading the file! Please try again in a few minutes or contact
        us.
      </p>
    {/if}
  </div>
{/if}

<style>
  .floorplan-images {
    display: grid;
    grid-template-columns: [first-col] minmax(0, 1fr);
    grid-template-rows: [first-row] minmax(0, 1fr);
  }
  .processed-img.blur {
    filter: blur(8px);
  }

  .loading {
    background-color: #434c50;
    opacity: 0.6;
    grid-column-start: first-col;
    grid-row-start: first-row;
    transform-origin: 0 0;
  }

  .loading-text {
    position: absolute;
    padding-left: 20px;
    color: white;
  }

  .slide-in-left {
    -webkit-animation: slide-in-left 120s cubic-bezier(0.25, 0.46, 0.45, 0.94)
      both;
    animation: slide-in-left 120s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
  }

  @keyframes slide-in-left {
    0% {
      transform: scaleX(0);
    }
    100% {
      transform: scaleX(1);
    }
  }

  .original {
    grid-column-start: first-col;
    grid-row-start: first-row;
  }
  .processed-img {
    grid-column-start: first-col;
    grid-row-start: first-row;
  }

  img {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }
</style>
