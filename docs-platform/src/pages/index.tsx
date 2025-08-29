import React from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className="hero__title">
          {siteConfig.title}
        </Heading>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/getting-started/quickstart">
            Get Started in 30 Minutes ⚡
          </Link>
          <Link
            className="button button--outline button--lg margin-left--md"
            to="/playground">
            Try API Playground 🚀
          </Link>
        </div>
        <div className={styles.heroStats}>
          <div className={styles.stat}>
            <div className={styles.statNumber}>100%</div>
            <div className={styles.statLabel}>Feature Parity</div>
            <div className={styles.statDesc}>REST & GraphQL</div>
          </div>
          <div className={styles.stat}>
            <div className={styles.statNumber}>85%+</div>
            <div className={styles.statLabel}>Cache Hit Rate</div>
            <div className={styles.statDesc}>Redis Optimization</div>
          </div>
          <div className={styles.stat}>
            <div className={styles.statNumber}>300ms</div>
            <div className={styles.statLabel}>P95 Response</div>
            <div className={styles.statDesc}>Cached Operations</div>
          </div>
          <div className={styles.stat}>
            <div className={styles.statNumber}>1000+</div>
            <div className={styles.statLabel}>Concurrent Users</div>
            <div className={styles.statDesc}>Horizontal Scaling</div>
          </div>
        </div>
      </div>
    </header>
  );
}

function QuickStartSection() {
  return (
    <section className={styles.quickStart}>
      <div className="container">
        <div className="row">
          <div className="col col--12">
            <div className="text--center margin-bottom--lg">
              <Heading as="h2">Get Started in Minutes</Heading>
              <p className="margin-bottom--lg">
                Deploy GraphRAG API with Docker Compose and start building intelligent applications
              </p>
            </div>
          </div>
        </div>
        <div className="row">
          <div className="col col--4">
            <div className={styles.quickStartStep}>
              <div className={styles.stepNumber}>1</div>
              <Heading as="h3">Clone & Start</Heading>
              <div className={styles.codeBlock}>
                <pre>
                  <code>{`git clone https://github.com/pierregrothe/graphrag-api.git
cd graphrag-api
docker-compose up -d`}</code>
                </pre>
              </div>
            </div>
          </div>
          <div className="col col--4">
            <div className={styles.quickStartStep}>
              <div className={styles.stepNumber}>2</div>
              <Heading as="h3">Authenticate</Heading>
              <div className={styles.codeBlock}>
                <pre>
                  <code>{`curl -X POST "http://localhost:8000/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{"username": "admin", "password": "admin123"}'`}</code>
                </pre>
              </div>
            </div>
          </div>
          <div className="col col--4">
            <div className={styles.quickStartStep}>
              <div className={styles.stepNumber}>3</div>
              <Heading as="h3">Query Graph</Heading>
              <div className={styles.codeBlock}>
                <pre>
                  <code>{`curl -X GET "http://localhost:8000/api/entities" \\
  -H "Authorization: Bearer $JWT_TOKEN"`}</code>
                </pre>
              </div>
            </div>
          </div>
        </div>
        <div className="text--center margin-top--lg">
          <Link
            className="button button--primary button--lg"
            to="/docs/getting-started/quickstart">
            Complete Quickstart Guide
          </Link>
        </div>
      </div>
    </section>
  );
}

function APIShowcase() {
  return (
    <section className={styles.apiShowcase}>
      <div className="container">
        <div className="row">
          <div className="col col--6">
            <Heading as="h2">REST API</Heading>
            <p>
              Complete REST API with OpenAPI 3.0 specification, interactive documentation,
              and comprehensive error handling.
            </p>
            <div className={styles.codeBlock}>
              <pre>
                <code>{`// Semantic search
const response = await fetch('/api/graph/query', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + token,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: 'artificial intelligence',
    limit: 10
  })
});

const results = await response.json();`}</code>
              </pre>
            </div>
            <Link className="button button--outline" to="/api">
              Explore REST API
            </Link>
          </div>
          <div className="col col--6">
            <Heading as="h2">GraphQL API</Heading>
            <p>
              Powerful GraphQL interface with real-time subscriptions, field selection optimization,
              and interactive playground.
            </p>
            <div className={styles.codeBlock}>
              <pre>
                <code>{`query GetEntitiesWithRelationships {
  entities(first: 10) {
    edges {
      node {
        id
        title
        type
        relationships {
          id
          target
          type
          weight
        }
      }
    }
  }
}`}</code>
              </pre>
            </div>
            <Link className="button button--outline" to="/playground">
              Try GraphQL Playground
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

function EnterpriseFeatures() {
  const features = [
    {
      title: 'Production Ready',
      description: 'Docker deployment, Redis caching, horizontal scaling, and enterprise security.',
      icon: '🚀'
    },
    {
      title: 'Advanced Monitoring',
      description: 'Prometheus metrics, Grafana dashboards, OpenTelemetry tracing, and real-time alerts.',
      icon: '📊'
    },
    {
      title: 'Multi-Provider LLM',
      description: 'Support for Ollama, Google Cloud AI, OpenAI with intelligent provider selection.',
      icon: '🤖'
    },
    {
      title: 'Real-time Updates',
      description: 'WebSocket subscriptions for live entity updates and performance monitoring.',
      icon: '⚡'
    },
    {
      title: 'Graph Analytics',
      description: 'Community detection, centrality analysis, multi-hop queries, and anomaly detection.',
      icon: '🔍'
    },
    {
      title: 'Enterprise Security',
      description: 'JWT authentication, API key management, RBAC, audit logging, and data encryption.',
      icon: '🔐'
    }
  ];

  return (
    <section className={styles.enterpriseFeatures}>
      <div className="container">
        <div className="text--center margin-bottom--lg">
          <Heading as="h2">Enterprise-Grade Features</Heading>
          <p>
            Built for production with enterprise security, monitoring, and scalability
          </p>
        </div>
        <div className="row">
          {features.map((feature, idx) => (
            <div key={idx} className="col col--4 margin-bottom--lg">
              <div className={styles.featureCard}>
                <div className={styles.featureIcon}>{feature.icon}</div>
                <Heading as="h3">{feature.title}</Heading>
                <p>{feature.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default function Home(): JSX.Element {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={`${siteConfig.title} - Enterprise Knowledge Graph Platform`}
      description="Enterprise-grade GraphRAG API for building intelligent knowledge graph applications with semantic search, real-time analytics, and advanced monitoring.">
      <HomepageHeader />
      <main>
        <QuickStartSection />
        <HomepageFeatures />
        <APIShowcase />
        <EnterpriseFeatures />
      </main>
    </Layout>
  );
}
