# GraphRAG API Service - Operational Runbook

## Table of Contents
1. [Service Overview](#service-overview)
2. [Deployment Procedures](#deployment-procedures)
3. [Monitoring & Alerts](#monitoring--alerts)
4. [Incident Response](#incident-response)
5. [Troubleshooting Guide](#troubleshooting-guide)
6. [Maintenance Procedures](#maintenance-procedures)
7. [Disaster Recovery](#disaster-recovery)
8. [Performance Tuning](#performance-tuning)

## Service Overview

### Architecture Components
- **API Service**: FastAPI application (REST + GraphQL)
- **Database**: PostgreSQL for persistence
- **Cache**: Redis for caching and rate limiting
- **LLM Provider**: Ollama (local) or Google Gemini (cloud)
- **Load Balancer**: Nginx/Ingress
- **Monitoring**: Prometheus + Grafana

### Key Metrics
- **SLA Target**: 99.9% uptime
- **Response Time**: p95 < 500ms
- **Error Rate**: < 0.1%
- **Throughput**: 1000 req/s

## Deployment Procedures

### Initial Deployment

```bash
# 1. Create namespace
kubectl apply -f k8s/namespace.yaml

# 2. Set up secrets (update with your values first!)
kubectl apply -f k8s/secret.yaml

# 3. Deploy ConfigMap
kubectl apply -f k8s/configmap.yaml

# 4. Deploy database
kubectl apply -f k8s/postgres/

# 5. Run database migrations
kubectl run migration --rm -it --image=graphrag/api:latest \
  --restart=Never -- alembic upgrade head

# 6. Deploy application
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# 7. Set up ingress
kubectl apply -f k8s/ingress.yaml

# 8. Verify deployment
kubectl get pods -n graphrag
kubectl logs -n graphrag -l app=graphrag-api
```

### Rolling Update

```bash
# 1. Update image version
kubectl set image deployment/graphrag-api \
  graphrag-api=graphrag/api:v2.0.0 -n graphrag

# 2. Monitor rollout
kubectl rollout status deployment/graphrag-api -n graphrag

# 3. Verify new version
kubectl get pods -n graphrag -o wide
```

### Rollback

```bash
# Immediate rollback to previous version
kubectl rollout undo deployment/graphrag-api -n graphrag

# Rollback to specific revision
kubectl rollout undo deployment/graphrag-api --to-revision=2 -n graphrag
```

## Monitoring & Alerts

### Key Metrics to Monitor

#### Application Metrics
```bash
# Check application health
curl http://api.example.com/health/detailed

# Get Prometheus metrics
curl http://api.example.com/health/metrics
```

#### System Metrics
- CPU Usage: `graphrag_cpu_percent`
- Memory Usage: `graphrag_memory_usage_bytes`
- Request Rate: `graphrag_request_total`
- Error Rate: `graphrag_errors_total`
- Response Time: `graphrag_request_duration_seconds`

### Alert Rules

#### Critical Alerts (Page immediately)
1. **Service Down**
   - Condition: `up{job="graphrag-api"} == 0`
   - Action: Check pods, restart if necessary

2. **High Error Rate**
   - Condition: `rate(graphrag_errors_total[5m]) > 0.01`
   - Action: Check logs, identify error pattern

3. **Database Connection Failed**
   - Condition: `graphrag_database_connected == 0`
   - Action: Check database status, connection string

#### Warning Alerts
1. **High Memory Usage**
   - Condition: `graphrag_memory_percent > 80`
   - Action: Monitor, plan scaling

2. **Slow Response Time**
   - Condition: `graphrag_request_duration_seconds{quantile="0.95"} > 1`
   - Action: Check query performance, cache hit rate

## Incident Response

### Severity Levels
- **P1 (Critical)**: Complete service outage
- **P2 (High)**: Degraded performance, partial outage
- **P3 (Medium)**: Minor feature issues
- **P4 (Low)**: Cosmetic issues

### Response Procedures

#### P1 - Service Outage
1. **Acknowledge** alert within 5 minutes
2. **Assess** impact and scope
3. **Communicate** status to stakeholders
4. **Execute** recovery procedure:
   ```bash
   # Check pod status
   kubectl get pods -n graphrag
   
   # Restart pods if needed
   kubectl rollout restart deployment/graphrag-api -n graphrag
   
   # Check logs
   kubectl logs -n graphrag -l app=graphrag-api --tail=100
   ```
5. **Monitor** recovery
6. **Post-mortem** within 24 hours

#### P2 - Performance Degradation
1. Check resource usage:
   ```bash
   kubectl top pods -n graphrag
   kubectl top nodes
   ```
2. Scale if needed:
   ```bash
   kubectl scale deployment/graphrag-api --replicas=5 -n graphrag
   ```
3. Check cache hit rate
4. Review slow queries

## Troubleshooting Guide

### Common Issues

#### 1. Pods Not Starting
```bash
# Check pod events
kubectl describe pod <pod-name> -n graphrag

# Check resource limits
kubectl get resourcequota -n graphrag

# Check node capacity
kubectl describe nodes
```

#### 2. Database Connection Issues
```bash
# Test database connection
kubectl run -it --rm psql --image=postgres:16 --restart=Never -- \
  psql postgresql://user:pass@postgres-service:5432/graphrag

# Check secret
kubectl get secret graphrag-secrets -n graphrag -o yaml
```

#### 3. High Memory Usage
```bash
# Get memory profile
kubectl exec -n graphrag <pod-name> -- \
  curl localhost:8001/debug/pprof/heap > heap.prof

# Force garbage collection
kubectl exec -n graphrag <pod-name> -- \
  curl -X POST localhost:8001/admin/gc
```

#### 4. Slow Queries
```sql
-- Find slow queries
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- Check table statistics
ANALYZE workspaces;
ANALYZE queries;
```

### Debug Commands

```bash
# Get into pod shell
kubectl exec -it <pod-name> -n graphrag -- /bin/bash

# View real-time logs
kubectl logs -f <pod-name> -n graphrag

# Port forward for local debugging
kubectl port-forward -n graphrag svc/graphrag-api-service 8001:80

# Get pod environment variables
kubectl exec <pod-name> -n graphrag -- env

# Check network connectivity
kubectl exec <pod-name> -n graphrag -- nc -zv postgres-service 5432
```

## Maintenance Procedures

### Database Maintenance

#### Weekly Tasks
```sql
-- Update statistics
ANALYZE;

-- Reindex if needed
REINDEX INDEX CONCURRENTLY idx_queries_created;

-- Vacuum tables
VACUUM ANALYZE workspaces;
VACUUM ANALYZE queries;
```

#### Monthly Tasks
```sql
-- Full vacuum (requires downtime)
VACUUM FULL;

-- Update materialized views
REFRESH MATERIALIZED VIEW CONCURRENTLY query_performance_stats;

-- Archive old data
INSERT INTO queries_archive 
SELECT * FROM queries 
WHERE created_at < NOW() - INTERVAL '90 days';

DELETE FROM queries 
WHERE created_at < NOW() - INTERVAL '90 days';
```

### Certificate Renewal
```bash
# Check certificate expiration
kubectl get certificate -n graphrag

# Trigger renewal (if using cert-manager)
kubectl annotate certificate graphrag-tls \
  cert-manager.io/issue-temporary-certificate="true" -n graphrag
```

### Backup Procedures

#### Daily Backup
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
NAMESPACE="graphrag"
POD=$(kubectl get pod -n $NAMESPACE -l app=postgres -o jsonpath='{.items[0].metadata.name}')

# Database backup
kubectl exec -n $NAMESPACE $POD -- \
  pg_dump -U graphrag graphrag | \
  gzip > backup_${DATE}.sql.gz

# Upload to S3
aws s3 cp backup_${DATE}.sql.gz s3://graphrag-backups/daily/
```

## Disaster Recovery

### RTO/RPO Targets
- **RTO (Recovery Time Objective)**: 1 hour
- **RPO (Recovery Point Objective)**: 1 hour

### Recovery Procedures

#### Database Recovery
```bash
# 1. Get latest backup
aws s3 cp s3://graphrag-backups/daily/latest.sql.gz .

# 2. Restore database
gunzip -c latest.sql.gz | \
  kubectl exec -i postgres-pod -n graphrag -- \
  psql -U graphrag graphrag

# 3. Verify data integrity
kubectl exec postgres-pod -n graphrag -- \
  psql -U graphrag -c "SELECT COUNT(*) FROM workspaces;"
```

#### Full Service Recovery
```bash
# 1. Deploy fresh cluster
terraform apply -auto-approve

# 2. Restore secrets
kubectl apply -f k8s/secret-backup.yaml

# 3. Deploy application
kubectl apply -f k8s/

# 4. Restore database
./scripts/restore-database.sh

# 5. Verify service
curl https://api.example.com/health
```

## Performance Tuning

### Application Tuning

```python
# Adjust in configmap
MAX_WORKERS: "8"  # Increase for more CPU cores
CONNECTION_POOL_SIZE: "50"  # Increase for more concurrent DB connections
CACHE_TTL: "7200"  # Increase for more aggressive caching
```

### Database Tuning

```sql
-- PostgreSQL configuration
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET work_mem = '256MB';
ALTER SYSTEM SET max_connections = 200;

-- Reload configuration
SELECT pg_reload_conf();
```

### Kubernetes Tuning

```yaml
# HPA (Horizontal Pod Autoscaler)
kubectl autoscale deployment graphrag-api \
  --min=3 --max=10 \
  --cpu-percent=70 \
  -n graphrag

# VPA (Vertical Pod Autoscaler)
kubectl apply -f - <<EOF
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: graphrag-api-vpa
  namespace: graphrag
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: graphrag-api
  updatePolicy:
    updateMode: "Auto"
EOF
```

## Escalation Matrix

| Severity | Response Time | Escalation Path | Contact |
|----------|--------------|-----------------|---------|
| P1 | 5 min | On-call → Team Lead → Director | PagerDuty |
| P2 | 15 min | On-call → Team Lead | Slack |
| P3 | 1 hour | On-call | Email |
| P4 | Next business day | Ticket | JIRA |

## Important URLs

- **Production API**: https://api.graphrag.example.com
- **Staging API**: https://staging-api.graphrag.example.com
- **Grafana Dashboard**: https://grafana.example.com/d/graphrag
- **Prometheus**: https://prometheus.example.com
- **Logs**: https://logs.example.com/app/graphrag
- **Documentation**: https://docs.graphrag.example.com
- **Status Page**: https://status.graphrag.example.com

## Contact Information

- **On-Call**: +1-XXX-XXX-XXXX
- **Slack Channel**: #graphrag-ops
- **Email**: graphrag-team@example.com
- **PagerDuty**: graphrag-service

---

Last Updated: 2025-09-02
Version: 1.0.0