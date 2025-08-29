import React, { useState, useEffect } from 'react';
import { GraphQLPlayground } from 'graphql-playground-react';
import { buildSchema, introspectionFromSchema, getIntrospectionQuery } from 'graphql';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { Copy, Play, Settings, Book, Zap } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';
import axios from 'axios';

interface GraphQLPlaygroundProps {
  endpoint?: string;
  subscriptionEndpoint?: string;
  schema?: string;
  defaultQuery?: string;
  examples?: QueryExample[];
}

interface QueryExample {
  name: string;
  description: string;
  query: string;
  variables?: Record<string, any>;
  category: 'query' | 'mutation' | 'subscription';
}

const defaultExamples: QueryExample[] = [
  {
    name: 'Get Entities',
    description: 'Retrieve entities with pagination',
    category: 'query',
    query: `query GetEntities($first: Int, $after: String) {
  entities(first: $first, after: $after) {
    edges {
      node {
        id
        title
        type
        description
        degree
        communityIds
      }
      cursor
    }
    pageInfo {
      hasNextPage
      hasPreviousPage
      startCursor
      endCursor
    }
    totalCount
  }
}`,
    variables: {
      first: 10,
      after: null
    }
  },
  {
    name: 'Entity with Relationships',
    description: 'Get entity details including relationships',
    category: 'query',
    query: `query GetEntityWithRelationships($id: String!) {
  entity(id: $id) {
    id
    title
    type
    description
    relationships {
      id
      source
      target
      type
      weight
      description
    }
  }
}`,
    variables: {
      id: "entity_123"
    }
  },
  {
    name: 'Semantic Search',
    description: 'Search entities and relationships semantically',
    category: 'query',
    query: `query SemanticSearch($query: String!, $limit: Int) {
  search(query: $query, limit: $limit) {
    entities {
      id
      title
      type
      description
    }
    relationships {
      id
      source
      target
      type
    }
    score
  }
}`,
    variables: {
      query: "artificial intelligence",
      limit: 5
    }
  },
  {
    name: 'Create Workspace',
    description: 'Create a new workspace',
    category: 'mutation',
    query: `mutation CreateWorkspace($name: String!, $description: String) {
  createWorkspace(name: $name, description: $description) {
    id
    name
    description
    status
    createdAt
  }
}`,
    variables: {
      name: "My Workspace",
      description: "A new workspace for testing"
    }
  },
  {
    name: 'Entity Updates',
    description: 'Subscribe to real-time entity updates',
    category: 'subscription',
    query: `subscription EntityUpdates($workspaceId: String) {
  entityUpdates(workspaceId: $workspaceId) {
    id
    title
    type
    action
  }
}`,
    variables: {
      workspaceId: "workspace_123"
    }
  },
  {
    name: 'Performance Metrics',
    description: 'Subscribe to real-time performance updates',
    category: 'subscription',
    query: `subscription PerformanceUpdates {
  performanceUpdates {
    timestamp
    cpuUsagePercent
    memoryUsageMb
    requestsPerSecond
    cacheHitRate
  }
}`
  }
];

