# MO OB 客户交付部署文档

## 1. 部署边界

本章部署 MO Observability 监控底座，使用客户已经准备好的外部 S3/MinIO。

本 Chart 负责：

- Prometheus、Prometheus Operator；
- Loki、Alloy、Promtail；
- Grafana、Alertmanager；
- node-exporter、kube-state-metrics。

本 Chart 不负责：

- 部署或修改客户的 MinIO/S3；
- 创建、扩容或删除客户的 StorageClass；
- 创建 Loki Bucket；
- 安装 MatrixOne/MOI 业务采集规则、告警规则和 Dashboard。

业务 ServiceMonitor、PrometheusRule 和 Dashboard 由配套的 `ob-ops` 内容
Chart 单独管理。底座健康后再安装内容 Chart。

## 2. 交付版本与完整性

正式交付包含：

| Chart | 版本 |
|---|---:|
| mo-ob-private | 1.0.5 |
| mo-ob-opensource | 1.0.11 |
| mo-ruler-stack | 1.1.0 |

正式交付必须同时提供：

```text
mo-ob-private-1.0.5.tgz
mo-ob-private-1.0.5.tgz.sha256
mo-ob-private-1.0.5.release-ref.txt
```

`release-ref.txt` 必须使用
`observability-charts-ref=<已审核的 40 位 Git commit SHA>` 格式记录固定提交。

发布时必须将下面占位符替换为已审核的固定提交，不得从持续变化的
分支或 Pull Request Head 直接构建客户包：

```bash
OBSERVABILITY_CHARTS_REF="<reviewed-40-character-commit-sha>"

if [[ ! "${OBSERVABILITY_CHARTS_REF}" =~ ^[0-9a-f]{40}$ ]]; then
  echo "错误：必须填写已审核的 40 位提交 SHA"
  exit 1
fi

git switch --detach "${OBSERVABILITY_CHARTS_REF}"
test "$(git rev-parse HEAD)" = "${OBSERVABILITY_CHARTS_REF}"
test -z "$(git status --porcelain)"
```

交付人必须在发布记录中同时保存 Chart 版本、Git SHA 和 tgz SHA-256。
客户部署只使用校验过的 `.tgz`，不直接从未提交工作树安装。

## 3. 客户现场参数表

部署前必须由客户确认以下参数，不能复制其他集群的值：

| 参数 | 客户填写 |
|---|---|
| Kubernetes 版本 | |
| CPU 架构 | amd64 / arm64 |
| StorageClass | |
| 是否为默认 StorageClass | |
| 是否支持动态 RWO PVC | |
| 是否支持 PVC 扩容 | |
| Loki write PVC 大小/副本数 | |
| Loki backend PVC 大小/副本数 | |
| Loki 保留时间 | |
| Prometheus PVC 大小/保留时间 | |
| Grafana PVC 大小 | |
| 各组件 CPU/内存 requests、limits | |
| S3/MinIO Endpoint | |
| Loki Bucket | |
| S3 是否使用 HTTPS | |
| 是否使用 Path Style | |
| 镜像来源 | 上游公网 / 客户 Harbor |
| Grafana Service 类型 | ClusterIP / NodePort / LoadBalancer |
| 是否配置 Grafana Ingress | 是 / 否 |
| Grafana NodePort（如使用） | |

当前 SimpleScalable 模式的持久化容量计算方式为：

```text
Loki write 副本数 × write PVC
+ Loki backend 副本数 × backend PVC
+ Prometheus 副本数 × Prometheus PVC
+ Grafana 副本数 × Grafana PVC
+ 现场预留空间
```

容量总数只是第一步，还必须确认存储拓扑、失败域和每个可调度节点的实际
可用空间。客户生产环境应根据日志写入量、指标基数、保留时间和故障恢复目标
做容量评估。

## 4. 安装前检查

