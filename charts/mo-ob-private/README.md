## MO OB Private Deploy Chart

original issue: https://github.com/matrixorigin/MO-Cloud/issues/2266

---


## Quick Start

To Set up a private ob:

1. clone this repo

2. set env:
   
    ```
    OBNS=mo-ob
    S3_ENDPOINT=s3-endpoint
    S3_ACCESS_KEY=s3-access-key
    S3_SECRET_KEY=s3-secret-key
    S3_BUCKET=bucket_name
    STORAGE_CLASS=storage_class
    PROM_STORAGE_SIZE=40Gi
    GRAFANA_USER=admin
    GRAFANA_PWD=matrixorigin2021
    ```

3. run

```
	helm install -n ${OBNS} \
		--set mo-ob-opensource.loki.loki.storage.bucketNames.chunks=${S3_BUCKET} \
		--set mo-ob-opensource.loki.loki.storage.s3.endpoint=${S3_ENDPOINT} \
		--set mo-ob-opensource.loki.loki.storage.s3.accessKeyId=${S3_ACCESS_KEY} \
		--set mo-ob-opensource.loki.loki.storage.s3.secretAccessKey=${S3_SECRET_KEY} \
		--set mo-ob-opensource.loki.write.persistence.storageClass=${STORAGE_CLASS} \
		--set mo-ob-opensource.loki.read.persistence.storageClass=${STORAGE_CLASS} \
		--set mo-ob-opensource.loki.backend.persistence.storageClass=${STORAGE_CLASS} \
		--set mo-ob-opensource.kube-prometheus-stack.prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=${STORAGE_CLASS} \
		--set mo-ruler-stack.grafana.persistence.storageClassName=${STORAGE_CLASS} \
		--set mo-ruler-stack.grafana.adminUser=${GRAFANA_USER} \
		--set mo-ruler-stack.grafana.adminPassword=${GRAFANA_PWD} \
		--set mo-ob-opensource.kube-prometheus-stack.prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=${PROM_STORAGE_SIZE} \
		mo-ob-private charts/mo-ob-private
```

## Detail

This is a helm chart for mo ob in private deployment environment, support basic feature but not alerting:

- logs / metrics data scraping
- general dashboards are provisioned (in grafana) for monitoring

These component are enabled defalut in chart:

| app                                            | limit              |
| ------------------------------------------------ | -------------------- |
| loki-read *1                                   | CPU: 1000 MEM: 3G  |
| loki-write *1                                  | CPU: 1000 MEM: 1G  |
| loki-backend *1                                | CPU: 200 MEM: 250M |
| loki-gateway *1                                | CPU: 1000 MEM: 1G  |
| prometheus *1                                  | CPU: 1000 MEM: 2G  |
| prometheus-operator (not set, avg. 50/200M) *1 | CPU: 200 MEM: 400M |
| promtail (not set, avg. 10/100M) * x           | CPU: 200 MEM: 200M |
| node-exporter (not set, avg. 10/20M) * x       | CPU: 200 MEM: 100M |
| grafana (not set, avg. 50/400M) *1             | CPU: 500 MEM: 1G   |