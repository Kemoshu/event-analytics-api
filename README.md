# Event Analytics API

[![CI](https://github.com/Kemoshu/event-analytics-api/actions/workflows/ci.yml/badge.svg)](https://github.com/Kemoshu/event-analytics-api/actions/workflows/ci.yml)

An event ingestion and analytics service, built and operated the way I would run it in production: containerized, deployed to Kubernetes on AWS with Terraform-managed infrastructure, shipped through a CI/CD pipeline with image scanning and OIDC-based cloud auth, and observable through Prometheus metrics, Grafana dashboards, and structured logs.

The application itself is deliberately small (FastAPI + PostgreSQL). The point of this repo is everything around it.

## Architecture

```mermaid
flowchart LR
    subgraph GitHub
        DEV[git tag vX.Y.Z] --> GA[GitHub Actions]
    end

    subgraph AWS
        GA -- OIDC, no stored keys --> IAM[IAM deploy role]
        GA -- push image --> ECR[(ECR)]
        GA -- helm upgrade --> EKS

        subgraph VPC
            subgraph PRIV["Private subnets"]
                EKS[EKS node group]
                RDS[(RDS PostgreSQL)]
            end
            NAT[NAT gateway]
        end

        EKS -- SQL --> RDS
        SM[Secrets Manager] -. DB credentials .-> EKS
    end

    subgraph Observability
        PROM[Prometheus] -- scrape /metrics --> EKS
        GRAF[Grafana RED dashboard] --> PROM
    end

    USER[Clients] -- HTTP --> EKS
```

The API ingests events (`POST /events`), serves filtered queries (`GET /events`), and aggregates (`GET /analytics/counts`, `GET /analytics/timeseries`). Interactive docs at `/docs`.

## Repo layout

```
app/                  FastAPI service: routers, metrics middleware, JSON logging
alembic/              database migrations
tests/                pytest suite (runs against a real PostgreSQL)
docker/               multi-stage Dockerfile (non-root, pinned base, healthcheck)
helm/                 Helm chart: Deployment, Service, HPA, probes, migration hook
infra/                Terraform: VPC, EKS, ECR, RDS, GitHub OIDC IAM
.github/workflows/    CI (lint, test, scan) and Release (build, push, deploy)
observability/        Prometheus scrape config, Grafana provisioning
dashboards/           Grafana RED dashboard JSON
docs/runbook.md       rollback, dashboard reading, deploy diagnosis
```

## Local development

Requirements: Docker Desktop.

```powershell
# API + PostgreSQL, migrations applied automatically
docker compose up -d

# seed sample events and explore
.\scripts\seed.ps1
curl http://localhost:8000/analytics/counts

# full local observability stack (adds Prometheus + Grafana)
docker compose --profile observability up -d
# Grafana: http://localhost:3000  Prometheus: http://localhost:9090

# lint and tests, in the same image CI uses
docker compose --profile test run --rm test sh -c "ruff check . && pytest -q"

# teardown (add -v to drop the database volume)
docker compose --profile observability down
```

## CI/CD flow

**CI** (every push and PR): ruff lint, pytest against a real PostgreSQL service container, Alembic upgrade/downgrade check, Helm lint and render, Terraform fmt and validate, Docker build, and a Trivy scan that fails the build on fixable CRITICAL/HIGH CVEs.

**Release** (pushing a `v*` tag): re-runs lint and tests, then assumes an AWS IAM role via GitHub OIDC (no long-lived keys anywhere), builds and scans the image, pushes it to ECR, and runs `helm upgrade --atomic` against EKS. `--atomic` means a rollout that never becomes ready rolls itself back.

```powershell
git tag v1.0.0
git push origin v1.0.0
```

The deploy role's trust policy only matches version tags on this specific repository, and its Kubernetes access is scoped to the app namespace through an EKS access entry.

## Deploying to AWS

Everything below bills real money until torn down; see the cost table.

```powershell
cd infra

# one time: create the state bucket and lock table, then:
cp backend.hcl.example backend.hcl   # fill in your bucket and table
cp terraform.tfvars.example terraform.tfvars  # set github_repository
terraform init -backend-config=backend.hcl
terraform plan
terraform apply

# point kubectl at the new cluster
terraform output -raw kubeconfig_command | Invoke-Expression

# one-time cluster prep: namespace + database secret
kubectl create namespace event-analytics
# build the URL from the RDS endpoint and the Secrets Manager password
# (terraform output rds_endpoint / rds_master_secret_arn)
kubectl create secret generic event-analytics-db `
  --from-literal=DATABASE_URL='postgresql+psycopg2://app:PASSWORD@HOST:5432/events' `
  -n event-analytics
```

Then set four GitHub repository variables from the Terraform outputs (`AWS_REGION`, `AWS_DEPLOY_ROLE_ARN`, `ECR_REPOSITORY`, `EKS_CLUSTER_NAME`) and push a version tag.

Teardown:

```powershell
helm uninstall event-analytics-api -n event-analytics
terraform destroy
```

### What this costs

| Resource | Approx. monthly (us-east-1) |
|---|---|
| EKS control plane | ~$73 |
| 2x t3.medium nodes | ~$60 |
| NAT gateway | ~$33 + data |
| RDS db.t4g.micro | ~$12 |
| **Total** | **~$180/month, ~$0.25/hour** |

This is a demo stack: spin it up, record the walkthrough, tear it down. Terraform makes both directions repeatable.

## Observability

The service exposes:

- `/metrics`: Prometheus exposition. RED metrics (`http_requests_total`, `http_request_duration_seconds` histogram, `http_requests_in_progress`) labeled by route template rather than raw URL to keep cardinality bounded, plus SQLAlchemy pool gauges (`db_pool_*`).
- `/health/live` and `/health/ready`: liveness is process-up; readiness executes `SELECT 1` against the database. Kubernetes probes and the Docker healthcheck use these.
- Structured JSON logs on stdout, one line per request with route, status, and duration, ready for CloudWatch or Loki.

The Grafana dashboard ([dashboards/event-analytics-red.json](dashboards/event-analytics-red.json)) tracks rate, errors, duration quantiles, and DB pool saturation. [docs/runbook.md](docs/runbook.md) explains how to read it during an incident and how to diagnose a failing deploy.

## Design decisions and trade-offs

**Raw Terraform resources instead of community modules.** The VPC and EKS modules from terraform-aws-modules are what I would reach for on a team, but writing the resources out shows I understand what the modules generate: subnet tagging for load balancer discovery, the IAM roles EKS actually needs, and the OIDC trust chain.

**One NAT gateway, not one per AZ.** Cuts the NAT bill in half for a demo. The trade-off is that an AZ outage takes private-subnet egress down with it; production gets one per AZ.

**RDS manages its own master password.** `manage_master_user_password = true` keeps the password out of Terraform state, git, and CI. The Helm chart never templates a secret either; it references one created out of band. Nothing sensitive is in this repository by construction.

**Migrations as a Helm pre-upgrade hook.** The Alembic job runs before new pods roll out, so code never runs against a schema it does not know. The constraint this imposes is that migrations must stay backward compatible for one release, which is the discipline you want anyway.

**Route-template metric labels.** Labeling `http_requests_total` with `/events` instead of `/events?limit=50...` keeps time series count flat no matter what clients send. Unmatched paths collapse into a single `unmatched` label so scanners cannot inflate cardinality.

**`helm upgrade --atomic` instead of a smarter deploy strategy.** Canary or blue/green would be overkill for one service; atomic upgrades plus readiness probes give automatic rollback for the dominant failure mode (a release that never becomes healthy).

**Tests hit a real PostgreSQL.** The analytics queries use `date_trunc` and JSON columns; mocking the database would test the mock. Compose and CI both provision a throwaway instance, so the suite is identical everywhere.

**Single region, single environment.** Variables exist to stamp out staging/prod copies, but a portfolio project gains nothing from a second environment except a second bill.

## Runbook

Operational procedures live in [docs/runbook.md](docs/runbook.md): rolling back a bad release, reading the RED dashboard under pressure, and a symptom-to-cause table for failed deploys.
