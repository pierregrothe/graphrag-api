// @ts-check
// Note: type annotations allow type checking and IDEs autocompletion

const lightCodeTheme = require('prism-react-renderer/themes/github');
const darkCodeTheme = require('prism-react-renderer/themes/dracula');

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'GraphRAG API Documentation',
  tagline: 'Enterprise Knowledge Graph Platform - Build intelligent applications with GraphRAG',
  favicon: 'img/favicon.ico',

  // Set the production url of your site here
  url: 'https://docs.graphrag.com',
  // Set the /<baseUrl>/ pathname under which your site is served
  baseUrl: '/',

  // GitHub pages deployment config
  organizationName: 'pierregrothe',
  projectName: 'graphrag-api',

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  // Even if you don't use internalization, you can use this field to set useful
  // metadata like html lang. For example, if your site is Chinese, you may want
  // to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  markdown: {
    mermaid: true,
  },

  themes: ['@docusaurus/theme-mermaid'],

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          editUrl: 'https://github.com/pierregrothe/graphrag-api/tree/main/docs-platform/',
          showLastUpdateAuthor: true,
          showLastUpdateTime: true,
          remarkPlugins: [],
          rehypePlugins: [],
        },
        blog: {
          showReadingTime: true,
          editUrl: 'https://github.com/pierregrothe/graphrag-api/tree/main/docs-platform/',
          blogTitle: 'GraphRAG API Blog',
          blogDescription: 'Latest updates, tutorials, and insights about GraphRAG API',
          postsPerPage: 10,
          blogSidebarTitle: 'Recent posts',
          blogSidebarCount: 5,
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
        sitemap: {
          changefreq: 'weekly',
          priority: 0.5,
          ignorePatterns: ['/tags/**'],
          filename: 'sitemap.xml',
        },
      }),
    ],
  ],

  plugins: [
    [
      '@docusaurus/plugin-ideal-image',
      {
        quality: 70,
        max: 1030,
        min: 640,
        steps: 2,
        disableInDev: false,
      },
    ],
    [
      '@docusaurus/plugin-content-docs',
      {
        id: 'api',
        path: 'api',
        routeBasePath: 'api',
        sidebarPath: require.resolve('./sidebars-api.js'),
        editUrl: 'https://github.com/pierregrothe/graphrag-api/tree/main/docs-platform/',
        showLastUpdateAuthor: true,
        showLastUpdateTime: true,
      },
    ],
    [
      '@docusaurus/plugin-content-docs',
      {
        id: 'guides',
        path: 'guides',
        routeBasePath: 'guides',
        sidebarPath: require.resolve('./sidebars-guides.js'),
        editUrl: 'https://github.com/pierregrothe/graphrag-api/tree/main/docs-platform/',
      },
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      // Replace with your project's social card
      image: 'img/graphrag-social-card.jpg',

      metadata: [
        {name: 'keywords', content: 'graphrag, api, knowledge graph, ai, machine learning, semantic search'},
        {name: 'description', content: 'Enterprise-grade GraphRAG API for building intelligent knowledge graph applications'},
      ],

      navbar: {
        title: 'GraphRAG API',
        logo: {
          alt: 'GraphRAG API Logo',
          src: 'img/logo.svg',
          srcDark: 'img/logo-dark.svg',
        },
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'tutorialSidebar',
            position: 'left',
            label: 'Documentation',
          },
          {
            to: '/api',
            label: 'API Reference',
            position: 'left',
          },
          {
            to: '/guides',
            label: 'Guides',
            position: 'left',
          },
          {
            to: '/playground',
            label: 'API Playground',
            position: 'left',
          },
          {
            to: '/blog',
            label: 'Blog',
            position: 'left'
          },
          {
            type: 'docsVersionDropdown',
            position: 'right',
            dropdownActiveClassDisabled: true,
          },
          {
            href: 'https://github.com/pierregrothe/graphrag-api',
            label: 'GitHub',
            position: 'right',
          },
          {
            type: 'search',
            position: 'right',
          },
        ],
      },

      footer: {
        style: 'dark',
        links: [
          {
            title: 'Documentation',
            items: [
              {
                label: 'Getting Started',
                to: '/docs/getting-started',
              },
              {
                label: 'API Reference',
                to: '/api',
              },
              {
                label: 'GraphQL Schema',
                to: '/api/graphql',
              },
              {
                label: 'Guides & Tutorials',
                to: '/guides',
              },
            ],
          },
          {
            title: 'Tools',
            items: [
              {
                label: 'API Playground',
                to: '/playground',
              },
              {
                label: 'Postman Collection',
                href: 'https://github.com/pierregrothe/graphrag-api/tree/main/postman',
              },
              {
                label: 'OpenAPI Spec',
                href: '/api/openapi.yaml',
              },
              {
                label: 'GraphQL Playground',
                href: '/playground/graphql',
              },
            ],
          },
          {
            title: 'Community',
            items: [
              {
                label: 'GitHub',
                href: 'https://github.com/pierregrothe/graphrag-api',
              },
              {
                label: 'Discussions',
                href: 'https://github.com/pierregrothe/graphrag-api/discussions',
              },
              {
                label: 'Issues',
                href: 'https://github.com/pierregrothe/graphrag-api/issues',
              },
              {
                label: 'Twitter',
                href: 'https://twitter.com/pierregrothe',
              },
            ],
          },
          {
            title: 'Support',
            items: [
              {
                label: 'Enterprise Support',
                href: 'mailto:enterprise@graphrag.com',
              },
              {
                label: 'Community Support',
                href: 'https://github.com/pierregrothe/graphrag-api/discussions',
              },
              {
                label: 'Status Page',
                href: 'https://status.graphrag.com',
              },
              {
                label: 'Contact',
                href: 'mailto:pierre@grothe.ca',
              },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Pierre Grothé. Built with Docusaurus.`,
      },

      prism: {
        theme: lightCodeTheme,
        darkTheme: darkCodeTheme,
        additionalLanguages: ['bash', 'json', 'yaml', 'graphql', 'python', 'javascript', 'typescript'],
      },

      algolia: {
        appId: 'YOUR_APP_ID',
        apiKey: 'YOUR_SEARCH_API_KEY',
        indexName: 'graphrag-api-docs',
        contextualSearch: true,
        searchParameters: {},
        searchPagePath: 'search',
      },

      colorMode: {
        defaultMode: 'light',
        disableSwitch: false,
        respectPrefersColorScheme: true,
      },

      announcementBar: {
        id: 'announcement-bar',
        content:
          '🎉 GraphRAG API v1.0 is now production ready! <a target="_blank" rel="noopener noreferrer" href="/docs/getting-started">Get started</a> in 30 minutes.',
        backgroundColor: '#20232a',
        textColor: '#fff',
        isCloseable: true,
      },

      docs: {
        sidebar: {
          hideable: true,
          autoCollapseCategories: true,
        },
      },

      tableOfContents: {
        minHeadingLevel: 2,
        maxHeadingLevel: 5,
      },
    }),
};

module.exports = config;
