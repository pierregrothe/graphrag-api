# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) that document the significant architectural decisions made in this project.

## What is an ADR?

An Architecture Decision Record captures an important architectural decision made along with its context and consequences. ADRs help future developers understand why certain decisions were made.

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](001-sqlite-over-postgresql.md) | Use SQLite Instead of PostgreSQL | Accepted | 2025-09-02 |
| [002](002-memory-cache-over-redis.md) | Use In-Memory Cache Instead of Redis | Accepted | 2025-09-02 |
| [003](003-serverless-over-kubernetes.md) | Use Serverless (Cloud Run) Instead of Kubernetes | Accepted | 2025-09-02 |
| [004](004-dual-llm-provider-strategy.md) | Dual LLM Provider Strategy (Ollama + Gemini) | Accepted | 2025-09-02 |
| [005](005-simplified-architecture.md) | Simplified Architecture for Small-Scale Deployment | Accepted | 2025-09-02 |

## ADR Template

When creating a new ADR, use this template:

```markdown
# ADR-XXX: [Title]

## Status
[Proposed | Accepted | Deprecated | Superseded by ADR-XXX]

## Date
YYYY-MM-DD

## Context
[Describe the issue or problem that needs to be addressed]

## Decision
[Describe the decision that was made]

## Consequences

### Positive
- [Positive consequence 1]
- [Positive consequence 2]

### Negative
- [Negative consequence 1]
- [Negative consequence 2]

### Mitigation
- [How to mitigate negative consequences]

## Implementation
[Brief description of how this was implemented]
```

## Key Architectural Principles

Based on our ADRs, the key principles for this project are:

1. **Simplicity First**: Optimize for small-scale deployment (1-5 users)
2. **Serverless Ready**: Design for Cloud Run and scale-to-zero
3. **Minimal Dependencies**: Use SQLite and in-memory cache
4. **Quick Deployment**: Target < 5 minute deployment time
5. **Cost Optimization**: Minimize infrastructure costs
6. **Developer Experience**: Easy local development with Docker
