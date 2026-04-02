targetScope = 'resourceGroup'

@description('Environment name (e.g. qa).')
param environmentName string = 'qa'

@description('Azure region for all resources.')
param location string = 'eastus'

@description('Image tag to deploy.')
param imageTag string = 'latest'

// --- Compute scaling ---
@description('Minimum replicas for the web container app.')
param webMinReplicas int = 1

@description('Maximum replicas for the web container app.')
param webMaxReplicas int = 3

@description('Minimum replicas for the worker container app.')
param workerMinReplicas int = 1

@description('Maximum replicas for the worker container app.')
param workerMaxReplicas int = 2

// --- PostgreSQL ---
@description('PostgreSQL SKU name.')
param postgresSku string = 'Standard_B1ms'

@description('PostgreSQL high-availability mode.')
@allowed(['Disabled', 'ZoneRedundant', 'SameZone'])
param postgresHaMode string = 'Disabled'

@description('PostgreSQL backup retention in days.')
param postgresBackupDays int = 7

@description('PostgreSQL admin username.')
param postgresAdminUser string = 'resumetailor'

@description('PostgreSQL admin password (injected via Key Vault ref at deploy time).')
@secure()
param postgresAdminPassword string

// --- Redis ---
@description('Redis SKU name.')
@allowed(['Basic', 'Standard', 'Premium'])
param redisSku string = 'Basic'

@description('Redis SKU capacity.')
param redisSkuCapacity int = 0

// --- Storage ---
@description('Storage account replication type.')
@allowed(['LRS', 'GRS', 'ZRS'])
param storageReplication string = 'LRS'

@description('Azure Storage account key (injected via Key Vault ref at deploy time).')
@secure()
param storageAccountKey string

// --- App secrets ---
@description('Django secret key (injected via Key Vault ref at deploy time).')
@secure()
param djangoSecretKey string

@description('GitHub Models API key (app key, injected via Key Vault ref at deploy time).')
@secure()
param githubModelsApiKey string

@description('Allowed hostnames for Django (space-separated).')
param djangoAllowedHosts string

// --- Derived resource names (fixed per AZURE-DEPLOYMENT-0001 §9) ---
var registryName = 'crresumetailor'
var containerAppsEnvName = 'cae-resumetailor-${environmentName}'
var webAppName = 'ca-web-resumetailor-${environmentName}'
var workerAppName = 'ca-worker-resumetailor-${environmentName}'
var postgresServerName = 'psql-resumetailor-${environmentName}'
var redisCacheName = 'redis-resumetailor-${environmentName}'
var storageAccountName = 'stresumetailor${environmentName}'
var keyVaultName = 'kv-resumetailor-${environmentName}'

// --- Modules ---

module registry 'modules/registry.bicep' = {
  name: 'registry'
  params: {
    location: location
    registryName: registryName
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    location: location
    storageAccountName: storageAccountName
    replication: storageReplication
  }
}

module secrets 'modules/secrets.bicep' = {
  name: 'secrets'
  params: {
    location: location
    keyVaultName: keyVaultName
  }
}

module data 'modules/data.bicep' = {
  name: 'data'
  params: {
    location: location
    postgresServerName: postgresServerName
    postgresAdminUser: postgresAdminUser
    postgresAdminPassword: postgresAdminPassword
    postgresSku: postgresSku
    postgresHaMode: postgresHaMode
    postgresBackupDays: postgresBackupDays
    redisCacheName: redisCacheName
    redisSku: redisSku
    redisSkuCapacity: redisSkuCapacity
  }
}

module compute 'modules/compute.bicep' = {
  name: 'compute'
  params: {
    location: location
    containerAppsEnvName: containerAppsEnvName
    webAppName: webAppName
    workerAppName: workerAppName
    registryLoginServer: registry.outputs.loginServer
    registryName: registryName
    imageTag: imageTag
    webMinReplicas: webMinReplicas
    webMaxReplicas: webMaxReplicas
    workerMinReplicas: workerMinReplicas
    workerMaxReplicas: workerMaxReplicas
    postgresHost: data.outputs.postgresServerFqdn
    postgresAdminUser: postgresAdminUser
    postgresAdminPassword: postgresAdminPassword
    redisHost: data.outputs.redisCacheHostName
    redisPrimaryKey: data.outputs.redisPrimaryKey
    djangoSecretKey: djangoSecretKey
    githubModelsApiKey: githubModelsApiKey
    djangoAllowedHosts: djangoAllowedHosts
    storageAccountName: storageAccountName
    storageAccountKey: storageAccountKey
  }
}

// --- Outputs ---
output registryLoginServer string = registry.outputs.loginServer
output webAppFqdn string = compute.outputs.webAppFqdn
output keyVaultUri string = secrets.outputs.keyVaultUri
output storageAccountName string = storage.outputs.storageAccountName