const GraphQLPlaygroundComponent: React.FC<GraphQLPlaygroundProps> = ({
  endpoint = 'http://localhost:8000/graphql',
  subscriptionEndpoint = 'ws://localhost:8000/graphql',
  schema,
  defaultQuery,
  examples = defaultExamples
}) => {
  const [authToken, setAuthToken] = useState('');
  const [authType, setAuthType] = useState<'jwt' | 'apikey'>('jwt');
  const [selectedExample, setSelectedExample] = useState<QueryExample | null>(null);
  const [introspectionResult, setIntrospectionResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch schema introspection
  useEffect(() => {
    const fetchIntrospection = async () => {
      if (schema) {
        try {
          const builtSchema = buildSchema(schema);
          const introspection = introspectionFromSchema(builtSchema);
          setIntrospectionResult(introspection);
        } catch (err) {
          console.error('Error building schema:', err);
        }
      } else {
        // Fetch introspection from endpoint
        try {
          setLoading(true);
          const headers: Record<string, string> = {
            'Content-Type': 'application/json',
          };

          if (authToken) {
            if (authType === 'jwt') {
              headers['Authorization'] = `Bearer ${authToken}`;
            } else {
              headers['X-API-Key'] = authToken;
            }
          }

          const response = await axios.post(endpoint, {
            query: getIntrospectionQuery()
          }, { headers });

          setIntrospectionResult(response.data.data);
        } catch (err: any) {
          setError(err.message);
        } finally {
          setLoading(false);
        }
      }
    };

    fetchIntrospection();
  }, [endpoint, schema, authToken, authType]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const getPlaygroundConfig = () => {
    const headers: Record<string, string> = {};
    
    if (authToken) {
      if (authType === 'jwt') {
        headers['Authorization'] = `Bearer ${authToken}`;
      } else {
        headers['X-API-Key'] = authToken;
      }
    }

    return {
      endpoint,
      subscriptionEndpoint,
      headers,
      introspection: introspectionResult,
      settings: {
        'general.betaUpdates': false,
        'editor.theme': 'dark',
        'editor.cursorShape': 'line',
        'editor.fontSize': 14,
        'editor.fontFamily': '"Source Code Pro", "Consolas", "Inconsolata", "Droid Sans Mono", "Monaco", monospace',
        'request.credentials': 'omit',
        'tracing.hideTracingResponse': true,
      },
      tabs: [
        {
          endpoint,
          query: selectedExample?.query || defaultQuery || `# Welcome to GraphRAG API GraphQL Playground
# 
# GraphQL is a query language for APIs and a runtime for fulfilling those queries with your existing data.
# GraphQL provides a complete and understandable description of the data in your API,
# gives clients the power to ask for exactly what they need and nothing more,
# makes it easier to evolve APIs over time, and enables powerful developer tools.
#
# To explore the schema, click on the "Schema" tab on the right.
# To run a query, type it in this editor and click the play button.
#
# Here's a simple query to get started:

query GetEntities {
  entities(first: 5) {
    edges {
      node {
        id
        title
        type
      }
    }
  }
}`,
          variables: selectedExample?.variables ? JSON.stringify(selectedExample.variables, null, 2) : undefined,
          responses: [],
          headers,
        },
      ],
    };
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'query': return 'bg-green-100 text-green-800';
      case 'mutation': return 'bg-blue-100 text-blue-800';
      case 'subscription': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="graphql-playground">
      <Tabs defaultValue="playground" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="playground" className="flex items-center gap-2">
            <Play className="w-4 h-4" />
            Playground
          </TabsTrigger>
          <TabsTrigger value="examples" className="flex items-center gap-2">
            <Book className="w-4 h-4" />
            Examples
          </TabsTrigger>
          <TabsTrigger value="settings" className="flex items-center gap-2">
            <Settings className="w-4 h-4" />
            Settings
          </TabsTrigger>
        </TabsList>

        <TabsContent value="playground" className="space-y-6">
          {/* Authentication */}
          <Card>
            <CardHeader>
              <CardTitle>Authentication</CardTitle>
              <CardDescription>
                Configure authentication for GraphQL requests
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4">
                <Select value={authType} onValueChange={(value: 'jwt' | 'apikey') => setAuthType(value)}>
                  <SelectTrigger className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="jwt">JWT Token</SelectItem>
                    <SelectItem value="apikey">API Key</SelectItem>
                  </SelectContent>
                </Select>
                <Input
                  placeholder={authType === 'jwt' ? 'Enter JWT token' : 'Enter API key'}
                  value={authToken}
                  onChange={(e) => setAuthToken(e.target.value)}
                  className="flex-1"
                  type="password"
                />
              </div>
            </CardContent>
          </Card>

          {/* Error Display */}
          {error && (
            <Alert>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* GraphQL Playground */}
          {!loading && introspectionResult && (
            <div className="h-screen">
              <GraphQLPlayground
                config={getPlaygroundConfig()}
                createApolloLink={() => null}
              />
            </div>
          )}

          {loading && (
            <Card>
              <CardContent className="flex items-center justify-center h-64">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                  <p>Loading GraphQL schema...</p>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="examples" className="space-y-6">
          <div className="grid gap-4">
            {examples.map((example, index) => (
              <Card key={index} className="cursor-pointer hover:shadow-md transition-shadow">
                <CardHeader 
                  className="pb-3"
                  onClick={() => setSelectedExample(example)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <CardTitle className="text-lg">{example.name}</CardTitle>
                      <Badge className={getCategoryColor(example.category)}>
                        {example.category}
                      </Badge>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          copyToClipboard(example.query);
                        }}
                        className="flex items-center gap-2"
                      >
                        <Copy className="w-4 h-4" />
                        Copy
                      </Button>
                      <Button
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedExample(example);
                        }}
                        className="flex items-center gap-2"
                      >
                        <Zap className="w-4 h-4" />
                        Use
                      </Button>
                    </div>
                  </div>
                  <CardDescription>{example.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <SyntaxHighlighter
                    language="graphql"
                    style={tomorrow}
                    className="rounded-md text-sm"
                    customStyle={{ margin: 0 }}
                  >
                    {example.query}
                  </SyntaxHighlighter>
                  {example.variables && (
                    <div className="mt-4">
                      <h4 className="text-sm font-medium mb-2">Variables:</h4>
                      <SyntaxHighlighter
                        language="json"
                        style={tomorrow}
                        className="rounded-md text-sm"
                        customStyle={{ margin: 0 }}
                      >
                        {JSON.stringify(example.variables, null, 2)}
                      </SyntaxHighlighter>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="settings" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>GraphQL Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">GraphQL Endpoint</label>
                <Input
                  value={endpoint}
                  readOnly
                  className="bg-gray-50"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Subscription Endpoint</label>
                <Input
                  value={subscriptionEndpoint}
                  readOnly
                  className="bg-gray-50"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Features</label>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-green-100 text-green-800">✓ Queries</Badge>
                    <span className="text-sm">Execute GraphQL queries</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-green-100 text-green-800">✓ Mutations</Badge>
                    <span className="text-sm">Execute GraphQL mutations</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-green-100 text-green-800">✓ Subscriptions</Badge>
                    <span className="text-sm">Real-time GraphQL subscriptions</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-green-100 text-green-800">✓ Schema Introspection</Badge>
                    <span className="text-sm">Explore the GraphQL schema</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-green-100 text-green-800">✓ Query Validation</Badge>
                    <span className="text-sm">Real-time query validation</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Quick Tips</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="text-sm space-y-2">
                <p><strong>Ctrl/Cmd + Enter:</strong> Execute query</p>
                <p><strong>Ctrl/Cmd + Space:</strong> Trigger autocomplete</p>
                <p><strong>Ctrl/Cmd + /:</strong> Comment/uncomment lines</p>
                <p><strong>Alt + Click:</strong> Multi-cursor editing</p>
                <p><strong>Ctrl/Cmd + F:</strong> Find in query</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default GraphQLPlaygroundComponent;