本 Chart 默认 Namespace 为 `mo-ob`。如果客户使用自定义 Namespace，后续所有
Helm、Secret 和验收命令都必须使用同一个 `OBNS`；配套 `ob-ops`
安装器中的 `EXISTING_MONITORING_NAMESPACE` 也必须与之一致。同时必须在客户
values 文件中完整覆盖
`mo-ob-opensource.kube-prometheus-stack.prometheus.prometheusSpec.alertingEndpoints[0]`
对象，并把其中的 `namespace` 改为同一个 `OBNS`。不要只覆盖数组中的
`namespace` 字段，因为 Helm 会把数组项作为整体替换。

```bash
export OBNS="${OBNS:-mo-ob}"

for REQUIRED_COMMAND in \
  kubectl helm mc jq openssl tar grep sha256sum; do
  if ! command -v "${REQUIRED_COMMAND}" >/dev/null 2>&1; then
    echo "错误：缺少命令 ${REQUIRED_COMMAND}"
    exit 1
  fi
done

kubectl version
helm version
kubectl get nodes -o wide
kubectl get storageclass
kubectl get pvc -A
```

如果使用第 8 节的私有镜像流程，执行机还必须安装支持
`--password-stdin` 的 Docker CLI。

确认选定 StorageClass 支持动态创建 `ReadWriteOnce` PVC。不同 CSI 的剩余容量
查询方式不同，应使用客户存储厂商提供的工具检查，不能仅根据
`kubectl get storageclass` 判断剩余容量。

最终镜像清单在完成客户 values 后通过第 10 节的渲染结果取得。单独
Chart 默认使用上游镜像；通过 `ob-ops` 一键流程部署时，使用
`IMAGE_SOURCE=upstream|domestic` 选择已审核的镜像 profile。国内 profile
是公网加速路径，不是离线可用保证；仍必须从客户网络逐个验证精确的
repository、tag 和 CPU 架构。如果使用客户 Harbor，必须先完整同步这些
镜像。

## 5. 准备外部 S3/MinIO

由客户提前创建独立 Loki Bucket。不得与 MatrixOne、MOI 或其他业务共用
Bucket。

准备一个只能访问 Loki Bucket 的专用 AK/SK，并验证它至少具备：

- 列举 Bucket；
- 写入、读取、删除对象；
- 列举和中止分片上传。

在能够使用 MinIO Client 的受信任环境中执行写入、读取和删除验证。
下面的子 Shell 使用独立的临时 `MC_CONFIG_DIR` 和唯一 alias，成功或失败都会
删除测试对象、alias、临时配置和本地文件：

```bash
(
set -euo pipefail

read -rp 'S3/MinIO endpoint（http[s]://host:port）：' \
  LOKI_S3_ENDPOINT
read -rp '已创建的 Loki Bucket：' \
  LOKI_S3_BUCKET
read -rsp 'S3 Access Key：' \
  LOKI_S3_ACCESS_KEY
printf '\n'
read -rsp 'S3 Secret Key：' \
  LOKI_S3_SECRET_KEY
printf '\n'

MC_CONFIG_DIR="$(mktemp -d)"
chmod 0700 "${MC_CONFIG_DIR}"
MC_ALIAS="mo-ob-check-$$"
CHECK_OBJECT="mo-ob-preflight-$(date +%s)-$$.txt"
CHECK_FILE="$(mktemp)"

cleanup_ob_preflight() {
  mc --config-dir "${MC_CONFIG_DIR}" rm \
    "${MC_ALIAS}/${LOKI_S3_BUCKET}/${CHECK_OBJECT}" \
    >/dev/null 2>&1 || true
  mc --config-dir "${MC_CONFIG_DIR}" alias rm "${MC_ALIAS}" \
    >/dev/null 2>&1 || true
  rm -f -- "${CHECK_FILE}"
  find "${MC_CONFIG_DIR}" -depth -mindepth 1 -delete 2>/dev/null || true
  rmdir -- "${MC_CONFIG_DIR}" 2>/dev/null || true
}
trap cleanup_ob_preflight EXIT

mc --config-dir "${MC_CONFIG_DIR}" alias set "${MC_ALIAS}" \
  "${LOKI_S3_ENDPOINT}" \
  "${LOKI_S3_ACCESS_KEY}" \
  "${LOKI_S3_SECRET_KEY}"

printf 'mo-ob-preflight\n' >"${CHECK_FILE}"
mc --config-dir "${MC_CONFIG_DIR}" cp "${CHECK_FILE}" \
  "${MC_ALIAS}/${LOKI_S3_BUCKET}/${CHECK_OBJECT}"
mc --config-dir "${MC_CONFIG_DIR}" stat \
  "${MC_ALIAS}/${LOKI_S3_BUCKET}/${CHECK_OBJECT}"
mc --config-dir "${MC_CONFIG_DIR}" cat \
  "${MC_ALIAS}/${LOKI_S3_BUCKET}/${CHECK_OBJECT}" \
  >/dev/null
mc --config-dir "${MC_CONFIG_DIR}" rm \
  "${MC_ALIAS}/${LOKI_S3_BUCKET}/${CHECK_OBJECT}"
)
```

