/**
 * API Reference sidebar configuration
 */

// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  apiSidebar: [
    'overview',
    {
      type: 'category',
      label: 'Authentication',
      collapsed: false,
      items: [
        'authentication/overview',
        'authentication/jwt-authentication',
        'authentication/api-key-authentication',
        'authentication/examples',
      ],
    },
    {
      type: 'category',
      label: 'REST API',
      collapsed: false,
      items: [
        'rest/overview',
        {
          type: 'category',
          label: 'Health & System',
          items: [
            'rest/health/basic-health',
            'rest/health/detailed-health',
            'rest/health/metrics',
          ],
        },
        {
          type: 'category',
          label: 'Authentication Endpoints',
          items: [
            'rest/auth/login',
            'rest/auth/refresh-token',
            'rest/auth/api-keys',
            'rest/auth/logout',
          ],
        },
        {
          type: 'category',
          label: 'Workspaces',
          items: [
            'rest/workspaces/list-workspaces',
            'rest/workspaces/create-workspace',
            'rest/workspaces/get-workspace',
            'rest/workspaces/update-workspace',
            'rest/workspaces/delete-workspace',
          ],
        },
        {
          type: 'category',
          label: 'Entities',
          items: [
            'rest/entities/list-entities',
            'rest/entities/get-entity',
            'rest/entities/create-entity',
            'rest/entities/update-entity',
            'rest/entities/delete-entity',
            'rest/entities/search-entities',
            'rest/entities/entity-statistics',
          ],
        },
        {
          type: 'category',
          label: 'Relationships',
          items: [
            'rest/relationships/list-relationships',
            'rest/relationships/get-relationship',
            'rest/relationships/create-relationship',
            'rest/relationships/update-relationship',
            'rest/relationships/delete-relationship',
            'rest/relationships/relationship-statistics',
          ],
        },
        {
          type: 'category',
          label: 'Graph Operations',
          items: [
            'rest/graph/semantic-search',
            'rest/graph/multi-hop-query',
            'rest/graph/centrality-analysis',
            'rest/graph/path-finding',
            'rest/graph/graph-statistics',
          ],
        },
        {
          type: 'category',
          label: 'Communities',
          items: [
            'rest/communities/list-communities',
            'rest/communities/get-community',
            'rest/communities/detect-communities',
            'rest/communities/community-analysis',
          ],
        },
        {
          type: 'category',
          label: 'Indexing',
          items: [
            'rest/indexing/start-indexing',
            'rest/indexing/indexing-status',
            'rest/indexing/indexing-logs',
            'rest/indexing/cancel-indexing',
          ],
        },
        {
          type: 'category',
          label: 'Monitoring',
          items: [
            'rest/monitoring/prometheus-metrics',
            'rest/monitoring/performance-metrics',
            'rest/monitoring/cache-metrics',
            'rest/monitoring/system-metrics',
          ],
        },
      ],
    },
    {
      type: 'category',
      label: 'GraphQL API',
      collapsed: false,
      items: [
        'graphql/overview',
        'graphql/schema',
        'graphql/playground',
        {
          type: 'category',
          label: 'Queries',
          items: [
            'graphql/queries/entities',
            'graphql/queries/relationships',
            'graphql/queries/communities',
            'graphql/queries/search',
            'graphql/queries/graph-analysis',
            'graphql/queries/system-info',
          ],
        },
        {
          type: 'category',
          label: 'Mutations',
          items: [
            'graphql/mutations/workspace-management',
            'graphql/mutations/entity-management',
            'graphql/mutations/relationship-management',
            'graphql/mutations/indexing-operations',
            'graphql/mutations/cache-management',
          ],
        },
        {
          type: 'category',
          label: 'Subscriptions',
          items: [
            'graphql/subscriptions/overview',
            'graphql/subscriptions/entity-updates',
            'graphql/subscriptions/indexing-updates',
            'graphql/subscriptions/performance-updates',
            'graphql/subscriptions/system-events',
          ],
        },
        {
          type: 'category',
          label: 'Advanced Features',
          items: [
            'graphql/advanced/field-selection',
            'graphql/advanced/query-complexity',
            'graphql/advanced/pagination',
            'graphql/advanced/fragments',
            'graphql/advanced/variables',
            'graphql/advanced/directives',
          ],
        },
      ],
    },
    {
      type: 'category',
      label: 'WebSocket API',
      collapsed: true,
      items: [
        'websocket/overview',
        'websocket/connection',
        'websocket/authentication',
        'websocket/subscriptions',
        'websocket/error-handling',
      ],
    },
    {
      type: 'category',
      label: 'Error Codes',
      collapsed: true,
      items: [
        'errors/overview',
        'errors/http-status-codes',
        'errors/authentication-errors',
        'errors/validation-errors',
        'errors/rate-limiting-errors',
        'errors/server-errors',
        'errors/graphql-errors',
      ],
    },
    {
      type: 'category',
      label: 'Rate Limiting',
      collapsed: true,
      items: [
        'rate-limiting/overview',
        'rate-limiting/limits',
        'rate-limiting/headers',
        'rate-limiting/handling',
      ],
    },
    {
      type: 'category',
      label: 'Webhooks',
      collapsed: true,
      items: [
        'webhooks/overview',
        'webhooks/setup',
        'webhooks/events',
        'webhooks/security',
        'webhooks/testing',
      ],
    },
    {
      type: 'category',
      label: 'OpenAPI Specification',
      collapsed: true,
      items: [
        'openapi/overview',
        'openapi/download',
        'openapi/validation',
        'openapi/code-generation',
      ],
    },
  ],
};

module.exports = sidebars;
