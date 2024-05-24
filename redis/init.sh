sysctl vm.overcommit_memory=1
redis-server /usr/local/etc/redis/redis.conf --bind 0.0.0.0 --requirepass ${REDIS_PASSWORD}