只有写入、读取和删除全部成功后才能继续。
如果 HTTPS S3/MinIO 使用私有 CA，必须通过已评审的现场 values 让所有
Loki 工作负载信任该 CA；不得为了规避证书错误而改用 HTTP 或关闭 TLS 校验。

## 6. 创建 Namespace 和外部存储 Secret

输入客户实际参数。命令不会显示 Secret Key：

```bash
(
set -euo pipefail

OBNS="${OBNS:-mo-ob}"

read -rp 'S3/MinIO endpoint（http[s]://host:port）：' \
  LOKI_S3_ENDPOINT
read -rp '已创建的 Loki Bucket：' \
  LOKI_S3_BUCKET
read -rsp 'S3 Access Key：' LOKI_S3_ACCESS_KEY
printf '\n'
read -rsp 'S3 Secret Key：' LOKI_S3_SECRET_KEY
printf '\n'

read -rp '是否使用 Path Style（true/false）[true]：' \
  LOKI_S3_FORCE_PATH_STYLE
LOKI_S3_FORCE_PATH_STYLE="${LOKI_S3_FORCE_PATH_STYLE:-true}"

case "${LOKI_S3_ENDPOINT}" in
  http://*)  LOKI_S3_INSECURE="true" ;;
  https://*) LOKI_S3_INSECURE="false" ;;
  *)
    echo "错误：Endpoint 必须以 http:// 或 https:// 开头"
    exit 1
    ;;
esac

case "${LOKI_S3_FORCE_PATH_STYLE}" in
  true|false) ;;
  *)
    echo "错误：Path Style 只能填写 true 或 false"
    exit 1
    ;;
esac

if [[ -z "${LOKI_S3_BUCKET}" || \
      -z "${LOKI_S3_ACCESS_KEY}" || \
      -z "${LOKI_S3_SECRET_KEY}" ]]; then
  echo "错误：Bucket、AK、SK 不能为空"
  exit 1
fi

kubectl create namespace "${OBNS}" \
  --dry-run=client \
  -o yaml |
kubectl apply -f -

SECRET_DIR="$(mktemp -d)"
chmod 0700 "${SECRET_DIR}"
cleanup_loki_secret_files() {
  rm -f -- \
    "${SECRET_DIR}/LOKI_S3_ENDPOINT" \
    "${SECRET_DIR}/LOKI_S3_BUCKET" \
    "${SECRET_DIR}/LOKI_S3_ACCESS_KEY" \
    "${SECRET_DIR}/LOKI_S3_SECRET_KEY" \
    "${SECRET_DIR}/LOKI_S3_FORCE_PATH_STYLE" \
    "${SECRET_DIR}/LOKI_S3_INSECURE"
  rmdir -- "${SECRET_DIR}" 2>/dev/null || true
}
trap cleanup_loki_secret_files EXIT

printf '%s' "${LOKI_S3_ENDPOINT}" >"${SECRET_DIR}/LOKI_S3_ENDPOINT"
printf '%s' "${LOKI_S3_BUCKET}" >"${SECRET_DIR}/LOKI_S3_BUCKET"
printf '%s' "${LOKI_S3_ACCESS_KEY}" >"${SECRET_DIR}/LOKI_S3_ACCESS_KEY"
printf '%s' "${LOKI_S3_SECRET_KEY}" >"${SECRET_DIR}/LOKI_S3_SECRET_KEY"
printf '%s' "${LOKI_S3_FORCE_PATH_STYLE}" >"${SECRET_DIR}/LOKI_S3_FORCE_PATH_STYLE"
printf '%s' "${LOKI_S3_INSECURE}" >"${SECRET_DIR}/LOKI_S3_INSECURE"

kubectl -n "${OBNS}" create secret generic mo-ob-loki-s3 \
  --from-file="${SECRET_DIR}/LOKI_S3_ENDPOINT" \
  --from-file="${SECRET_DIR}/LOKI_S3_BUCKET" \
  --from-file="${SECRET_DIR}/LOKI_S3_ACCESS_KEY" \
  --from-file="${SECRET_DIR}/LOKI_S3_SECRET_KEY" \
  --from-file="${SECRET_DIR}/LOKI_S3_FORCE_PATH_STYLE" \
  --from-file="${SECRET_DIR}/LOKI_S3_INSECURE" \
  --dry-run=client \
  -o yaml |
kubectl apply -f -
)
```

