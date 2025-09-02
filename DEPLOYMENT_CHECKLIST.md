# GraphRAG API Service - Production Deployment Checklist

## Pre-Deployment Requirements

### 1. Infrastructure Setup ⬜
- [ ] **Cloud Account Setup**
  - [ ] AWS/GCP/Azure account configured
  - [ ] IAM roles and permissions set up
  - [ ] VPC and networking configured
  - [ ] Security groups/firewall rules defined

- [ ] **Kubernetes Cluster**
  - [ ] Cluster provisioned (EKS/GKE/AKS)
  - [ ] kubectl configured and authenticated
  - [ ] Ingress controller installed
  - [ ] Cert-manager installed (for SSL)

- [ ] **Database Setup**
  - [ ] PostgreSQL instance created (RDS/Cloud SQL)
  - [ ] Database credentials secured
  - [ ] Backup strategy configured
  - [ ] Connection pooling configured

- [ ] **Redis Cache**
  - [ ] Redis instance created (ElastiCache/Memorystore)
  - [ ] Redis credentials secured
  - [ ] Persistence configured
  - [ ] Cluster mode enabled (if needed)

### 2. Configuration & Secrets ⬜
- [ ] **API Keys & Credentials**
  - [ ] Google Gemini API key (if using)
  - [ ] Google Project ID configured
  - [ ] Database connection string
  - [ ] Redis connection string
  - [ ] JWT secret key generated

- [ ] **Domain & SSL**
  - [ ] Domain name registered
  - [ ] DNS records configured
  - [ ] SSL certificate obtained
  - [ ] Certificate stored in Kubernetes

- [ ] **Environment Variables**
  ```bash
  # Update these in k8s/secret.yaml
  - [ ] DATABASE_URL
  - [ ] REDIS_URL
  - [ ] JWT_SECRET_KEY
  - [ ] GOOGLE_API_KEY (if using Gemini)
  - [ ] DEFAULT_ADMIN_PASSWORD
  ```

### 3. Security Review ⬜
- [ ] **Access Control**
  - [ ] RBAC policies reviewed
  - [ ] Service accounts created
  - [ ] API key rotation scheduled
  - [ ] Network policies defined

- [ ] **Secrets Management**
  - [ ] Secrets encrypted at rest
  - [ ] External secrets operator configured (optional)
  - [ ] Vault/AWS Secrets Manager integrated (optional)
  - [ ] Secret rotation policy defined

- [ ] **Compliance**
  - [ ] GDPR compliance verified (if applicable)
  - [ ] Data residency requirements met
  - [ ] Audit logging enabled
  - [ ] Security scanning completed

## Deployment Steps

### Phase 1: Database Setup ⬜
```bash
# 1. Connect to database
- [ ] psql -h <db-host> -U <username> -d postgres

# 2. Create database
- [ ] CREATE DATABASE graphrag;

# 3. Run initialization script
- [ ] psql -h <db-host> -U <username> -d graphrag < scripts/init.sql

# 4. Verify tables created
- [ ] \dt graphrag.*
```

### Phase 2: Kubernetes Deployment ⬜
```bash
# 1. Create namespace
- [ ] kubectl apply -f k8s/namespace.yaml

# 2. Update and apply secrets
- [ ] # Edit k8s/secret.yaml with your values
- [ ] kubectl apply -f k8s/secret.yaml

# 3. Apply ConfigMap
- [ ] kubectl apply -f k8s/configmap.yaml

# 4. Deploy application
- [ ] kubectl apply -f k8s/deployment.yaml
- [ ] kubectl apply -f k8s/service.yaml

# 5. Configure ingress
- [ ] # Edit k8s/ingress.yaml with your domain
- [ ] kubectl apply -f k8s/ingress.yaml
```

### Phase 3: Verification ⬜
- [ ] **Pod Status**
  ```bash
  kubectl get pods -n graphrag
  # All pods should be Running
  ```

- [ ] **Service Health**
  ```bash
  kubectl port-forward -n graphrag svc/graphrag-api-service 8001:80
  curl http://localhost:8001/health
  ```

- [ ] **Database Connectivity**
  ```bash
  kubectl logs -n graphrag -l app=graphrag-api | grep database
  # Should show successful connection
  ```

- [ ] **External Access**
  ```bash
  curl https://your-domain.com/health
  # Should return healthy status
  ```

### Phase 4: Monitoring Setup ⬜
- [ ] **Prometheus**
  - [ ] Prometheus configured to scrape metrics
  - [ ] Service monitor created
  - [ ] Alert rules configured
  - [ ] Test alerts firing

