# Runbook: Event Analytics API

Operational procedures for the service running on EKS. Commands assume
`aws eks update-kubeconfig --region <region> --name <cluster>` has been run
(the exact command is a Terraform output: `terraform output kubeconfig_command`).

The release lives in namespace `event-analytics`, release name `event-analytics-api`.

```
NS=event-analytics
APP=event-analytics-api
```

## 1. Rolling back a bad release

Deploys run `helm upgrade --atomic`, so a release that never becomes ready
rolls itself back. Manual rollback is for the other case: the rollout
succeeded but the new version misbehaves.

```bash
# What is deployed right now, and what came before it?
helm history $APP -n $NS

# Roll back to the previous revision
helm rollback $APP -n $NS

# Or to a specific known-good revision
helm rollback $APP <REVISION> -n $NS

# Confirm
kubectl rollout status deployment/$APP -n $NS
kubectl get pods -n $NS -o wide
```

Notes:
- Rollback restores the previous image tag and chart values. It does not
  undo database migrations. Alembic downgrades exist
  (`alembic downgrade -1`) but treat them as a last resort; prefer
  roll-forward migrations that stay backward compatible for one release.
- If the bad version corrupted data, stop and assess before rolling back;
  rollback fixes code, not data.

## 2. Reading the dashboards

Grafana dashboard: "Event Analytics API: RED" (uid `event-analytics-red`).

Top row, in the order to check them during an incident:

| Panel | Healthy looks like | If it is not |
|---|---|---|
| Request rate | Steady, follows traffic patterns | Sudden drop: clients cannot reach you (LB, DNS, crash loop). Sudden spike: retry storm or abuse. |
| Error rate (5xx) | ~0, alert-worthy above 1% | Correlate with the "Error rate by route" panel to find which endpoint. Check pod logs next. |
| p95 latency | Low ms for health, tens of ms for queries | Rising p95 with flat request rate usually means the database: check the pool panel. |
| In-flight requests | Low single digits | Climbing steadily means requests are stuck, often on DB connections. |

Second-level panels:

- "Request rate by route": which endpoint changed behavior. The `path` label
  is the route template, so cardinality stays flat; unknown URLs appear as
  `unmatched` (scanners and typos, usually 404s).
- "Latency quantiles": p50 vs p99 divergence means a subset of requests is
  slow (cold pool connections, lock contention), not the service as a whole.
- "Database connection pool": `checked out` pinned at `pool size` plus
  `overflow` above zero means the pool is exhausted; requests are queueing.
  Fix is usually a slow query, not a bigger pool.

Logs are structured JSON on stdout, one line per request from the
`app.access` logger with `route`, `status`, and `duration_ms` fields:

```bash
kubectl logs deployment/$APP -n $NS --tail=100
# Only errors:
kubectl logs deployment/$APP -n $NS --tail=500 | grep '"level": "ERROR"'
```

## 3. Diagnosing a failing deploy

A release deploy failed in GitHub Actions. Where to look, in order:

### 3a. The workflow failed before touching the cluster

Lint, tests, or the Trivy scan failed. Read the job log; nothing was
deployed and the cluster is untouched. A Trivy failure means a fixable
CRITICAL/HIGH CVE in the image: bump the base image or the pinned
dependency, then re-tag.

### 3b. Helm failed and rolled back (`--atomic` timed out)

The workflow log shows `UPGRADE FAILED` and the previous release is still
serving. Find out why the new pods never became ready:

```bash
# Migration job is a pre-upgrade hook; it runs before pods. Did it fail?
kubectl get jobs -n $NS
kubectl logs job/$APP-migrate -n $NS

# Pod-level: pending, crash looping, or failing probes?
kubectl get pods -n $NS
kubectl describe pod <POD> -n $NS   # read Events at the bottom
kubectl logs <POD> -n $NS --previous
```

Common causes, mapped to what you will see:

| Symptom | Likely cause |
|---|---|
| `ImagePullBackOff` | Tag not in ECR (push step failed?) or node role lost ECR read access. |
| Migration job error | Bad migration or DATABASE_URL secret wrong; fix and re-run. |
| `CreateContainerConfigError` | Secret `event-analytics-db` missing in the namespace. |
| Readiness probe failing, pod Running | App cannot reach RDS: check the RDS security group and the secret's host/credentials. `kubectl exec` into the pod and hit `localhost:8000/health/ready`. |
| Pods `Pending` | Cluster out of capacity: `kubectl describe pod` shows FailedScheduling; check node group size. |

### 3c. Deploy succeeded but the service is unhealthy

Use section 2. If the previous version was healthy, roll back first
(section 1), diagnose second.

## 4. Local observability stack

To explore the dashboards without a cluster:

```powershell
docker compose --profile observability up -d
.\scripts\seed.ps1        # generate some traffic
```

- API: http://localhost:8000 (docs at /docs)
- Prometheus: http://localhost:9090 (Status > Targets should show the api up)
- Grafana: http://localhost:3000 (anonymous admin, dashboard is pre-provisioned)

Teardown: `docker compose --profile observability down` (add `-v` to drop the database).