只检查键名，不显示值：

```bash
kubectl -n "${OBNS}" get secret mo-ob-loki-s3 -o json |
jq '{type: .type, keys: (.data | keys)}'
```

预期包含 6 个键：

```text
LOKI_S3_ENDPOINT
LOKI_S3_BUCKET
LOKI_S3_ACCESS_KEY
LOKI_S3_SECRET_KEY
LOKI_S3_FORCE_PATH_STYLE
LOKI_S3_INSECURE
```

## 7. 创建 Grafana 管理员 Secret

先在客户密码管理系统中创建并保存一个不少于 16 个字符的密码。然后输入同一个
密码创建或更新 Secret：

```bash
(
set -euo pipefail

OBNS="${OBNS:-mo-ob}"
read -rp 'Grafana 管理员用户名 [admin]：' GRAFANA_ADMIN_USER
GRAFANA_ADMIN_USER="${GRAFANA_ADMIN_USER:-admin}"
read -rsp '请输入密码管理系统中已保存的 Grafana 密码：' \
  GRAFANA_ADMIN_PASSWORD
printf '\n'

if (( ${#GRAFANA_ADMIN_PASSWORD} < 16 )) || \
   [[ "${GRAFANA_ADMIN_PASSWORD}" == "${GRAFANA_ADMIN_USER}" ]]; then
  echo "错误：Grafana 密码必须至少 16 位且不能与用户名相同"
  exit 1
fi

SECRET_DIR="$(mktemp -d)"
chmod 0700 "${SECRET_DIR}"
cleanup_grafana_secret_files() {
  rm -f -- "${SECRET_DIR}/admin-user" "${SECRET_DIR}/admin-password"
  rmdir -- "${SECRET_DIR}" 2>/dev/null || true
}
trap cleanup_grafana_secret_files EXIT

printf '%s' "${GRAFANA_ADMIN_USER}" >"${SECRET_DIR}/admin-user"
printf '%s' "${GRAFANA_ADMIN_PASSWORD}" >"${SECRET_DIR}/admin-password"

kubectl -n "${OBNS}" create secret generic mo-ob-grafana-admin \
  --from-file="admin-user=${SECRET_DIR}/admin-user" \
  --from-file="admin-password=${SECRET_DIR}/admin-password" \
  --dry-run=client -o yaml | kubectl apply -f -
)
```

不要把密码写入 values、Shell 脚本、工单或交付文档。重复执行会使用本次
输入值更新 Secret；轮换必须先更新密码管理系统，再更新 Secret，并在维护窗口内
滚动重启和验证 Grafana。

## 8. 私有镜像 Secret（可选）

默认交付路径使用上游公网镜像。客户节点能够访问第 10 节渲染出的所有镜像时，
跳过本节。

