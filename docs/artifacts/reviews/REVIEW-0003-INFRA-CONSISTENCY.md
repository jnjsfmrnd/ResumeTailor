# Review: Azure Deployment and GitHub Actions Consistency Check

**Date**: 2026-04-01
**Reviewer Mode**: Infra and CI consistency review
**Decision**: NOT CONSISTENT WITH CURRENT SQLITE PLANNING BASELINE

**Assigned Owner**: Engineer F

## Findings

### 1. Azure IaC still provisions PostgreSQL, which directly contradicts the approved SQLite planning baseline

**Severity**: High

The live Azure infrastructure definition still declares PostgreSQL parameters, names, and a dedicated data module. That is inconsistent with the updated ADR, technical spec, and deployment plan that now remove managed PostgreSQL from local, CI, and QA scope.

**Evidence**:
- infra/main.bicep defines PostgreSQL parameters and derived names, and wires the `data` module into compute.
- infra/modules/data.bicep provisions `Microsoft.DBforPostgreSQL/flexibleServers` and its database.
- infra/parameters/qa.bicepparam still requires `POSTGRES_ADMIN_PASSWORD`.

**Impact**:
- QA deployment behavior does not match the planning packet.
- Cost and deployment failure modes still include managed PostgreSQL.
- Implementation teams would be coding against a stale deployment contract.

### 2. Container Apps compute wiring still injects PostgreSQL runtime variables into web, worker, and setup job containers

**Severity**: High

The compute module still passes `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, and `PGPASSWORD`, and stores a PostgreSQL password secret. That conflicts with the newly documented SQLite runtime contract requiring a single environment-driven SQLite path.

**Evidence**:
- infra/modules/compute.bicep shared environment variables remain PostgreSQL-based.
- infra/modules/compute.bicep shared secrets still include `postgres-password`.

**Impact**:
- Even if documentation says SQLite, the deployed apps would still boot against PostgreSQL assumptions.
- The setup job is not yet aligned with a SQLite-specific runtime profile.

### 3. Deploy QA workflow still depends on PostgreSQL secrets and passes them into infrastructure deployment

**Severity**: High

The deployment workflow continues to pass `postgresAdminPassword` into both `what-if` and `deployment group create`. This is inconsistent with the updated deployment plan and means the live delivery path still assumes PostgreSQL exists.

**Evidence**:
- .github/workflows/deploy-qa.yml passes `postgresAdminPassword` during Bicep what-if.
- .github/workflows/deploy-qa.yml passes `postgresAdminPassword` during deployment.

**Impact**:
- The live pipeline cannot be considered aligned with the SQLite planning baseline.
- Secret inventory and operator steps remain larger than the current plan allows.

### 4. CI workflow still provisions a PostgreSQL service even though test settings already use in-memory SQLite

**Severity**: Medium

The CI workflow starts a PostgreSQL service and exports PG connection variables, but the test settings file already overrides the database to SQLite in-memory. This is at best dead configuration and at worst misleading configuration drift.

**Evidence**:
- .github/workflows/ci.yml defines a `postgres` service and PG environment variables.
- resumetailor/settings/test.py explicitly forces SQLite in-memory.

**Impact**:
- CI cost and runtime complexity are higher than necessary.
- The workflow suggests a database dependency that the test settings do not actually use.

### 5. The current Bicep design has an additional secret-handling issue unrelated to SQLite planning

**Severity**: Medium

The data module outputs a Redis primary key using `listKeys()`, which Bicep flags as a secret-leak pattern in outputs.

**Evidence**:
- infra/modules/data.bicep outputs `redisPrimaryKey` from `redisCache.listKeys().primaryKey`.

**Impact**:
- The current template is not clean even before the SQLite migration work begins.
- This should be corrected during the eventual infra implementation pass.

## Overall Assessment

The live Azure deployment artifacts and GitHub Actions files are internally consistent with the old PostgreSQL-based implementation path, but they are not consistent with the newly approved SQLite planning baseline. In other words, the repo currently contains two coherent but conflicting states:

1. Planning artifacts now describe SQLite for local, CI, and QA.
2. Live infrastructure and deployment automation still implement PostgreSQL for QA and carry leftover PostgreSQL setup in CI.

## Required Alignment Work

1. Remove PostgreSQL module usage and parameters from the Azure IaC layer.
2. Replace PostgreSQL runtime environment wiring in compute with a SQLite path contract.
3. Remove PostgreSQL secret inputs from the deployment workflow.
4. Simplify CI to match the existing SQLite-backed test settings.
5. Fix the Redis secret output pattern during the same infra pass.

## Ownership Note

Engineer F owns closure of these findings as part of the SQLite runtime alignment lane. Engineer E remains a dependency for QA validation and deployment readiness, but the contract-alignment work itself is assigned to Engineer F.

## Recommendation

Do not treat the current Azure and GitHub Actions files as aligned with the approved plan. They should be updated together in the future implementation phase under the SQLite migration stories, not piecemeal.