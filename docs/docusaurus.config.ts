import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Smart Mobility Platform',
  tagline: 'Enterprise-Grade Ride-Hailing Platform — 2-Year Learning Curriculum',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://enterprise-platform.example.com',
  baseUrl: '/',

  organizationName: 'Agi-Learning',
  projectName: 'EnterprisePlatform',

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/Agi-Learning/EnterprisePlatform/tree/main/docs/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Smart Mobility Platform',
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'learningSidebar',
          position: 'left',
          label: 'Learning Path',
        },
        {
          href: 'https://github.com/Agi-Learning/EnterprisePlatform',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Curriculum',
          items: [
            { label: 'Phase 1: Foundation', to: '/docs/phase-1' },
            { label: 'Phase 2: Events', to: '/docs/phase-2' },
            { label: 'Phase 3: Data', to: '/docs/phase-3' },
            { label: 'Phase 4: ML', to: '/docs/phase-4' },
          ],
        },
        {
          title: 'Advanced',
          items: [
            { label: 'Phase 5: DevOps', to: '/docs/phase-5' },
            { label: 'Phase 6: AI', to: '/docs/phase-6' },
            { label: 'Phase 7: Scale', to: '/docs/phase-7' },
            { label: 'Architecture', to: '/docs/architecture' },
          ],
        },
      ],
      copyright: `Smart Mobility & Analytics Platform — Built with Docusaurus`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['python', 'bash', 'sql', 'yaml', 'json', 'typescript'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