如果客户要求使用私有 Harbor，交付方必须同时提供经过 `helm template` 验证的
`values-registry.yaml`，其中包含全部启用组件的镜像 repository、tag、CPU 架构和
`imagePullSecrets` 映射。不能只创建 Secret，也不能只替换 Registry 主机名。

`imagePullSecret` 是 Namespace 级资源，必须创建在实际的 `OBNS`（默认为
`mo-ob`）；其他 Namespace 中的同名 Secret 不能被复用。如果配套内容 release
在其他 Namespace 运行可选镜像，还必须在该 Namespace 重新创建并显式引用
对应 Secret。下面流程使用临时
Docker config 和 `--password-stdin`，不把 Harbor
密码放入进程参数：

```bash
(
set -euo pipefail

OBNS="${OBNS:-mo-ob}"
read -rp 'Harbor Registry（host[:port]）：' HARBOR_REGISTRY
read -rp 'Harbor 用户名：' HARBOR_USERNAME
read -rsp 'Harbor 密码：' HARBOR_PASSWORD
echo

if [[ -z "${HARBOR_REGISTRY}" || \
      -z "${HARBOR_USERNAME}" || \
      -z "${HARBOR_PASSWORD}" ]]; then
  echo "错误：Harbor 地址、用户名和密码不能为空"
  exit 1
fi

REGISTRY_DIR="$(mktemp -d)"
chmod 0700 "${REGISTRY_DIR}"
cleanup_registry_config() {
  docker --config "${REGISTRY_DIR}" logout "${HARBOR_REGISTRY}" \
    >/dev/null 2>&1 || true
  find "${REGISTRY_DIR}" -depth -mindepth 1 -delete 2>/dev/null || true
  rmdir -- "${REGISTRY_DIR}" 2>/dev/null || true
}
trap cleanup_registry_config EXIT

printf '%s' "${HARBOR_PASSWORD}" | \
  docker --config "${REGISTRY_DIR}" login "${HARBOR_REGISTRY}" \
    --username "${HARBOR_USERNAME}" \
    --password-stdin
chmod 0600 "${REGISTRY_DIR}/config.json"

kubectl -n "${OBNS}" create secret generic harbor-image-secret \
  --type=kubernetes.io/dockerconfigjson \
  --from-file=".dockerconfigjson=${REGISTRY_DIR}/config.json" \
  --dry-run=client -o yaml | kubectl apply -f -
)
```

如果没有与该交付包、CPU 架构和客户 Harbor 一一对应的
`values-registry.yaml`，就不能宣称私有镜像路径已经支持。
如果 Harbor 使用私有 CA，还必须让每个 Kubernetes 节点的容器运行时信任该
CA；`imagePullSecret` 只解决认证，不解决证书信任。

## 9. 创建客户 values

从交付 Chart 中提取示例：

```bash
(
set -euo pipefail

sha256sum --check mo-ob-private-1.0.5.tgz.sha256

if [[ -e values-customer.yaml ]]; then
  echo "错误：values-customer.yaml 已存在，请先备份或改用新文件名"
  exit 1
fi

tar -xOf ./mo-ob-private-1.0.5.tgz \
  mo-ob-private/values-customer.yaml.example \
  > values-customer.yaml

vi values-customer.yaml
)
```

必须根据客户现场修改：

- Loki、Prometheus、Grafana 的副本数、资源和保留时间；
- Loki write/backend StorageClass 和 PVC 大小；
- Prometheus StorageClass、PVC 大小和 retention；
- Grafana StorageClass 和 PVC 大小；
- Grafana Service 类型或 Ingress；
- NodePort（如果指定，必须先检查未占用）。

Secret 值不在该文件中。values 中只保留 Loki 运行时环境变量占位符。
示例中的单副本、容量和资源只是编辑工作表，不是生产推荐值。评审人必须将：

```yaml
customerSizingApproved: false
```

在交付记录中登记变更单、评审人和评审日期后，改为 YAML 布尔值：

```yaml
customerSizingApproved: true
```

