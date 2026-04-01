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
- Azure Database for PostgreSQL Flexible Server
- Azure Cache for Redis
- Azure Storage Account
- Azure Key Vault

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
- Database connectivity check
- Redis connectivity check
- Storage access check

## 6. Rollback Strategy

- Revert to the previous Container Apps revision.
- Re-run infrastructure deployment only when config drift is involved.
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
		data.bicep
		storage.bicep
		secrets.bicep
```

## 8. Environment Configuration

| Parameter | Value |
|-----------|-------|
| environmentName | qa |
| location | eastus |
| webMinReplicas | 1 |
| webMaxReplicas | 3 |
| workerMinReplicas | 1 |
| workerMaxReplicas | 2 |
| postgresSku | Standard_B1ms |
| postgresHaMode | Disabled |
| postgresBackupDays | 7 |
| redisSku | Basic |
| redisSkuCapacity | 0 |
| storageReplication | LRS |

## 9. Resource Naming

| Resource | Name |
|----------|------|
| Resource Group | rg-resumetailor-qa |
| Container Registry | crresumetailor |
| Container Apps Env | cae-resumetailor-qa |
| Web App | ca-web-resumetailor-qa |
| Worker App | ca-worker-resumetailor-qa |
| PostgreSQL | psql-resumetailor-qa |
| Redis | redis-resumetailor-qa |
| Storage | stresumetailorqa |
| Key Vault | kv-resumetailor-qa |

## 10. QA Validation Checklist

- Bicep build passes
- Bicep what-if passes
- Image build and push pass
- Deployment to QA in `eastus` succeeds
- Health checks pass
- Regression runner passes blocking checks

## 11. Governance Gate

- This deployment plan is approved for architecture and readiness planning.
- Infrastructure and CI/CD implementation are blocked until explicit CEO approval.

