<script lang="ts">
  import { processedWalls, processedIcons, processedSpaces } from "../stores";
  import { Check } from "lucide-svelte";

  let wrappingUp = false;
  $: wrappingUp = Boolean(
    $processedSpaces && $processedWalls && $processedIcons
  );
</script>

<div>
  <div class="status">
    <p>1. Loading spaces...</p>
    {#if $processedSpaces}
      <Check />
    {/if}
  </div>
  <div class="status">
    <p>2. Loading features...</p>
    {#if $processedIcons}
      <Check />
    {/if}
  </div>
  <div class="status">
    <p>3. Loading walls...</p>
    {#if $processedWalls}
      <Check />
    {/if}
  </div>
  {#if wrappingUp}
    <p>Wrapping up...</p>
  {/if}
</div>

<style>
  .status {
    line-height: 10px;
    display: flex;
    align-items: center;
  }
</style>
