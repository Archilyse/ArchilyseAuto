<script lang="ts">
    import { fade } from "svelte/transition";
    import { UploadStatus } from "../types";
    import { beforeUpdate } from "svelte";
    import { processedWalls, processedIcons, processedSpaces, processedBackground } from "../stores";

    export let original;
    export let uploadStatus;

    const OPACITY = 0.5;
    const STILL_LOADING_MS = 20 * 1000;

    let processedImgClass;
    let stillLoading;
    $: processedImgClass = `processed-img ${uploadStatus !== UploadStatus.SUCCESS ? "blur" : ""}`;

    const getSVGContents = (url) => {
        return fetch(url)
            .then((response) => response.text())
            .then((svgString) => {
                let domParser = new DOMParser();
                let svgDOM = domParser.parseFromString(svgString, "text/xml").getElementsByTagName("svg")[0];
                return svgDOM.innerHTML;
            });
    };

    const downloadProcessedPlan = () => {
        Promise.all([
            getSVGContents($processedBackground),
            getSVGContents($processedSpaces),
            getSVGContents($processedWalls),
            getSVGContents($processedIcons),
        ])
            .then((results) => {
                const combinedSvg = `<svg xmlns="http://www.w3.org/2000/svg">
                              ${results[0]}
                              ${results[1]}
                              ${results[2]}
                              ${results[3]}
                           </svg>`;
                const blob = new Blob([combinedSvg], { type: "image/svg+xml" });
                const link = document.createElement("a");
                link.href = URL.createObjectURL(blob);
                link.download = "processedFloorPlan.svg";
                link.click();
            })
            .catch((error) => {
                console.error(error);
            });
    };

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
        <img class="original" src={original} alt="Preview of the uploaded plan without processing" />
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
        {#if uploadStatus === UploadStatus.SUCCESS}
            <div class="download-results">
                <button class="download-button" on:click={downloadProcessedPlan}> Download result </button>
            </div>
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
            <p class="loading-text">Error uploading the file! Please try again in a few minutes or contact us.</p>
        {/if}
    </div>
{/if}

<style>
    .floorplan-images {
        display: grid;
        grid-template-columns: [first-col] minmax(0, 1fr);
        grid-template-rows: [first-row] minmax(0, 1fr);
        height: 100%;
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
        -webkit-animation: slide-in-left 120s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
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

    .download-results {
        margin-top: 30px;
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        height: 10%;
        background-color: #343541;
    }
    .download-button {
        background-color: transparent;
        color: #ddd;
        border: 1px solid #50515d;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        padding: 15px 35px;
        transition: background-color 0.25s ease;
    }
    .download-button:hover {
        background-color: #444654;
    }
    .download-button:focus {
        outline: none;
        box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.5);
    }
</style>
