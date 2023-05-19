<script lang="ts">
    import Dropzone from "svelte-file-dropzone";
    import { UploadStatus } from "../types";
    import { UPLOAD_CONFIG } from "../constants";
    const { LOADING, SUCCESS } = UploadStatus;
    const { MAX_FILE_SIZE, OPTIMAL_SCALE, ACCEPTED_FILE_EXTENSIONS } = UPLOAD_CONFIG;
    const MAX_SIZE_MB = MAX_FILE_SIZE / 1024 ** 2;

    export let uploadStatus;
    export let onSelectFile: (file: File) => void;
    export let fileTooLarge = false; // This is a prop so that it can be used in the test easily
    let rejectedFileMessage = "";

    $: disableInteraction = uploadStatus === LOADING || uploadStatus === SUCCESS;

    const onFileDroppedOrSelected = async (event) => {
        rejectedFileMessage = "";
        const [fileToUpload] = event.detail.acceptedFiles;
        const [rejectedFile] = event.detail.fileRejections;

        if (!fileToUpload && rejectedFile) {
            rejectedFileMessage = rejectedFile.errors[0]?.message;
            return;
        }

        if (fileToUpload.size > MAX_FILE_SIZE) {
            fileTooLarge = true;
        } else {
            fileTooLarge = false;
            onSelectFile(fileToUpload);
        }
    };
</script>

<Dropzone
    name={"file-dropzone"}
    containerClasses={`file-dropzone ${disableInteraction ? "disabled" : ""}`}
    on:drop={onFileDroppedOrSelected}
    accept={ACCEPTED_FILE_EXTENSIONS}
    multiple={false}
>
    <p class="drop-text">Drop a plan here or click to upload</p>
    {#if fileTooLarge}
        <h4 class="error-message">
            File is larger than {MAX_SIZE_MB}MB, please try again with a smaller file
        </h4>
    {:else if rejectedFileMessage}
        <h4 class="error-message">{rejectedFileMessage}, please try again</h4>
    {:else}
        <small>Accepted files: {ACCEPTED_FILE_EXTENSIONS.join(", ").replaceAll(".", "")}</small>
        <small>Max size: {MAX_SIZE_MB}MB</small>
        <small>Optimal scale: {OPTIMAL_SCALE}px/m</small>
    {/if}
</Dropzone>

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

    .error-message {
        text-decoration: underline;
    }
</style>
