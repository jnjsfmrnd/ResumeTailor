targetScope = 'resourceGroup'

@description('Azure region for this resource.')
param location string

@description('Name for the Container Registry.')
param registryName string

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

output registryId string = registry.id
output loginServer string = registry.properties.loginServer
output registryName string = registry.name