不要给 `true` 加引号，也不要使用 `--skip-schema-validation`。该字段由 Chart
Schema 强制校验；未完成评审时，第 10 节会拒绝继续。

默认 `ClusterIP` 最适合生产基线。如果要使用 NodePort 或 LoadBalancer，只能修改
`mo-ruler-stack.grafana.service.type`。Ingress 不是 Service 类型；使用 Ingress 时
保持 `service.type: ClusterIP`，并单独配置：

```yaml
mo-ruler-stack:
  grafana:
    service:
      type: ClusterIP
    ingress:
      enabled: true
      hosts:
        - grafana.customer.example
      tls:
        - secretName: grafana-customer-tls
          hosts:
            - grafana.customer.example
```

Ingress 域名、TLS Secret 和 IngressClass 必须按客户现场调整。

## 10. 渲染和安全检查

```bash
(
set -euo pipefail

OBNS="${OBNS:-mo-ob}"
PACKAGE="./mo-ob-private-1.0.5.tgz"
VALUES_FILE="./values-customer.yaml"
RELEASE_REF_FILE="./mo-ob-private-1.0.5.release-ref.txt"
RENDERED_MANIFEST="$(mktemp)"
trap 'rm -f -- "${RENDERED_MANIFEST}"' EXIT

sha256sum --check "${PACKAGE}.sha256"

if [[ ! -f "${RELEASE_REF_FILE}" ]] || \
   ! grep -Eq '^observability-charts-ref=[0-9a-f]{40}$' \
     "${RELEASE_REF_FILE}"; then
  echo "错误：缺少已审核的固定提交 SHA 记录"
  exit 1
fi

if ! grep -Eq '^customerSizingApproved:[[:space:]]+true[[:space:]]*$' \
     "${VALUES_FILE}"; then
  echo "错误：生产容量与资源评审尚未确认"
  exit 1
fi

HELM_VALUE_ARGS=(-f "${VALUES_FILE}")

if [[ -f ./values-registry.yaml ]]; then
  HELM_VALUE_ARGS+=(-f ./values-registry.yaml)
fi

helm lint "${PACKAGE}" \
  "${HELM_VALUE_ARGS[@]}"

helm template mo-ob-private "${PACKAGE}" \
  --namespace "${OBNS}" \
  "${HELM_VALUE_ARGS[@]}" \
  >"${RENDERED_MANIFEST}"

if grep -Eq \
  'obtest-|test-bucket|admin:admin|smtp\.exmail|it@matrixorigin|moc-warning|baseAuthChecksum: required|cmVxdWlyZQo=' \
  "${RENDERED_MANIFEST}"; then
  echo "错误：渲染结果包含旧测试值或弱凭据"
  exit 1
fi

if grep -Eq \
  'app\.kubernetes\.io/name: minio|kind: Tenant' \
  "${RENDERED_MANIFEST}"; then
  echo "错误：渲染结果意外包含内置 MinIO"
  exit 1
fi

if grep -Eq \
  'vm-additional-scrape-configs|vmsingle-.*victoria-metrics|storageClass(Name)?:[[:space:]]*""' \
  "${RENDERED_MANIFEST}"; then
  echo "错误：渲染结果包含已关闭组件或禁用动态供给的空 StorageClass"
  exit 1
fi

if [[ -f ./values-registry.yaml ]] && \
   ! grep -Fq 'name: harbor-image-secret' \
     "${RENDERED_MANIFEST}"; then
  echo "错误：私有镜像 values 没有让工作负载引用 harbor-image-secret"
  exit 1
fi

for REQUIRED_VALUE in \
  '${LOKI_S3_ENDPOINT}' \
  '${LOKI_S3_BUCKET}' \
  '${LOKI_S3_ACCESS_KEY}' \
  '${LOKI_S3_SECRET_KEY}'; do
  if ! grep -Fq "${REQUIRED_VALUE}" \
    "${RENDERED_MANIFEST}"; then
    echo "错误：缺少安全环境变量占位符 ${REQUIRED_VALUE}"
    exit 1
  fi
done

echo "Helm 渲染和安全检查通过"

grep -E '^[[:space:]]*image:' \
  "${RENDERED_MANIFEST}" |
sort -u
)
```

