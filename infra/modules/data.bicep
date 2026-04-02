targetScope = 'resourceGroup'

@description('Azure region for this resource.')
param location string

@description('Name for the PostgreSQL server.')
param postgresServerName string

@description('PostgreSQL admin username.')
param postgresAdminUser string

@description('PostgreSQL admin password.')
@secure()
param postgresAdminPassword string

@description('PostgreSQL SKU name.')
param postgresSku string = 'Standard_B1ms'

@description('High availability mode.')
@allowed(['Disabled', 'ZoneRedundant', 'SameZone'])
param postgresHaMode string = 'Disabled'

@description('Backup retention in days.')
param postgresBackupDays int = 7

@description('Name for the Redis cache.')
param redisCacheName string

@description('Redis SKU name.')
@allowed(['Basic', 'Standard', 'Premium'])
param redisSku string = 'Basic'

@description('Redis SKU capacity (0=250MB, 1=1GB, ...).')
param redisSkuCapacity int = 0

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2022-12-01' = {
  name: postgresServerName
  location: location
  sku: {
    name: postgresSku
    tier: 'Burstable'
  }
  properties: {
    administratorLogin: postgresAdminUser
    administratorLoginPassword: postgresAdminPassword
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: postgresBackupDays
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: postgresHaMode
    }
    version: '15'
  }
}

resource postgresDb 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2022-12-01' = {
  parent: postgresServer
  name: 'resumetailor'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.UTF8'
  }
}

resource postgresFirewall 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2022-12-01' = {
  parent: postgresServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource redisCache 'Microsoft.Cache/redis@2023-08-01' = {
  name: redisCacheName
  location: location
  properties: {
    sku: {
      name: redisSku
      family: redisSku == 'Premium' ? 'P' : 'C'
      capacity: redisSkuCapacity
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
  }
}

output postgresServerId string = postgresServer.id
output postgresServerFqdn string = postgresServer.properties.fullyQualifiedDomainName
output postgresServerName string = postgresServer.name
output redisCacheId string = redisCache.id
output redisCacheHostName string = redisCache.properties.hostName
output redisPrimaryKey string = redisCache.listKeys().primaryKey
