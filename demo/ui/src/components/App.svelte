<script lang="ts">
    import * as Sentry from "@sentry/browser";
    import { onMount } from "svelte";
    import FileDropzone from "./FileDropzone.svelte";
    import Sidebar from "./Sidebar.svelte";
    import { localUrlToBlob, uploadPlan } from "../utils";
    import { UploadStatus } from "../types";
    import { auth } from "../providers";
    import {
        authError,
        processedWalls,
        processedIcons,
        processedSpaces,
        processedBackground,
        processedStats,
    } from "../stores";
    import InitialInfo from "./InitialInfo.svelte";
    import Snackbar from "./Snackbar.svelte";
    import FloorplanImages from "./FloorplanImages.svelte";
    import SignupModal from "./SignupModal.svelte";
    import StatsCharts from "./StatsCharts.svelte";
    import LoadingProgress from "./LoadingProgress.svelte";
    import { UNAUTHENTICATED } from "../constants";

    const CANCELLED_REQUEST_ERROR = "ERR_CANCELED";

    let original;
    let isAuthenticated = false;
    let uploadStatus: UploadStatus | "" = "";
    let modalToSignup = false;
    let fileToUploadAfterAuth = null;

    let isDisplayingAPlan = false;

    $: isDisplayingAPlan = original || uploadStatus === UploadStatus.SUCCESS;

    let preloadedPlans: string[] = Object.values(
        import.meta.glob(["../assets/preloaded-plans/*.jpg", "../assets/preloaded-plans/*.png"], {
            eager: true,
            import: "default",
        })
    );

    onMount(async () => {
        isAuthenticated = await auth.authenticate();
        if (isAuthenticated) {
            const user = await auth.getUser();
            Sentry.setUser({ email: user?.email });
        } else {
            Sentry.setUser({ email: UNAUTHENTICATED });
        }
    });

    const onSelectFile = async (fileToUpload) => {
        // To avoid stale closure we use provider function
        isAuthenticated = await auth.isAuthenticated();
        if (isAuthenticated) {
            modalToSignup = false;
            await processAndUploadPlan(fileToUpload);
        } else {
            fileToUploadAfterAuth = fileToUpload;
            modalToSignup = true;
        }
    };

    const processAndUploadPlan = async (fileToUpload: File) => {
        try {
            $processedWalls = null;
            $processedIcons = null;
            $processedSpaces = null;
            $processedBackground = null;
            $processedStats = null;

            uploadStatus = UploadStatus.LOADING;
            original = URL.createObjectURL(fileToUpload);

            await uploadPlan(fileToUpload);

            uploadStatus = UploadStatus.SUCCESS;
        } catch (error) {
            if (error.code === CANCELLED_REQUEST_ERROR) {
                console.debug("A new upload has begun, previous one has been cancelled.");
                return;
            }
            uploadStatus = UploadStatus.FAILED;
            console.error("Error uploading the file", error);
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
        $processedStats = null;
    };

    const authenticateAndContinueUpload = async (authFn: "signup" | "login") => {
        await auth[authFn]({ usePopup: true });
        isAuthenticated = await auth.isAuthenticated();
        if (isAuthenticated) {
            modalToSignup = false;
            processAndUploadPlan(fileToUploadAfterAuth);
        }
    };
</script>

<main class="main">
    <Sidebar {isAuthenticated} {onClickReset} />
    <div class={"plan-area"}>
        {#if isDisplayingAPlan}
            <div class={`results ${$processedStats ? "finished" : ""}`}>
                <FloorplanImages {original} {uploadStatus} />
                {#if $processedStats}
                    <StatsCharts stats={$processedStats} />
                {:else if uploadStatus !== UploadStatus.FAILED}
                    <LoadingProgress />
                {/if}
            </div>
        {:else}
            <h2>Archilyse Auto-Annotation</h2>
            <InitialInfo {preloadedPlans} onClickExample={onLoadPreloadedPlan} onDropExample={onLoadPreloadedPlan} />
            <FileDropzone {uploadStatus} {onSelectFile} />
        {/if}
        {#if modalToSignup}
            <SignupModal
                onClose={() => (modalToSignup = false)}
                onPopupSignup={() => authenticateAndContinueUpload("signup")}
                onPopupLogin={() => authenticateAndContinueUpload("login")}
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
