import React, { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { Copy, Play, Settings, Eye, Code } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';
import axios from 'axios';

interface ApiExplorerProps {
  endpoint: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  description: string;
  parameters?: Parameter[];
  requestBody?: RequestBodySchema;
  responses?: ResponseSchema[];
  examples?: CodeExample[];
}

interface Parameter {
  name: string;
  type: string;
  required: boolean;
  description: string;
  example?: any;
  enum?: string[];
}

interface RequestBodySchema {
  type: string;
  properties: Record<string, any>;
  required?: string[];
  example?: any;
}

interface ResponseSchema {
  status: number;
  description: string;
  schema?: any;
  example?: any;
}

interface CodeExample {
  language: string;
  label: string;
  code: string;
}

const ApiExplorer: React.FC<ApiExplorerProps> = ({
  endpoint,
  method,
  description,
  parameters = [],
  requestBody,
  responses = [],
  examples = []
}) => {
  const [baseUrl, setBaseUrl] = useState('http://localhost:8000');
  const [authToken, setAuthToken] = useState('');
  const [authType, setAuthType] = useState<'jwt' | 'apikey'>('jwt');
  const [paramValues, setParamValues] = useState<Record<string, any>>({});
  const [requestBodyValue, setRequestBodyValue] = useState('');
  const [response, setResponse] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize parameter values with examples
  useEffect(() => {
    const initialValues: Record<string, any> = {};
    parameters.forEach(param => {
      if (param.example !== undefined) {
        initialValues[param.name] = param.example;
      }
    });
    setParamValues(initialValues);

    // Initialize request body with example
    if (requestBody?.example) {
      setRequestBodyValue(JSON.stringify(requestBody.example, null, 2));
    }
  }, [parameters, requestBody]);

  const handleParameterChange = (paramName: string, value: any) => {
    setParamValues(prev => ({
      ...prev,
      [paramName]: value
    }));
  };

  const executeRequest = async () => {
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      // Build URL with parameters
      let url = `${baseUrl}${endpoint}`;
      const queryParams = new URLSearchParams();

      parameters.forEach(param => {
        if (param.name in paramValues && paramValues[param.name] !== '') {
          if (endpoint.includes(`{${param.name}}`)) {
            // Path parameter
            url = url.replace(`{${param.name}}`, encodeURIComponent(paramValues[param.name]));
          } else {
            // Query parameter
            queryParams.append(param.name, paramValues[param.name]);
          }
        }
      });

      if (queryParams.toString()) {
        url += `?${queryParams.toString()}`;
      }

      // Prepare headers
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

      // Prepare request config
      const config: any = {
        method: method.toLowerCase(),
        url,
        headers,
      };

      // Add request body for POST/PUT/PATCH
      if (['POST', 'PUT', 'PATCH'].includes(method) && requestBodyValue) {
        try {
          config.data = JSON.parse(requestBodyValue);
        } catch (e) {
          throw new Error('Invalid JSON in request body');
        }
      }

      const result = await axios(config);
      setResponse({
        status: result.status,
        statusText: result.statusText,
        headers: result.headers,
        data: result.data,
      });
    } catch (err: any) {
      setError(err.response?.data?.message || err.message || 'Request failed');
      if (err.response) {
        setResponse({
          status: err.response.status,
          statusText: err.response.statusText,
          headers: err.response.headers,
          data: err.response.data,
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const generateCurlCommand = () => {
    let url = `${baseUrl}${endpoint}`;
    const queryParams = new URLSearchParams();

    parameters.forEach(param => {
      if (param.name in paramValues && paramValues[param.name] !== '') {
        if (endpoint.includes(`{${param.name}}`)) {
          url = url.replace(`{${param.name}}`, encodeURIComponent(paramValues[param.name]));
        } else {
          queryParams.append(param.name, paramValues[param.name]);
        }
      }
    });

    if (queryParams.toString()) {
      url += `?${queryParams.toString()}`;
    }

    let curl = `curl -X ${method} "${url}"`;

    if (authToken) {
      if (authType === 'jwt') {
        curl += ` \\\n  -H "Authorization: Bearer ${authToken}"`;
      } else {
        curl += ` \\\n  -H "X-API-Key: ${authToken}"`;
      }
    }

    curl += ` \\\n  -H "Content-Type: application/json"`;

    if (['POST', 'PUT', 'PATCH'].includes(method) && requestBodyValue) {
      curl += ` \\\n  -d '${requestBodyValue}'`;
    }

    return curl;
  };

  const getMethodColor = (method: string) => {
    switch (method) {
      case 'GET': return 'bg-green-100 text-green-800';
      case 'POST': return 'bg-blue-100 text-blue-800';
      case 'PUT': return 'bg-yellow-100 text-yellow-800';
      case 'DELETE': return 'bg-red-100 text-red-800';
      case 'PATCH': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="api-explorer">
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center gap-3">
            <Badge className={getMethodColor(method)}>{method}</Badge>
            <code className="text-lg font-mono">{endpoint}</code>
          </div>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
      </Card>

      <Tabs defaultValue="try-it" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="try-it" className="flex items-center gap-2">
            <Play className="w-4 h-4" />
            Try It Out
          </TabsTrigger>
          <TabsTrigger value="examples" className="flex items-center gap-2">
            <Code className="w-4 h-4" />
            Code Examples
          </TabsTrigger>
          <TabsTrigger value="schema" className="flex items-center gap-2">
            <Eye className="w-4 h-4" />
            Schema
          </TabsTrigger>
          <TabsTrigger value="settings" className="flex items-center gap-2">
            <Settings className="w-4 h-4" />
            Settings
          </TabsTrigger>
        </TabsList>

        <TabsContent value="try-it" className="space-y-6">
          {/* Authentication */}
          <Card>
            <CardHeader>
              <CardTitle>Authentication</CardTitle>
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

          {/* Parameters */}
          {parameters.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Parameters</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {parameters.map((param) => (
                  <div key={param.name} className="space-y-2">
                    <label className="flex items-center gap-2 text-sm font-medium">
                      {param.name}
                      {param.required && <Badge variant="destructive" className="text-xs">Required</Badge>}
                      <span className="text-gray-500">({param.type})</span>
                    </label>
                    <p className="text-sm text-gray-600">{param.description}</p>
                    {param.enum ? (
                      <Select
                        value={paramValues[param.name] || ''}
                        onValueChange={(value) => handleParameterChange(param.name, value)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select value" />
                        </SelectTrigger>
                        <SelectContent>
                          {param.enum.map((option) => (
                            <SelectItem key={option} value={option}>
                              {option}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        value={paramValues[param.name] || ''}
                        onChange={(e) => handleParameterChange(param.name, e.target.value)}
                        placeholder={param.example ? String(param.example) : `Enter ${param.name}`}
                      />
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Request Body */}
          {requestBody && ['POST', 'PUT', 'PATCH'].includes(method) && (
            <Card>
              <CardHeader>
                <CardTitle>Request Body</CardTitle>
              </CardHeader>
              <CardContent>
                <textarea
                  className="w-full h-40 p-3 border rounded-md font-mono text-sm"
                  value={requestBodyValue}
                  onChange={(e) => setRequestBodyValue(e.target.value)}
                  placeholder="Enter JSON request body"
                />
              </CardContent>
            </Card>
          )}

          {/* Execute Button */}
          <div className="flex gap-4">
            <Button onClick={executeRequest} disabled={loading} className="flex items-center gap-2">
              <Play className="w-4 h-4" />
              {loading ? 'Executing...' : 'Execute Request'}
            </Button>
            <Button
              variant="outline"
              onClick={() => copyToClipboard(generateCurlCommand())}
              className="flex items-center gap-2"
            >
              <Copy className="w-4 h-4" />
              Copy as cURL
            </Button>
          </div>

          {/* Response */}
          {(response || error) && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  Response
                  {response && (
                    <Badge className={response.status < 400 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                      {response.status} {response.statusText}
                    </Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {error && (
                  <Alert className="mb-4">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}
                {response && (
                  <SyntaxHighlighter
                    language="json"
                    style={tomorrow}
                    className="rounded-md"
                  >
                    {JSON.stringify(response.data, null, 2)}
                  </SyntaxHighlighter>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="examples" className="space-y-6">
          {examples.map((example, index) => (
            <Card key={index}>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>{example.label}</CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => copyToClipboard(example.code)}
                  className="flex items-center gap-2"
                >
                  <Copy className="w-4 h-4" />
                  Copy
                </Button>
              </CardHeader>
              <CardContent>
                <SyntaxHighlighter
                  language={example.language}
                  style={tomorrow}
                  className="rounded-md"
                >
                  {example.code}
                </SyntaxHighlighter>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="schema" className="space-y-6">
          {/* Request Schema */}
          {requestBody && (
            <Card>
              <CardHeader>
                <CardTitle>Request Schema</CardTitle>
              </CardHeader>
              <CardContent>
                <SyntaxHighlighter
                  language="json"
                  style={tomorrow}
                  className="rounded-md"
                >
                  {JSON.stringify(requestBody, null, 2)}
                </SyntaxHighlighter>
              </CardContent>
            </Card>
          )}

          {/* Response Schemas */}
          {responses.map((response, index) => (
            <Card key={index}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  Response {response.status}
                  <Badge className={response.status < 400 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                    {response.status}
                  </Badge>
                </CardTitle>
                <CardDescription>{response.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <SyntaxHighlighter
                  language="json"
                  style={tomorrow}
                  className="rounded-md"
                >
                  {JSON.stringify(response.schema || response.example, null, 2)}
                </SyntaxHighlighter>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="settings" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>API Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Base URL</label>
                <Input
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="http://localhost:8000"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default ApiExplorer;
