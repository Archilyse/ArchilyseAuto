<script lang="ts">
    import discordLogo from "../assets/discordLogo.svg";
    import linkedinLogo from "../assets/linkedinLogo.svg";
    import { LogIn, LogOut, Home } from "lucide-svelte";
    import { auth } from "../providers";
    import { DISCORD_URL, LINKEDIN_URL } from "../constants";

    export let isAuthenticated;
    export let onClickReset;
</script>

<aside class="sidebar">
    {#if !isAuthenticated}
        <button title="Login" class="sidebar-btn" on:click={() => auth.login()}>
            <LogIn />
            <span>Login</span>
        </button>
    {/if}
    <button title="Home" class="sidebar-btn" on:click={onClickReset}>
        <Home />
        <span>Home</span>
    </button>
    <button title="Discuss" class="sidebar-btn" on:click={() => window.open(DISCORD_URL, "_blank")}>
        <img src={discordLogo} alt="Discord logo" width={24} height={24} />
        <span>Discuss</span>
    </button>
    <button title="Follow" class="sidebar-btn" on:click={() => window.open(LINKEDIN_URL, "_blank")}>
        <img src={linkedinLogo} alt="Linkedin logo" width={24} height={24} />
        <span>Follow</span>
    </button>

    {#if isAuthenticated}
        <button
            title="Log out"
            class="sidebar-btn logout-button"
            on:click={() => auth.logout()}
            data-testid="signup-sidebar"
        >
            <LogOut />
            <span>Log out</span>
        </button>
    {/if}
</aside>

<style>
    .sidebar {
        background-color: var(--secondary-bg-color);
        color: white;
        display: flex;
        flex-direction: column;
        justify-content: top;
        align-items: center;
        padding-top: 10px;
        width: 100%;
    }

    .sidebar-btn {
        color: inherit;

        display: flex;
        justify-content: flex-start;

        align-items: center;
        cursor: pointer !important;
        background: transparent;
        border: none;

        padding: 20px;
        width: 100%;
    }
    .sidebar-btn:hover {
        background: rgba(255, 255, 255, 0.05);
    }
    .sidebar-btn > span {
        font-size: 1rem;
        margin-left: 20px;
    }

    @media only screen and (max-width: 600px) {
        /* Layout is flex in mobile, check App.svelte */
        .sidebar {
            display: flex;
            flex-direction: row;
            justify-content: space-evenly;
            align-items: center;
            padding: 10px;
            width: auto;
        }
        .sidebar-btn {
            display: block;
            padding: 0;
        }
        .sidebar-btn span {
            display: none;
        }
    }
</style>
