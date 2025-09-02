# ADR-003: Use Serverless (Cloud Run) Instead of Kubernetes

## Status
Accepted

## Date
2025-09-02

## Context
The initial deployment strategy included Kubernetes manifests with deployments, services, ingress, and horizontal pod autoscaling for enterprise-grade container orchestration.

However, the actual requirements are:
- Very small scale (1-5 users)
- Minimal operational overhead
- Serverless and PaaS preferred
- Quick deployment
- Cost optimization (scale to zero)

## Decision
Use Google Cloud Run for production deployment instead of Kubernetes.

## Consequences

### Positive
- **Scale to Zero**: No costs when not in use
- **Fully Managed**: No cluster management overhead
- **Automatic HTTPS**: Built-in SSL certificates
- **Simple Deployment**: Single command deployment
- **Automatic Scaling**: Handles traffic spikes automatically
- **Pay Per Use**: Only pay for actual request processing time
- **Built-in Monitoring**: Integrated with Cloud Monitoring

### Negative
- **Cold Starts**: Initial request latency when scaled to zero
- **Stateless Only**: No persistent local storage
- **Request Limits**: 60-minute timeout maximum
- **Less Control**: Cannot customize runtime environment as much

### Mitigation
- Set minimum instances to 1 for production to avoid cold starts
- Use Cloud SQL or Firestore for persistent storage if needed
- Design application to be stateless (already done)
- Use Cloud Build for CI/CD pipeline

## Implementation
- Created `Dockerfile.cloudrun` optimized for Cloud Run
- Created `cloudbuild.yaml` for automated deployment
- Created deployment script `scripts/deploy-cloudrun.sh`
- Removed all Kubernetes manifests from k8s/ directory
- Updated documentation for Cloud Run deployment