- [ ] **Grafana**
  - [ ] Dashboards imported
  - [ ] Data sources configured
  - [ ] Alerts configured
  - [ ] Test dashboard visibility

- [ ] **Logging**
  - [ ] Log aggregation configured
  - [ ] Log retention policy set
  - [ ] Log alerts configured
  - [ ] Test log queries

## Post-Deployment Validation

### 1. Functional Testing ⬜
- [ ] **API Endpoints**
  ```bash
  # Health check
  - [ ] curl https://api.domain.com/health
  
  # Create workspace
  - [ ] curl -X POST https://api.domain.com/api/workspaces \
        -H "Authorization: Bearer $TOKEN" \
        -d '{"name": "test"}'
  
  # GraphQL query
  - [ ] curl -X POST https://api.domain.com/graphql \
        -H "Content-Type: application/json" \
        -d '{"query": "{ healthCheck { status } }"}'
  ```

- [ ] **Authentication**
  - [ ] Login endpoint works
  - [ ] JWT tokens generated
  - [ ] Protected endpoints secured
  - [ ] Rate limiting active

### 2. Performance Testing ⬜
- [ ] **Load Testing**
  ```bash
  # Run load test
  - [ ] k6 run scripts/load-test.js
  
  # Verify metrics
  - [ ] Response time < 500ms (p95)
  - [ ] Error rate < 0.1%
  - [ ] CPU usage < 70%
  - [ ] Memory usage < 80%
  ```

### 3. Security Testing ⬜
- [ ] **Security Scan**
  ```bash
  # Run security scan
  - [ ] trivy image graphrag/api:latest
  
  # Check headers
  - [ ] curl -I https://api.domain.com
  # Should include security headers
  ```

### 4. Backup Verification ⬜
- [ ] **Database Backup**
  ```bash
  # Test backup
  - [ ] ./scripts/backup.sh
  
  # Verify backup exists
  - [ ] aws s3 ls s3://backups/graphrag/
  ```

## Rollback Plan ⬜

### If Issues Occur:
1. [ ] **Immediate Rollback**
   ```bash
   kubectl rollout undo deployment/graphrag-api -n graphrag
   ```

2. [ ] **Database Rollback**
   ```bash
   # Restore from backup
   psql -h <db-host> -U <username> -d graphrag < backup.sql
   ```

3. [ ] **DNS Rollback**
   - [ ] Point DNS to previous environment
   - [ ] Verify traffic routing

## Sign-off Checklist

### Technical Sign-off ⬜
- [ ] All tests passing
- [ ] Performance benchmarks met
- [ ] Security scan clean
- [ ] Monitoring operational
- [ ] Backups verified
- [ ] Documentation complete

### Business Sign-off ⬜
- [ ] Feature requirements met
- [ ] SLA requirements confirmed
- [ ] Cost within budget
- [ ] Training completed
- [ ] Support team ready

### Final Approval ⬜
- [ ] Technical Lead: _______________ Date: ___________
- [ ] Product Owner: _______________ Date: ___________
- [ ] Security Team: _______________ Date: ___________
- [ ] Operations Team: _____________ Date: ___________

## Go-Live Communication ⬜

### Internal Communication
- [ ] Team notified via Slack
- [ ] Runbook shared with on-call
- [ ] Support team briefed
- [ ] Monitoring alerts configured

### External Communication
- [ ] API documentation published
- [ ] Status page updated
- [ ] Customer notification sent (if applicable)
- [ ] Partner notification sent (if applicable)

## Post Go-Live Tasks ⬜

### Day 1
- [ ] Monitor metrics closely
- [ ] Review error logs
- [ ] Gather initial feedback
- [ ] Address any critical issues

### Week 1
- [ ] Performance review
- [ ] Security audit
- [ ] User feedback analysis
- [ ] Optimization opportunities identified

### Month 1
- [ ] Full operational review
- [ ] Cost optimization
- [ ] Capacity planning update
- [ ] Roadmap planning

---

## Important Notes

⚠️ **CRITICAL**: Before deployment, ensure you have:
1. Updated all secret values in `k8s/secret.yaml`
2. Configured your domain in ingress
3. Set up database backups
4. Tested rollback procedures
5. Notified all stakeholders

📝 **Documentation**: Ensure these documents are accessible:
- [RUNBOOK.md](./RUNBOOK.md)
- [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- [DEPLOYMENT_REQUIREMENTS.md](./DEPLOYMENT_REQUIREMENTS.md)

🔐 **Security**: Never commit actual secrets to git. Use:
- Kubernetes secrets
- External secrets operator
- Vault or cloud secret managers

---

Deployment Date: ___________
Deployed By: ___________
Version: ___________
Environment: Production