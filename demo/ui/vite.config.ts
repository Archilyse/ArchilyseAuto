import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { resolve } from 'path';

export default defineConfig(({ mode }) => {
  return {
    build: {
      rollupOptions: {
        input: {
          main: resolve(__dirname, 'index.html'),
          502: resolve(__dirname, '502.html'),
          tos: resolve(__dirname, 'tos.html'),
        },
      },
    },
    test: {
      globals: true,
      environment: 'jsdom',
    },
    plugins: [svelte({hot: !process.env.VITEST})],
    envDir: './'
  };
})

