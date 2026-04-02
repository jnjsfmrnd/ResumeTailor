targetScope = 'resourceGroup'

@description('Azure region for this resource.')
param location string

@description('Container Apps environment name.')
param containerAppsEnvName string

@description('Web container app name.')
param webAppName string

@description('Worker container app name.')
param workerAppName string

@description('Container Registry login server.')
param registryLoginServer string

@description('Container Registry name (for credentials lookup).')
param registryName string

@description('Image tag to deploy.')
param imageTag string = 'latest'

@description('Minimum replicas for the web app.')
param webMinReplicas int = 1

// SQLite on a shared Azure File Share does not support concurrent writers.
// Keep this at 1 for any environment using the SQLite-backed storage.
@description('Maximum replicas for the web app. Must be 1 when using SQLite storage.')
@maxValue(1)
param webMaxReplicas int = 1

@description('Minimum replicas for the worker app.')
param workerMinReplicas int = 1

// SQLite on a shared Azure File Share does not support concurrent writers.
// Keep this at 1 for any environment using the SQLite-backed storage.
@description('Maximum replicas for the worker app. Must be 1 when using SQLite storage.')
@maxValue(1)
param workerMaxReplicas int = 1

@description('SQLite database file path inside the container.')
param sqliteDbPath string = '/app/data/resumetailor.sqlite3'

@description('Azure Storage file share name for the SQLite data volume.')
param sqliteStorageShareName string

@description('Redis hostname.')
param redisHost string

@description('Redis primary key.')
@secure()
param redisPrimaryKey string

@description('Django secret key.')
@secure()
param djangoSecretKey string

@description('GitHub Models API key (app key).')
@secure()
param githubModelsApiKey string

@description('Allowed hostnames for Django (space-separated).')
param djangoAllowedHosts string

@description('Azure Storage account name.')
param storageAccountName string

@description('Azure Storage account key.')
@secure()
param storageAccountKey string

@description('Name for the one-off setup Container Apps Job (migrate + collectstatic).')
param setupJobName string

var registryCredentials = [
  {
    server: registryLoginServer
    username: registryName
    passwordSecretRef: 'registry-password'
  }
]

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: registryName
}

resource containerAppsEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerAppsEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
  }
}

resource containerAppsEnvStorage 'Microsoft.App/managedEnvironments/storages@2023-05-01' = {
  parent: containerAppsEnv
  name: 'sqlite-storage'
  properties: {
    azureFile: {
      accountName: storageAccountName
      accountKey: storageAccountKey
      shareName: sqliteStorageShareName
      accessMode: 'ReadWrite'
    }
  }
}

var sharedEnvVars = [
  { name: 'DJANGO_SETTINGS_MODULE', value: 'resumetailor.settings.qa' }
  { name: 'DJANGO_ALLOWED_HOSTS', value: djangoAllowedHosts }
  { name: 'DJANGO_SECRET_KEY', secretRef: 'django-secret-key' }
  { name: 'SQLITE_DB_PATH', value: sqliteDbPath }
  { name: 'CELERY_BROKER_URL', secretRef: 'redis-url' }
  { name: 'CELERY_RESULT_BACKEND', secretRef: 'redis-url' }
  { name: 'GITHUB_MODELS_API_KEY', secretRef: 'github-models-api-key' }
  { name: 'AZURE_STORAGE_ACCOUNT', value: storageAccountName }
  { name: 'AZURE_STORAGE_KEY', secretRef: 'storage-account-key' }
]

var sharedSecrets = [
  { name: 'django-secret-key', value: djangoSecretKey }
  { name: 'redis-url', value: 'rediss://:${redisPrimaryKey}@${redisHost}:6380/0' }
  { name: 'github-models-api-key', value: githubModelsApiKey }
  { name: 'storage-account-key', value: storageAccountKey }
  { name: 'registry-password', value: registry.listCredentials().passwords[0].value }
]

resource webApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: webAppName
  location: location
  dependsOn: [containerAppsEnvStorage]
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
      }
      registries: registryCredentials
      secrets: sharedSecrets
    }
    template: {
      containers: [
        {
          name: 'web'
          image: '${registryLoginServer}/resumetailor-web:${imageTag}'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: sharedEnvVars
          volumeMounts: [
            {
              volumeName: 'sqlite-data'
              mountPath: '/app/data'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health/'
                port: 8000
              }
              initialDelaySeconds: 15
              periodSeconds: 20
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health/ready/'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
          ]
        }
      ]
      volumes: [
        {
          name: 'sqlite-data'
          storageType: 'AzureFile'
          storageName: 'sqlite-storage'
        }
      ]
      scale: {
        minReplicas: webMinReplicas
        maxReplicas: webMaxReplicas
      }
    }
  }
}

resource workerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: workerAppName
  location: location
  dependsOn: [containerAppsEnvStorage]
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      registries: registryCredentials
      secrets: sharedSecrets
    }
    template: {
      containers: [
        {
          name: 'worker'
          image: '${registryLoginServer}/resumetailor-worker:${imageTag}'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: sharedEnvVars
          volumeMounts: [
            {
              volumeName: 'sqlite-data'
              mountPath: '/app/data'
            }
          ]
        }
      ]
      volumes: [
        {
          name: 'sqlite-data'
          storageType: 'AzureFile'
          storageName: 'sqlite-storage'
        }
      ]
      scale: {
        minReplicas: workerMinReplicas
        maxReplicas: workerMaxReplicas
      }
    }
  }
}

output containerAppsEnvId string = containerAppsEnv.id
output webAppFqdn string = webApp.properties.configuration.ingress.fqdn
output webAppId string = webApp.id
output workerAppId string = workerApp.id

// ---------------------------------------------------------------------------
// One-off setup job: runs Django migrate + collectstatic after every deploy.
// Triggered manually from the Deploy QA workflow via `az containerapp job start`.
// ---------------------------------------------------------------------------
resource setupJob 'Microsoft.App/jobs@2023-05-01' = {
  name: setupJobName
  location: location
  dependsOn: [containerAppsEnvStorage]
  properties: {
    environmentId: containerAppsEnv.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 600
      replicaRetryLimit: 0
      manualTriggerConfig: {
        replicaCompletionCount: 1
        parallelism: 1
      }
      registries: registryCredentials
      secrets: sharedSecrets
    }
    template: {
      containers: [
        {
          name: 'setup'
          image: '${registryLoginServer}/resumetailor-web:${imageTag}'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: sharedEnvVars
          volumeMounts: [
            {
              volumeName: 'sqlite-data'
              mountPath: '/app/data'
            }
          ]
          command: ['/bin/sh', '-c', 'python manage.py migrate --noinput && python manage.py collectstatic --noinput']
        }
      ]
      volumes: [
        {
          name: 'sqlite-data'
          storageType: 'AzureFile'
          storageName: 'sqlite-storage'
        }
      ]
    }
  }
}

output setupJobName string = setupJob.name
