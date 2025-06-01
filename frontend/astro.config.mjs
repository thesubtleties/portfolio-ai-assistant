// @ts-check
import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import react from '@astrojs/react';

// https://astro.build/config
export default defineConfig({
  site: 'https://sbtl.dev',
  base: '/',
  integrations: [tailwind(), react()],
  output: 'static',
  build: {
    assets: '_assets',
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
  },
  vite: {
    ssr: {
      noExternal: ['gsap'],
    },
    optimizeDeps: {
      include: ['gsap', 'gsap/SplitText'],
    },
  },
});
