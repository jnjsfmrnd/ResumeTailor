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

@description('Maximum replicas for the web container app. Must be 1 when using SQLite storage.')
param webMaxReplicas int = 1

@description('Minimum replicas for the worker container app.')
param workerMinReplicas int = 1

@description('Maximum replicas for the worker container app. Must be 1 when using SQLite storage.')
param workerMaxReplicas int = 1

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
var redisCacheName = 'redis-resumetailor-${environmentName}'
var storageAccountName = 'stresumetailor${environmentName}'
var keyVaultName = 'kv-resumetailor-${environmentName}'
var setupJobName = 'job-setup-resumetailor-${environmentName}'

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
    sqliteStorageShareName: storage.outputs.sqliteShareName
    redisHost: data.outputs.redisCacheHostName
    redisPrimaryKey: data.outputs.redisPrimaryKey
    djangoSecretKey: djangoSecretKey
    githubModelsApiKey: githubModelsApiKey
    djangoAllowedHosts: djangoAllowedHosts
    storageAccountName: storageAccountName
    storageAccountKey: storageAccountKey
    setupJobName: setupJobName
  }
}

// --- Outputs ---
output registryLoginServer string = registry.outputs.loginServer
output webAppFqdn string = compute.outputs.webAppFqdn
output keyVaultUri string = secrets.outputs.keyVaultUri
output storageAccountName string = storage.outputs.storageAccountName
output setupJobName string = compute.outputs.setupJobName
