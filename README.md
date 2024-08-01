# Observability
MOCloud Observability Charts

## 安装

### Helm 安装

添加 Helm 仓库

```shell
helm repo add mo-ob https://matrixorigin.github.io/observability-charts
```

更新仓库

```shell
helm repo update
```

查看版本

```shell
helm search repo mo-ob/mo-agent-stack --versions --devel
helm search repo mo-ob/mo-ruler-stack --versions --devel
helm search repo mo-ob/mo-ob-opensource --versions --devel
helm search repo mo-ob/mo-ob-private --versions --devel
```

安装 MO Agent

```shell
helm install <RELEASE_NAME> mo-ob/mo-agent-stack --version <VERSION>
```


安装 MO Ruler

```shell
helm install <RELEASE_NAME> mo-ob/mo-ruler-stack --version <VERSION>
```

安装 MO OB

```shell
helm install <RELEASE_NAME> mo-ob/mo-ob-opensource --version <VERSION>
```

安装 MO OB Private (私有化)

1. 设置必要的 env 参数用于安装:
   
```shell
OBNS=mo-ob
S3_ENDPOINT=<your-s3-endpoint>
S3_ACCESS_KEY=<your-s3-access-key>
S3_SECRET_KEY=<your-s3-secret-key>
S3_BUCKET=<your-bucket-name>
STORAGE_CLASS=<your-storage-class>
PROM_STORAGE_SIZE=40Gi
GRAFANA_USER=<your-admin-user>
GRAFANA_PWD=<your-grafana-pwd>
```

2. 执行 helm 安装

```shell
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
    <RELEASE_NAME> mo-ob/mo-ob-private --version <VERSION>
```
