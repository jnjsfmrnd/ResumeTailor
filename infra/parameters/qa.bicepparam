using '../main.bicep'

param environmentName = 'qa'
param location = 'eastus'
param imageTag = 'latest'

// Compute scaling
param webMinReplicas = 1
param webMaxReplicas = 3
param workerMinReplicas = 1
param workerMaxReplicas = 2

// PostgreSQL
param postgresSku = 'Standard_B1ms'
param postgresHaMode = 'Disabled'
param postgresBackupDays = 7
param postgresAdminUser = 'resumetailor'

// These secure params are injected at deploy time from Key Vault references.
// They must be supplied via --parameters in the deployment command and must NOT
// be hard-coded here.
param postgresAdminPassword = readEnvironmentVariable('POSTGRES_ADMIN_PASSWORD')
param storageAccountKey = readEnvironmentVariable('AZURE_STORAGE_KEY')
param djangoSecretKey = readEnvironmentVariable('DJANGO_SECRET_KEY')
param githubModelsApiKey = readEnvironmentVariable('GITHUB_MODELS_API_KEY')
param djangoAllowedHosts = readEnvironmentVariable('DJANGO_ALLOWED_HOSTS', 'localhost')

// Redis
param redisSku = 'Basic'
param redisSkuCapacity = 0

// Storage
param storageReplication = 'LRS'
