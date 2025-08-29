/**
 * Creating a sidebar enables you to:
 - create an ordered group of docs
 - render a sidebar for each doc of that group
 - provide next/previous navigation

 The sidebars can be generated from the filesystem, or explicitly defined here.

 Create as many sidebars as you want.
 */

// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  // Main documentation sidebar
  tutorialSidebar: [
    'introduction',
    {
      type: 'category',
      label: 'Getting Started',
      collapsed: false,
      items: [
        'getting-started/quickstart',
        'getting-started/installation',
        'getting-started/authentication',
        'getting-started/first-api-call',
        'getting-started/postman-setup',
      ],
    },
    {
      type: 'category',
      label: 'Core Concepts',
      collapsed: false,
      items: [
        'concepts/knowledge-graphs',
        'concepts/entities-relationships',
        'concepts/semantic-search',
        'concepts/community-detection',
        'concepts/graph-algorithms',
        'concepts/embeddings',
      ],
    },
    {
      type: 'category',
      label: 'Authentication',
      collapsed: true,
      items: [
        'authentication/overview',
        'authentication/jwt-tokens',
        'authentication/api-keys',
        'authentication/permissions',
        'authentication/rate-limiting',
        'authentication/security-best-practices',
      ],
    },
    {
      type: 'category',
      label: 'API Usage',
      collapsed: true,
      items: [
        'api-usage/rest-api',
        'api-usage/graphql-api',
        'api-usage/real-time-subscriptions',
        'api-usage/batch-operations',
        'api-usage/pagination',
        'api-usage/filtering-sorting',
        'api-usage/error-handling',
      ],
    },
    {
      type: 'category',
      label: 'Data Management',
      collapsed: true,
      items: [
        'data-management/workspaces',
        'data-management/document-indexing',
        'data-management/entity-management',
        'data-management/relationship-management',
        'data-management/data-import-export',
        'data-management/backup-recovery',
      ],
    },
    {
      type: 'category',
      label: 'Advanced Features',
      collapsed: true,
      items: [
        'advanced/graph-analytics',
        'advanced/centrality-analysis',
        'advanced/community-detection',
        'advanced/anomaly-detection',
        'advanced/semantic-similarity',
        'advanced/multi-hop-queries',
        'advanced/custom-algorithms',
      ],
    },
    {
      type: 'category',
      label: 'LLM Providers',
      collapsed: true,
      items: [
        'llm-providers/overview',
        'llm-providers/ollama',
        'llm-providers/google-cloud',
        'llm-providers/openai',
        'llm-providers/comparison',
        'llm-providers/custom-providers',
      ],
    },
    {
      type: 'category',
      label: 'Deployment',
      collapsed: true,
      items: [
        'deployment/overview',
        'deployment/docker',
        'deployment/kubernetes',
        'deployment/cloud-providers',
        'deployment/scaling',
        'deployment/load-balancing',
        'deployment/ssl-certificates',
      ],
    },
    {
      type: 'category',
      label: 'Monitoring & Observability',
      collapsed: true,
      items: [
        'monitoring/overview',
        'monitoring/prometheus-metrics',
        'monitoring/grafana-dashboards',
        'monitoring/distributed-tracing',
        'monitoring/logging',
        'monitoring/alerting',
        'monitoring/performance-tuning',
      ],
    },
    {
      type: 'category',
      label: 'Security',
      collapsed: true,
      items: [
        'security/overview',
        'security/authentication',
        'security/authorization',
        'security/data-privacy',
        'security/encryption',
        'security/audit-logging',
        'security/compliance',
      ],
    },
    {
      type: 'category',
      label: 'Performance',
      collapsed: true,
      items: [
        'performance/overview',
        'performance/caching',
        'performance/query-optimization',
        'performance/indexing-optimization',
        'performance/memory-management',
        'performance/benchmarking',
      ],
    },
    {
      type: 'category',
      label: 'Troubleshooting',
      collapsed: true,
      items: [
        'troubleshooting/common-issues',
        'troubleshooting/debugging',
        'troubleshooting/performance-issues',
        'troubleshooting/connection-issues',
        'troubleshooting/authentication-issues',
        'troubleshooting/data-issues',
        'troubleshooting/support',
      ],
    },
    {
      type: 'category',
      label: 'SDKs & Libraries',
      collapsed: true,
      items: [
        'sdks/overview',
        'sdks/python-sdk',
        'sdks/javascript-sdk',
        'sdks/typescript-sdk',
        'sdks/go-sdk',
        'sdks/java-sdk',
        'sdks/community-sdks',
      ],
    },
    {
      type: 'category',
      label: 'Migration & Upgrades',
      collapsed: true,
      items: [
        'migration/overview',
        'migration/version-compatibility',
        'migration/upgrade-guides',
        'migration/breaking-changes',
        'migration/data-migration',
      ],
    },
    {
      type: 'category',
      label: 'Contributing',
      collapsed: true,
      items: [
        'contributing/overview',
        'contributing/development-setup',
        'contributing/code-style',
        'contributing/testing',
        'contributing/documentation',
        'contributing/pull-requests',
      ],
    },
    'changelog',
    'roadmap',
    'faq',
  ],
};

module.exports = sidebars;
