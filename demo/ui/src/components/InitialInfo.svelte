<script lang="ts">
    import { Sun, Zap, AlertTriangle } from "lucide-svelte";
    import getRandomizedPreloadedPlans from "../utils/getRandomizedPreloadedPlans";

    export let preloadedPlans;
    export let onClickExample;
    export let onDropExample;
</script>

<div class="info-columns">
    <div class="section plan-samples">
        <h3 class="section-title">
            <Sun />
            Examples
        </h3>
        <ul>
            {#each getRandomizedPreloadedPlans(preloadedPlans) as plan, index}
                <li class="plan-sample">
                    <img
                        src={plan}
                        alt={"Thumbnail of plan"}
                        on:click={() => onClickExample(plan)}
                        on:keypress={() => onClickExample(plan)}
                        draggable={true}
                        on:dragend={() => onDropExample(plan)}
                    />
                </li>
            {/each}
        </ul>
    </div>

    <div class="section">
        <h3 class="section-title">
            <Zap />
            Capabilities
        </h3>
        <ul>
            <li>Automatically annotate elements of floor plans</li>
            <li>Identify region of interest on the documents</li>
            <li>Basic analysis of element footprint distribution</li>
        </ul>
    </div>

    <div class="section limitations">
        <h3 class="section-title">
            <AlertTriangle />
            Limitations
        </h3>
        <ul>
            <li>May occasionally generate incorrect output</li>
            <li>Ideal plan scale is 40px per meter</li>
            <li>Larger plans take longer to complete</li>
        </ul>
    </div>
</div>

<style>
    .info-columns {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        width: var(--plan-area-width-taken);
    }

    .info-columns ul {
        list-style: none;
        padding: 0;
    }
    .info-columns li {
        padding: 0.75em;
        margin: 0.5em;
        background-color: hsla(0, 0%, 100%, 0.05);
        border-radius: 0.375em;

        height: 2em;
        display: flex;
        justify-content: center;
        align-items: center;
        text-align: center;
    }

    .section {
        display: flex;
        flex-direction: column;
        align-items: center;
        line-height: 1.25em;
    }

    .section-title {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1.5em;
    }

    .plan-sample {
        display: flex;
        align-items: center;
        justify-content: space-around;
    }

    .plan-sample img {
        cursor: pointer;
        width: 250px;
        height: 50px;
        object-fit: cover;
    }

    .section.plan-samples {
        justify-self: start;
    }
    .section.limitations {
        justify-self: end;
    }

    @media only screen and (max-width: 900px) {
        .info-columns {
            display: flex;
            flex-direction: column;
            overflow-y: scroll;
        }
        .info-columns li {
            height: inherit !important;
        }
    }
</style>
