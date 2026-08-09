import svelte from '@astrojs/svelte';
import starlight from '@astrojs/starlight';
import tailwind from '@tailwindcss/vite';
import { defineConfig } from 'astro/config';
import d2 from 'astro-d2';

// A plain Astro page owns the base itself, and Astro gives static routes priority over Starlight's dynamic
// `[...slug]`, so the marketing page wins without a redirect. Starlight has no base option of its
// own, so every docs page is nested one level deeper under `src/content/docs/docs/` to come out
// at `/mcmr/docs/...`, mirroring the trick aizk uses to keep a plain landing page at its root.
export default defineConfig({
  site: 'https://phvv.me',
  base: '/mcmr',
  trailingSlash: 'always',
  vite: { plugins: [tailwind()] },
  integrations: [
    // D2 draws what mermaid draws badly, the pipeline stages and the table shapes. useD2js
    // renders through WebAssembly so no D2 binary has to exist in the build container.
    d2({
      experimental: { useD2js: true },
      layout: 'elk',
      pad: 20,
      theme: { default: '103', dark: '200' },
    }),
    svelte(),
    starlight({
      title: 'mcmr',
      description: 'Define and enforce the engineering rules that make your code yours.',
      logo: { src: './src/assets/icon.svg', alt: 'MCMR' },
      favicon: '/favicon.svg',
      customCss: ['./src/styles/docs.css'],
      social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/phvv-me/mcmr' }],
      sidebar: [
        { label: 'Documentation home', slug: 'docs' },
        {
          label: 'Start here',
          items: [
            { label: 'What MCMR is', slug: 'docs/start/what-is-mcmr' },
            { label: 'Install', slug: 'docs/start/install' },
            { label: 'The demo walkthrough', slug: 'docs/start/demo-walkthrough' },
          ],
        },
        {
          label: 'Concepts',
          items: [
            { label: 'Fact tables', slug: 'docs/concepts/fact-tables' },
            { label: 'Rules and lanes', slug: 'docs/concepts/rules-and-lanes' },
            { label: 'Verified repairs', slug: 'docs/concepts/verified-repairs' },
            { label: 'The rulebook', slug: 'docs/concepts/rulebook' },
            { label: 'Institutional memory', slug: 'docs/concepts/institutional-memory' },
          ],
        },
        {
          label: 'DataHub',
          items: [
            { label: 'Why metadata', slug: 'docs/datahub/why-metadata' },
            { label: 'What gets published', slug: 'docs/datahub/what-gets-published' },
            { label: 'Reading history back', slug: 'docs/datahub/reading-history' },
            { label: 'Cost provenance', slug: 'docs/datahub/cost-provenance' },
            { label: 'Incidents and contracts', slug: 'docs/datahub/incidents-and-contracts' },
          ],
        },
        {
          label: 'Reference',
          items: [
            { label: 'CLI commands', slug: 'docs/reference/cli' },
            { label: 'Configuration keys', slug: 'docs/reference/configuration' },
          ],
        },
      ],
    }),
  ],
});
