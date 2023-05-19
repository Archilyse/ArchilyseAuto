<script lang="ts">
    export let isAuthenticated;

    let showSnackbar = true;
    const closeSnackbar = () => (showSnackbar = false);
</script>

{#if showSnackbar && !isAuthenticated}
    <div class="snackbar">
        By accessing and using this site, you acknowledge and agree to our
        <a href="/tos" target="_blank" rel="noreferrer">terms of service</a>. Click
        <a href={"#"} on:click={closeSnackbar} data-testid="close-tos-snackbar">here</a> to continue.
    </div>
{/if}

<style>
    .snackbar {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: #001;
        color: #fff;
        padding: 1rem;
        text-align: center;
    }

    .snackbar a {
        text-decoration: none;
        color: #fff;
        font-weight: 600;
    }

    .snackbar a:hover {
        text-decoration: underline;
    }
</style>
