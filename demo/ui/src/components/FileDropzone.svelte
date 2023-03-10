<script lang="ts">
  import Dropzone from "svelte-file-dropzone";
  import { UploadStatus } from "../types";
  import AuthError from "./AuthError.svelte";
  import { authError } from "../stores";

  const { LOADING, SUCCESS } = UploadStatus;

  export let uploadStatus;
  export let isAuthenticated;
  export let onSelectFile: (file: File) => void;
  export let onClickReset;

  const ACCEPTED_FILE_EXTENSIONS = [".png", ".pdf", ".svg", ".jpg"]; // @TODO: Review if these are the correct ones

  $: disableInteraction = uploadStatus === LOADING || uploadStatus === SUCCESS;

  const onFileDroppedOrSelected = async (event) => {
    const [fileToUpload] = event.detail.acceptedFiles;
    onSelectFile(fileToUpload);
  };
</script>

{#if isAuthenticated}
  <Dropzone
    name={"file-dropzone"}
    containerClasses={`file-dropzone ${disableInteraction ? "disabled" : ""}`}
    on:drop={onFileDroppedOrSelected}
    accept={ACCEPTED_FILE_EXTENSIONS}
    multiple={false}
  >
    <p class="drop-text">Drop a plan here or click to upload</p>
  </Dropzone>
{:else}
  <Dropzone
    name={"file-dropzone disabled"}
    containerClasses={`file-dropzone ${disableInteraction ? "disabled" : ""}`}
    on:drop={onFileDroppedOrSelected}
    accept={ACCEPTED_FILE_EXTENSIONS}
    disabled={true}
    multiple={false}
  >
    {#if $authError}
      <AuthError {onClickReset} />
    {:else}
      <p>Log in with your account to upload plans</p>
    {/if}
  </Dropzone>
{/if}

<style>
  /* Global style needed otherwise linter will complain we are not using the styles */
  :global(.file-dropzone) {
    flex: initial !important;
    background-color: inherit !important;
    width: var(--plan-area-width-taken);
    height: 20%;
    justify-content: center;
    font-size: 1em; /* Assuming font-size of html == 16 px, this would be 16px * 2 */
    padding: 0 !important;
    cursor: pointer;
    margin-top: 150px; /* @TODO: Adjust */
    margin-bottom: 50px; /* @TODO: Adjust */
  }
  :global(.file-dropzone.disabled) {
    cursor: none !important;
    pointer-events: none !important;
  }
  .drop-text {
    text-align: center;
  }
  @media only screen and (max-width: 600px) {
    .drop-text {
      padding: 5px;
    }
    :global(.file-dropzone) {
      margin-top: 10px;
    }
  }
</style>
