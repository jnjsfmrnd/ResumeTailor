# Azure Deployment Plan: ResumeTailor V1 Round 2

**Date**: 2026-04-01
**Status**: Approved (Planning Only)

## 1. Deployment Strategy

V1 uses one hosted QA environment only. There is no production environment in this release.

- Environment: `qa`
- Region: `eastus`
- Purpose: smoke tests, regression checks, and operator validation

## 2. Promotion Strategy

- CI builds and tests the application.
- Bicep validation and what-if run before deployment.
- Deployment targets QA only.
- Smoke checks and regression checks run after deployment.
- Failed validation blocks further rollout work.

## 3. Azure Resources

- Azure Container Registry
- Azure Container Apps environment
- Web Container App
- Worker Container App
- Azure Cache for Redis
- Azure Storage Account for document artifacts and mounted SQLite storage
- Azure Key Vault

The QA deployment removes Azure Database for PostgreSQL from the V1 footprint and uses a storage-backed SQLite file for application persistence.

## 4. Security Strategy

- Use GitHub OIDC for Azure authentication where possible.
- Store operator-managed secrets in Key Vault.
- Keep user-supplied GitHub Models keys out of storage, logs, database rows, queue payloads, and files.
- Use managed identity from the apps to access Key Vault and Storage.
- Encrypt uploaded PDFs, generated PDFs, and session records at rest.
- Run a scheduled cleanup job that purges QA session artifacts older than 7 days.

## 5. Health Checks

- Web app health endpoint
- Worker readiness check
- SQLite file connectivity and migration state check
- Redis connectivity check
- Storage access check

## 6. Rollback Strategy

- Revert to the previous Container Apps revision.
- Re-run infrastructure deployment only when config drift is involved.
- Restore the last known-good SQLite database snapshot before resuming QA validation if data corruption or lock failures occur.
- Do not reverse database migrations without an explicit migration rollback plan.

## 7. Bicep Layout

```text
infra/
	main.bicep
	parameters/
		qa.bicepparam
	modules/
		registry.bicep
		compute.bicep
		storage.bicep
		secrets.bicep
```

## 8. Environment Configuration

| Parameter | Value |
|-----------|-------|
| environmentName | qa |
| location | eastus |
| webMinReplicas | 1 |
| webMaxReplicas | 1 |
| workerMinReplicas | 1 |
| workerMaxReplicas | 1 |
| sqliteDbPath | /app/data/resumetailor.sqlite3 |
| qaTrafficProfile | single-replica, low-concurrency |
| redisSku | Basic |
| redisSkuCapacity | 0 |
| storageReplication | LRS |

Implementation directive for Engineer F:

- Freeze one concrete SQLite environment contract in the first implementation pass, including the environment variable name and default-path behavior.
- Freeze one shared writable storage model for the web app, worker app, and setup job in the same pass.
- Ensure migrations complete before user traffic is enabled; do not leave migration ordering as an implicit runtime behavior.
- Align Django settings, Docker, CI, GitHub Actions, and Azure IaC to that contract in one coordinated change set.

## 9. Resource Naming

| Resource | Name |
|----------|------|
| Resource Group | rg-resumetailor-qa |
| Container Registry | crresumetailor |
| Container Apps Env | cae-resumetailor-qa |
| Web App | ca-web-resumetailor-qa |
| Worker App | ca-worker-resumetailor-qa |
| Redis | redis-resumetailor-qa |
| Storage | stresumetailorqa |
| SQLite path | /app/data/resumetailor.sqlite3 |
| Key Vault | kv-resumetailor-qa |

## 10. QA Validation Checklist

- Bicep build passes
- Bicep what-if passes
- Image build and push pass
- Deployment to QA in `eastus` succeeds
- SQLite path is writable before traffic is enabled
- Health checks pass
- Regression runner passes blocking checks

## 11. Governance Gate

- This deployment plan is approved for architecture and readiness planning.
- Infrastructure and CI/CD implementation are blocked until explicit CEO approval.

