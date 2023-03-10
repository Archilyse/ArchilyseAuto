<script lang="ts">
  export let onClickReset;

  const onClickTryAgain = (event) => {
    event.preventDefault();
    onClickReset();
  };
</script>

<div class="auth-error">
  <p>
    Error trying to authenticate! Please <a href="/" on:click={onClickTryAgain}
      >try again
    </a>or contact support if the situation persists.
  </p>
</div>

<style>
  .auth-error {
    height: 100%;
    width: 100%;

    display: flex;
    justify-content: center;
    align-items: center;
    flex-direction: column;
  }
</style>
