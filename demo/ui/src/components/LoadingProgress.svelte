<script lang="ts">
    import { processedWalls, processedIcons, processedSpaces } from "../stores";
    import { Check } from "lucide-svelte";

    let wrappingUp = false;
    $: wrappingUp = Boolean($processedSpaces && $processedWalls && $processedIcons);
</script>

<div class="loading-progress">
    <p class="title">Processing steps</p>
    <div class="status">
        <p>1. Spaces...</p>
        {#if $processedSpaces}
            <div class="check-mark">
                <Check size={16} />
            </div>
        {/if}
    </div>
    <div class="status">
        <p>2. Features...</p>
        {#if $processedIcons}
            <div class="check-mark">
                <Check size={16} />
            </div>
        {/if}
    </div>
    <div class="status">
        <p>3. Walls...</p>
        {#if $processedWalls}
            <div class="check-mark">
                <Check size={16} />
            </div>
        {/if}
    </div>
    {#if wrappingUp}
        <p>Wrapping up...</p>
    {/if}
</div>

<style>
    .loading-progress {
        color: rgb(140, 141, 146);
        font-size: 12px;
    }
    .title {
        font-weight: bold;
    }
    .status {
        line-height: 10px;
        display: flex;
        align-items: center;
    }
    .check-mark {
        margin-bottom: 1px;
    }
</style>
