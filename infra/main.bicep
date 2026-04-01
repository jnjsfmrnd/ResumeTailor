targetScope = 'resourceGroup'

@description('Planning-only infrastructure scaffold. No resources are provisioned in this file yet.')
param environmentName string = 'qa'

@description('Planning-only location scaffold.')
param location string = 'eastus'

output scaffoldStatus string = 'planning-only'
output scaffoldEnvironment string = environmentName
output scaffoldLocation string = location
