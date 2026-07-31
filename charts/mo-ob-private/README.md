## MO OB Private Deploy Chart

original issue: https://github.com/matrixorigin/MO-Cloud/issues/2266

---


## Quick Start

`mo-ob-private` installs the observability stack only. It does not install or
manage DirectPV, a StorageClass, MinIO, S3, or object-storage buckets.

Before installation, prepare:

- an existing dynamic `ReadWriteOnce` StorageClass, such as the class provided
  by DirectPV;
- an independently deployed S3-compatible service and an existing Loki bucket;
- credentials that can read and write that bucket.

Pass those site-specific values explicitly:

```bash
STORAGE_CLASS=directpv-storage-class
S3_ENDPOINT=http://minio.minio-tenant.svc.cluster.local:80
S3_BUCKET=loki
S3_ACCESS_KEY=replace-me
S3_SECRET_KEY=replace-me
GRAFANA_USER=admin
GRAFANA_PASSWORD=replace-me

helm upgrade --install mo-ob-private charts/mo-ob-private \
  --namespace mo-ob \
  --create-namespace \
  --set mo-ob-opensource.loki.minio.enabled=false \
  --set-string mo-ob-opensource.loki.loki.storage.bucketNames.chunks="${S3_BUCKET}" \
  --set-string mo-ob-opensource.loki.loki.storage.s3.endpoint="${S3_ENDPOINT}" \
  --set-string mo-ob-opensource.loki.loki.storage.s3.accessKeyId="${S3_ACCESS_KEY}" \
  --set-string mo-ob-opensource.loki.loki.storage.s3.secretAccessKey="${S3_SECRET_KEY}" \
  --set-string mo-ob-opensource.loki.write.persistence.storageClass="${STORAGE_CLASS}" \
  --set-string mo-ob-opensource.loki.read.persistence.storageClass="${STORAGE_CLASS}" \
  --set-string mo-ob-opensource.loki.backend.persistence.storageClass="${STORAGE_CLASS}" \
  --set-string mo-ob-opensource.kube-prometheus-stack.prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName="${STORAGE_CLASS}" \
  --set-string mo-ruler-stack.grafana.persistence.storageClassName="${STORAGE_CLASS}" \
  --set-string mo-ruler-stack.grafana.adminUser="${GRAFANA_USER}" \
  --set-string mo-ruler-stack.grafana.adminPassword="${GRAFANA_PASSWORD}" \
  --atomic \
  --wait \
  --timeout 20m
```

The companion `ob-ops/customer-installer/mo-kube-monitoring` helper provides
preflight checks and a single command that installs this base Chart followed
by the monitoring-content Chart. The helper stays outside both Chart packages.

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

## Customer compatibility contract

A portable installation requires the site to provide:

- a working Kubernetes API and Helm 3;
- a dynamic `ReadWriteOnce` StorageClass, passed explicitly to every persistent
  component;
- an independently managed S3/MinIO endpoint and pre-created Loki bucket;
- reachable images or a customer-provided offline image mirror;
- enough schedulable CPU, memory, and storage for the selected profile.

The Chart never creates, modifies, or deletes DirectPV, StorageClass, MinIO,
S3, or bucket resources. The installation values are the contract between the
site infrastructure and the monitoring stack.
