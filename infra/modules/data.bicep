targetScope = 'resourceGroup'

@description('Azure region for this resource.')
param location string

@description('Name for the Redis cache.')
param redisCacheName string

@description('Redis SKU name.')
@allowed(['Basic', 'Standard', 'Premium'])
param redisSku string = 'Basic'

@description('Redis SKU capacity (0=250MB, 1=1GB, ...).')
param redisSkuCapacity int = 0

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

output redisCacheId string = redisCache.id
output redisCacheHostName string = redisCache.properties.hostName

@secure()
output redisPrimaryKey string = redisCache.listKeys().primaryKey
