<script lang="ts">
    import { onDestroy } from "svelte";

    // Adapted from: https://svelte.dev/examples/modal

    let modal;
    export let onClose;
    export let onPopupSignup;
    export let onPopupLogin;

    const handleKeyDown = (e) => {
        if (e.key === "Escape") {
            onClose();
            return;
        }

        if (e.key === "Tab") {
            // trap focus
            const nodes: HTMLElement[] = modal.querySelectorAll("*");
            const tabbable: HTMLElement[] = Array.from(nodes).filter((n) => n.tabIndex >= 0);

            const activeElement = document?.activeElement as HTMLElement;
            let index = tabbable.indexOf(activeElement);
            if (index === -1 && e.shiftKey) index = 0;

            index += tabbable.length + (e.shiftKey ? -1 : 1);
            index %= tabbable.length;

            tabbable[index].focus();
            e.preventDefault();
        }
    };

    const previously_focused = document?.activeElement as HTMLElement;

    if (previously_focused) {
        onDestroy(() => {
            previously_focused.focus();
        });
    }
</script>

<svelte:window on:keydown={handleKeyDown} />
<div class="modal-background" on:keydown={handleKeyDown} on:click={onClose} />

<div class="modal" role="dialog" aria-modal="true" bind:this={modal}>
    <div class="modal-content">
        <h3>Create an account to upload plans</h3>
        <button class="primary" on:click={onPopupSignup}> Sign up </button>
        <small
            ><p>
                Or <a href={"#"} on:click={onPopupLogin}>Log in</a> to continue
            </p></small
        >
    </div>
</div>

<style>
    .modal-background {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.3);
    }

    .modal {
        position: absolute;
        left: 50%;
        top: 50%;
        width: calc(100vw - 4rem);
        max-width: 30rem;
        transform: translate(-50%, -50%);
    }
    .modal-content {
        background: black;
        padding: 1rem;
        border-radius: 0.2em;

        display: flex;
        flex-direction: column;
        justify-content: space-around;
        align-items: center;
    }

    @media only screen and (max-width: 600px) {
        .modal {
            width: initial;
        }
        .modal-content {
            padding: 2rem;
        }
    }
</style>