最后输出的是客户必须能够拉取的精确镜像清单。

不要使用 `--skip-schema-validation`，也不要通过 Helm `--set-string` 传递 AK/SK
或 Grafana 密码。

## 11. 安装

```bash
(
set -euo pipefail

OBNS="${OBNS:-mo-ob}"
PACKAGE="./mo-ob-private-1.0.5.tgz"
HELM_VALUE_ARGS=(-f ./values-customer.yaml)

if [[ -f ./values-registry.yaml ]]; then
  HELM_VALUE_ARGS+=(-f ./values-registry.yaml)
fi

helm upgrade --install mo-ob-private \
  "${PACKAGE}" \
  --namespace "${OBNS}" \
  --create-namespace \
  "${HELM_VALUE_ARGS[@]}" \
  --wait \
  --timeout 30m
)
```

首次安装故意不使用 `--atomic`，这样失败后的 Pod、PVC 和 Events 会保留供排查。
首次失败时先查看 Pod、PVC、Events、镜像拉取和外部 S3 日志。不要删除客户
已有 MinIO、StorageClass、MatrixOne、MOI 或其他业务资源。
也不要把 `destroy`、`helm uninstall`、删除 Namespace 或删除 PVC 当作首次失败的
排查步骤。修正配置后应使用同一 values 重复执行 `helm upgrade --install`。

基线验收成功后，计划内升级可以增加 `--atomic`。

## 12. 验收

```bash
OBNS="${OBNS:-mo-ob}"
helm -n "${OBNS}" status mo-ob-private

kubectl -n "${OBNS}" get pods -o wide
kubectl -n "${OBNS}" get pvc -o wide
kubectl -n "${OBNS}" get service

kubectl -n "${OBNS}" get events \
  --sort-by=.metadata.creationTimestamp |
tail -n 100

kubectl -n "${OBNS}" logs statefulset/loki-write \
  --all-containers \
  --tail=200

kubectl -n "${OBNS}" logs statefulset/loki-backend \
  --all-containers \
  --tail=200

# Grafana 默认是 ClusterIP，验收时可建立临时本地转发。
kubectl -n "${OBNS}" port-forward \
  service/mo-ob-private-grafana \
  3000:80
```

验收要求：

1. 所有底座 Pod Ready；
2. 所有 PVC Bound，且没有意外使用错误 StorageClass；
3. Loki 日志没有鉴权、Bucket 不存在或对象写入失败；
4. Prometheus、Grafana、Alertmanager Service 正常；
5. 重启 Loki write/backend 后仍能查询重启前日志；
6. Helm 使用相同 values 重复执行 upgrade 成功；
7. MatrixOne、MOI、MinIO 等业务 Pod UID 未因安装监控发生变化。

基础包的 Alertmanager receiver 默认为 `null`，不会发送邮件或 Webhook；这表示
告警组件健康，不表示通知链路已经交付。`mo-ob-private 1.0.5` 内置的是
standalone Alertmanager，它不会选择或消费 `AlertmanagerConfig`。与本底座配套时，
`ob-ops` 内容 values 必须保持：

```yaml
notifications:
  enabled: false
  alertmanagerConfigSupported: false
```

只有客户另外提供了 Prometheus Operator-managed Alertmanager，并已验证
`alertmanagerConfigSelector` 和 Namespace selector，才能开启 `ob-ops` 通知资源。
Grafana 默认通过 ClusterIP 提供 HTTP，生产访问应由客户的 HTTPS Ingress
或 LoadBalancer 统一保护。

底座验收通过后，再安装匹配版本的 `ob-ops` 内容 Chart，并继续验收
Prometheus targets、rules、Loki 查询和 Grafana Dashboard。
如果使用了自定义 Namespace，`ob-ops` 的 `EXISTING_MONITORING_NAMESPACE`
必须设为同一个 `OBNS`。
