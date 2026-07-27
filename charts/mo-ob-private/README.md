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

This is a Helm chart for the private observability runtime:

- Prometheus, Grafana, Alertmanager and Loki workloads
- infrastructure exporters and log collectors
- storage, Services and Prometheus Operator CRDs

Scrape definitions, dashboards and alert rules are installed by the companion
`ob-ops` integration Chart.

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

## Monitoring content integration

`mo-ob-private` is the base observability stack. It installs Prometheus,
Grafana, Alertmanager, Loki and infrastructure collectors.

The companion `ob-ops` integration Chart owns every scrape and content
resource: Kubernetes, monitoring-stack, Loki, MatrixOne, MOI and MinIO
`ServiceMonitor` resources, all `PrometheusRule` resources and all dashboard
ConfigMaps. This base Chart owns only workloads, Services, storage and the
Prometheus Operator CRDs. It intentionally renders no `ServiceMonitor`,
`PodMonitor`, `PrometheusRule`, dashboard ConfigMap or
`additionalScrapeConfigs`.

The Services created by this Chart keep stable labels and named metrics ports
so the integration Chart can discover them without hard-coded ClusterIP
addresses. This split gives every scrape and content resource one Helm owner
and lets the integration release be enabled, upgraded or removed without
restarting Prometheus, Grafana or Loki.

Grafana's dashboard sidecar remains enabled and honors the `grafana_folder`
annotation on ConfigMaps created by the integration chart. It uses
`k8s-sidecar 2.8.1` with 10-second list reconciliation, while Grafana's file
provider reconciles every 30 seconds. Helm uninstall therefore removes the
corresponding provisioned dashboards even if Kubernetes watch events are
missed. Grafana API/UI cleanup may take 40-60 seconds after the Helm resources
have been deleted.

Loki uses TSDB schema v13. Table Manager stays disabled; 30-day retention is
implemented by the compactor with `retention_period: 720h`. Override that value
for customer-specific retention requirements.
