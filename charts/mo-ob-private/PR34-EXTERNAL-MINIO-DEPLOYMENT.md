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

随包提供的 `values-customer.yaml.example` 是高可用容量评审起点：Loki write、
backend 各 3 副本，read、gateway 各 2 副本；Prometheus、Grafana 各 2 副本；
Alertmanager 3 副本。硬反亲和要求至少 3 个合适的可调度节点。这些数值不是所有
客户生产环境的统一推荐值，必须按客户写入量、指标基数、保留周期、故障域和恢复
目标完成评审。

这里的硬反亲和以 `kubernetes.io/hostname` 为拓扑键，只提供节点级可用性，不等于
自动完成跨可用区或跨机房容灾。PDB 只约束计划维护等自愿驱逐，不能防止节点、磁盘、
网络、对象存储或数据库硬故障，也不能解决 CPU、内存或 PVC 容量不足。

Grafana 两副本不能分别使用本地 SQLite；那只是两个相互独立的实例，不是真正的
高可用。两个副本必须通过 Namespace 级 Secret `mo-ob-grafana-database` 共用客户
独立维护的高可用 PostgreSQL 或 MySQL。示例同时使用 NodePort `30081`，允许获准
客户端通过 `http://<可达节点IP>:30081` 直接访问；客户必须确认端口未占用并限制
节点防火墙或安全组的来源范围。示例关闭 Grafana Unified Alerting，告警由
Prometheus 和 Alertmanager 负责；如需 Grafana Alerting 或 Grafana Live，必须另行
完成其 HA 设计和验收。Grafana 插件必须通过同一镜像或 values 同步到两个副本，禁止
只在单个 Pod 中手工安装。

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
| 可调度节点数和故障域 | 至少 3 个合适节点 |
| Loki write PVC 大小/副本数 | 示例 10Gi × 3 |
| Loki read 副本数 | 示例 2 |
| Loki backend PVC 大小/副本数 | 示例 10Gi × 3 |
| Loki gateway 副本数 | 示例 2 |
| Loki 保留时间 | |
| Prometheus PVC 大小/副本数/保留时间 | 示例 40Gi × 2 / 21d |
| Grafana PVC 大小/副本数 | 示例 5Gi × 2 |
| Alertmanager PVC 大小/副本数 | 示例 1Gi × 3 |
| 各组件 CPU/内存 requests、limits | |
| S3/MinIO Endpoint | |
| Loki Bucket | |
| S3 是否使用 HTTPS | |
| 是否使用 Path Style | |
| 镜像来源 | 上游公网 / 客户 Harbor |
| Grafana 外部数据库类型 | PostgreSQL / MySQL |
| Grafana 外部数据库 HA、备份和 TLS | |
| Grafana 数据库地址（不含密码） | |
| Grafana Service 类型 | 示例 NodePort |
| Grafana NodePort | 示例 30081，部署前确认未占用 |

当前 SimpleScalable 模式的持久化容量计算方式为：

```text
Loki write 副本数 × write PVC
+ Loki backend 副本数 × backend PVC
+ Prometheus 副本数 × Prometheus PVC
+ Grafana 副本数 × Grafana PVC
+ Alertmanager 副本数 × Alertmanager PVC
```

当前示例的计算结果为：

```text
(3 × 10Gi) + (3 × 10Gi) + (2 × 40Gi) + (2 × 5Gi) + (3 × 1Gi)
= 约 153Gi，共 13 个 ReadWriteOnce PVC
```

`153Gi` 和 13 个 PVC 只是示例申请量，不包含客户预留、快照、存储系统开销和
外部 Loki 对象存储。它不能证明客户存储系统的实际可用容量足够。还必须按客户
存储厂商的流程确认 StorageClass 拓扑、扩容能力、失败域和每个可调度节点的容量；
不得带入其他测试集群的节点名称、剩余空间或经验值。客户生产环境应根据日志
写入量、指标基数、保留时间和故障恢复目标重新评估。

如果 StorageClass 使用节点本地 `ReadWriteOnce` 磁盘，节点或磁盘故障后，既有 PVC
通常不能自动漂移到其他节点。高可用依靠剩余副本继续服务；故障副本的磁盘恢复或
重建必须按客户存储系统的正式流程执行。

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
  kubectl helm mc jq openssl tar grep sha256sum curl; do
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

高可用示例要求至少 3 个符合资源、污点和存储拓扑条件的可调度节点。还必须确认
NodePort `30081` 未被其他 Service 使用，且客户网络能够按安全策略访问节点地址：

```bash
kubectl get service -A \
  -o 'custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,NODEPORT:.spec.ports[*].nodePort' |
grep -w 30081 || true
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

推荐直接使用 Chart 包内的统一客户凭据模板。这个文件已经把 Loki MinIO/S3、
Grafana 登录账号和 Grafana 外部数据库的所有必填位置全部展开：

```bash
(
set -euo pipefail

OB_PACKAGE="/root/mo-work/ob-base/artifacts/mo-ob-private-1.0.5.tgz"
WORK_DIR="$(mktemp -d)"
SECRET_FILE="/root/mo-ob-customer-secrets.yaml"

tar -xzf "${OB_PACKAGE}" -C "${WORK_DIR}"
install -m 0600 \
  "${WORK_DIR}/mo-ob-private/customer-secrets.yaml.example" \
  "${SECRET_FILE}"

echo "请编辑 ${SECRET_FILE}，替换所有 FILL_THIS_VALUE"
)
```

打开 `/root/mo-ob-customer-secrets.yaml`，按照文件内注释填写：

1. Loki 使用的 MinIO/S3 Endpoint、Bucket、AK、SK；
2. Grafana Web 管理员用户名和密码；
3. Grafana 高可用 PostgreSQL/MySQL 地址、数据库、用户和密码；
4. 所有 Grafana 副本共用的 `GF_SECURITY_SECRET_KEY`。

填写后一次性创建 Namespace 和三个 Secret：

```bash
(
set -euo pipefail

SECRET_FILE="/root/mo-ob-customer-secrets.yaml"

if grep -n 'FILL_THIS_VALUE' "${SECRET_FILE}"; then
  echo "错误：${SECRET_FILE} 中仍有未填写项"
  exit 1
fi

test "$(stat -c '%a' "${SECRET_FILE}")" = "600"
kubectl apply -f "${SECRET_FILE}"

for SECRET_NAME in \
  mo-ob-loki-s3 \
  mo-ob-grafana-admin \
  mo-ob-grafana-database; do

  kubectl -n mo-ob get secret "${SECRET_NAME}" -o name
done
)
```

填写后的文件包含明文密码，只能保存在受控位置并保持权限 `0600`；不能作为
Helm values 使用，也不能提交 Git、重新打进 Chart 或粘贴到工单、聊天和交付文档。

当前底座只有 Loki 使用 MinIO/S3。Prometheus 和 Alertmanager 使用 PVC；Grafana
使用 PVC 保存各 Pod 的插件/本地文件，并使用外部 PostgreSQL/MySQL 保存共享业务
状态，不使用 MinIO AK/SK。

下面的手工交互命令保留为可选替代方式。统一凭据模板已经成功创建三个 Secret 时，
不需要再重复执行手工创建步骤。

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

## 7. 创建 Grafana 管理员和外部数据库 Secret

如果第 6 节已经使用统一客户凭据模板成功创建 `mo-ob-grafana-admin` 和
`mo-ob-grafana-database`，本节无需重复执行；下面仅作为手工替代方式保留。

### 7.1 Grafana 管理员 Secret

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

### 7.2 Grafana 高可用数据库 Secret

两个 Grafana 副本必须连接同一个客户独立维护的高可用 PostgreSQL 或 MySQL。
数据库必须已创建，专用用户必须具备 Grafana 初始化和迁移所需权限，并且地址可从
两个 Grafana Pod 访问。数据库高可用、备份、恢复、监控和 TLS 均不由本 Chart
管理。不要把两个 Pod 各自的本地 SQLite 当作高可用数据库。

先在客户密码管理系统中保存数据库密码和一个长期固定的随机共享安全密钥，再创建
Namespace 级 Secret：

```bash
(
set -euo pipefail

OBNS="${OBNS:-mo-ob}"
read -rp 'Grafana 数据库类型 [postgres]：' GRAFANA_DATABASE_TYPE
GRAFANA_DATABASE_TYPE="${GRAFANA_DATABASE_TYPE:-postgres}"
read -rp 'Grafana 数据库地址（host:port）：' GRAFANA_DATABASE_HOST
read -rp 'Grafana 数据库名 [grafana]：' GRAFANA_DATABASE_NAME
GRAFANA_DATABASE_NAME="${GRAFANA_DATABASE_NAME:-grafana}"
read -rp 'Grafana 数据库用户：' GRAFANA_DATABASE_USER
read -rsp 'Grafana 数据库密码：' GRAFANA_DATABASE_PASSWORD
printf '\n'
read -rp 'Grafana 数据库 SSL mode（按数据库类型和客户 TLS 策略填写）：' \
  GRAFANA_DATABASE_SSL_MODE
read -rsp 'Grafana 全副本共享安全密钥（至少 32 个字符）：' \
  GRAFANA_SECURITY_SECRET_KEY
printf '\n'

case "${GRAFANA_DATABASE_TYPE}" in
  postgres|mysql) ;;
  *) echo '错误：数据库类型只能是 postgres 或 mysql'; exit 1 ;;
esac

if [[ -z "${GRAFANA_DATABASE_HOST}" || \
      -z "${GRAFANA_DATABASE_USER}" || \
      -z "${GRAFANA_DATABASE_PASSWORD}" || \
      -z "${GRAFANA_DATABASE_SSL_MODE}" ]]; then
  echo '错误：数据库地址、用户、密码和 SSL mode 不能为空'
  exit 1
fi
if (( ${#GRAFANA_SECURITY_SECRET_KEY} < 32 )); then
  echo '错误：Grafana 全副本共享安全密钥不能少于 32 个字符'
  exit 1
fi

DATABASE_SECRET_DIR="$(mktemp -d)"
chmod 0700 "${DATABASE_SECRET_DIR}"
cleanup_grafana_database_secret_files() {
  rm -f -- \
    "${DATABASE_SECRET_DIR}/GF_DATABASE_TYPE" \
    "${DATABASE_SECRET_DIR}/GF_DATABASE_HOST" \
    "${DATABASE_SECRET_DIR}/GF_DATABASE_NAME" \
    "${DATABASE_SECRET_DIR}/GF_DATABASE_USER" \
    "${DATABASE_SECRET_DIR}/GF_DATABASE_PASSWORD" \
    "${DATABASE_SECRET_DIR}/GF_DATABASE_SSL_MODE" \
    "${DATABASE_SECRET_DIR}/GF_SECURITY_SECRET_KEY"
  rmdir -- "${DATABASE_SECRET_DIR}" 2>/dev/null || true
}
trap cleanup_grafana_database_secret_files EXIT

printf '%s' "${GRAFANA_DATABASE_TYPE}" \
  >"${DATABASE_SECRET_DIR}/GF_DATABASE_TYPE"
printf '%s' "${GRAFANA_DATABASE_HOST}" \
  >"${DATABASE_SECRET_DIR}/GF_DATABASE_HOST"
printf '%s' "${GRAFANA_DATABASE_NAME}" \
  >"${DATABASE_SECRET_DIR}/GF_DATABASE_NAME"
printf '%s' "${GRAFANA_DATABASE_USER}" \
  >"${DATABASE_SECRET_DIR}/GF_DATABASE_USER"
printf '%s' "${GRAFANA_DATABASE_PASSWORD}" \
  >"${DATABASE_SECRET_DIR}/GF_DATABASE_PASSWORD"
printf '%s' "${GRAFANA_DATABASE_SSL_MODE}" \
  >"${DATABASE_SECRET_DIR}/GF_DATABASE_SSL_MODE"
printf '%s' "${GRAFANA_SECURITY_SECRET_KEY}" \
  >"${DATABASE_SECRET_DIR}/GF_SECURITY_SECRET_KEY"

kubectl -n "${OBNS}" create secret generic mo-ob-grafana-database \
  --from-file="${DATABASE_SECRET_DIR}/GF_DATABASE_TYPE" \
  --from-file="${DATABASE_SECRET_DIR}/GF_DATABASE_HOST" \
  --from-file="${DATABASE_SECRET_DIR}/GF_DATABASE_NAME" \
  --from-file="${DATABASE_SECRET_DIR}/GF_DATABASE_USER" \
  --from-file="${DATABASE_SECRET_DIR}/GF_DATABASE_PASSWORD" \
  --from-file="${DATABASE_SECRET_DIR}/GF_DATABASE_SSL_MODE" \
  --from-file="${DATABASE_SECRET_DIR}/GF_SECURITY_SECRET_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
)
```

`GF_DATABASE_SSL_MODE` 的合法值取决于 PostgreSQL 或 MySQL 以及客户的 TLS
策略，必须经过数据库负责人确认。不得为了绕过未知证书而关闭 TLS。
`GF_SECURITY_SECRET_KEY` 必须由所有 Grafana 副本共用、存入客户密码管理系统并在
升级期间保持不变；随意更换可能导致既有加密数据无法解密。只检查键名、不要显示值：

```bash
kubectl -n "${OBNS}" get secret mo-ob-grafana-database -o json |
jq '{type: .type, keys: (.data | keys)}'
```

预期包含：`GF_DATABASE_TYPE`、`GF_DATABASE_HOST`、`GF_DATABASE_NAME`、
`GF_DATABASE_USER`、`GF_DATABASE_PASSWORD`、`GF_DATABASE_SSL_MODE`、
`GF_SECURITY_SECRET_KEY`。

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

- Loki、Prometheus、Grafana、Alertmanager 的资源、保留时间和容量；
- 至少 3 个可调度节点是否满足示例中的硬反亲和；
- Loki write/backend StorageClass 和 PVC 大小；
- Prometheus StorageClass、PVC 大小和 retention；
- Grafana StorageClass 和 PVC 大小；
- Alertmanager StorageClass 和 PVC 大小；
- Grafana 外部高可用 PostgreSQL/MySQL 地址、TLS 和 Secret 是否就绪；
- NodePort `30081` 是否未占用，以及防火墙或安全组的允许来源。

Secret 值不在该文件中。values 中只引用 `mo-ob-loki-s3`、
`mo-ob-grafana-admin` 和 `mo-ob-grafana-database`。示例中的高可用副本、容量和
资源只是编辑工作表，不是所有生产环境的统一推荐值。评审人必须将：

```yaml
customerSizingApproved: false
```

在交付记录中登记变更单、评审人和评审日期后，改为 YAML 布尔值：

```yaml
customerSizingApproved: true
```

不要给 `true` 加引号，也不要使用 `--skip-schema-validation`。该字段由 Chart
Schema 强制校验；未完成评审时，第 10 节会拒绝继续。

本高可用示例使用以下直接访问配置：

```yaml
mo-ruler-stack:
  grafana:
    service:
      enabled: true
      type: NodePort
      port: 80
      targetPort: 3000
      nodePort: 30081
```

部署后，获准客户端使用 `http://<可达节点IP>:30081`。NodePort 本身不提供 HTTPS；
必须通过客户网络边界限制访问。若客户改用 Ingress、LoadBalancer 或其他端口，必须
作为现场 values 变更重新完成网络、安全和容量评审，不能同时保留冲突的暴露方式。

Grafana Dashboard 目录配置不是容量参数。为兼容配套 `ob-ops` 内容 Chart，必须
明确保留：

```yaml
mo-ruler-stack:
  grafana:
    sidecar:
      dashboards:
        enabled: true
        label: grafana_dashboard
        labelValue: "1"
        folderAnnotation: grafana_folder
        provider:
          foldersFromFilesStructure: true
```

`folderAnnotation: grafana_folder` 让 sidecar 识别 Dashboard ConfigMap 的目录注解；
`foldersFromFilesStructure: true` 让 Grafana 把 sidecar 创建的文件目录映射成 Dashboard
目录。只保留其中一项或让注解键与内容 Chart 不一致，都会破坏 MatrixOne、MOI、
K8s、Loki 的目录分层。

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

for REQUIRED_SECRET in \
  mo-ob-loki-s3 \
  mo-ob-grafana-admin \
  mo-ob-grafana-database; do
  if ! kubectl -n "${OBNS}" get secret "${REQUIRED_SECRET}" >/dev/null; then
    echo "错误：缺少 Namespace 级 Secret ${REQUIRED_SECRET}"
    exit 1
  fi
done

HELM_VALUE_ARGS=(-f "${VALUES_FILE}")

if [[ -f ./values-registry.yaml ]]; then
  HELM_VALUE_ARGS+=(-f ./values-registry.yaml)
fi

helm lint "${PACKAGE}" \
  "${HELM_VALUE_ARGS[@]}"

helm template mo-ob-private "${PACKAGE}" \
  --namespace "${OBNS}" \
  --api-versions policy/v1/PodDisruptionBudget \
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

for REQUIRED_GRAFANA_VALUE in \
  'name: mo-ob-grafana-database' \
  'foldersFromFilesStructure: true' \
  'value: "grafana_folder"' \
  'nodePort: 30081'; do
  if ! grep -Fq "${REQUIRED_GRAFANA_VALUE}" \
    "${RENDERED_MANIFEST}"; then
    echo "错误：Grafana 高可用渲染缺少 ${REQUIRED_GRAFANA_VALUE}"
    exit 1
  fi
done

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

kubectl -n "${OBNS}" get service mo-ob-private-grafana -o wide
kubectl get nodes -o wide

# 在防火墙或安全组已放行的客户端执行。
GRAFANA_NODE_IP="<可达节点IP>"
curl --fail "http://${GRAFANA_NODE_IP}:30081/api/health"

# 检查 Grafana 文件 provider 保留目录映射。
kubectl -n "${OBNS}" get configmap \
  mo-ob-private-grafana-config-dashboards \
  -o jsonpath='{.data.provider\.yaml}'

# 检查 Dashboard sidecar 的目录注解键，不输出 Secret 值。
GRAFANA_POD="$(kubectl -n "${OBNS}" get pod \
  -l app.kubernetes.io/name=grafana \
  -o jsonpath='{.items[0].metadata.name}')"
kubectl -n "${OBNS}" get pod "${GRAFANA_POD}" \
  -o jsonpath='{range .spec.containers[?(@.name=="grafana-sc-dashboard")].env[*]}{.name}{"="}{.value}{"\n"}{end}'
```

验收要求：

1. Loki write/backend 各 3 个 Pod、read/gateway 各 2 个 Pod Ready，并按硬反亲和
   分散；
2. Prometheus、Grafana 各 2 个 Pod，Alertmanager 3 个 Pod Ready；
3. 当前示例在全新 Namespace 中创建约 153Gi、13 个 RWO PVC，全部 Bound 且没有
   意外使用错误 StorageClass；该数字仍须与客户评审记录核对；
4. Loki 日志没有鉴权、Bucket 不存在或对象写入失败；
5. Grafana 两个副本都引用 `mo-ob-grafana-database`，数据库连接正常；停掉任一
   Grafana Pod 后，NodePort `30081` 仍能访问并保留 Dashboard、用户和会话状态；
6. provider 输出包含 `foldersFromFilesStructure: true`，sidecar 环境包含
   `FOLDER_ANNOTATION=grafana_folder`；
7. Prometheus、Grafana、Alertmanager Service 正常；
8. 重启 Loki write/backend 后仍能查询重启前日志；
9. Helm 使用相同 values 重复执行 upgrade 成功；
10. MatrixOne、MOI、MinIO 等业务 Pod UID 未因安装监控发生变化。

基础包的 Alertmanager receiver 默认为 `null`，不会发送邮件或 Webhook；这表示
告警组件健康，不表示通知链路已经交付。`mo-ob-private 1.0.5` 内置的是
standalone Alertmanager Chart；这里的 standalone 表示不由 Prometheus Operator
管理，不表示单副本，高可用示例会运行 3 个集群副本。它不会选择或消费
`AlertmanagerConfig`。与本底座配套时，
`ob-ops` 内容 values 必须保持：

```yaml
notifications:
  enabled: false
  alertmanagerConfigSupported: false
```

只有客户另外提供了 Prometheus Operator-managed Alertmanager，并已验证
`alertmanagerConfigSelector` 和 Namespace selector，才能开启 `ob-ops` 通知资源。
本示例中的 Grafana 通过 NodePort `30081` 提供 HTTP。它只应暴露给客户批准的网络；
若需要跨不受信任网络访问，应在客户网络边界增加经过审核的 HTTPS 入口，不能把
NodePort 当作 TLS 或身份边界。

底座验收通过后，再安装匹配版本的 `ob-ops` 内容 Chart，并继续验收
Prometheus targets、rules、Loki 查询和 Grafana Dashboard。
如果使用了自定义 Namespace，`ob-ops` 的 `EXISTING_MONITORING_NAMESPACE`
必须设为同一个 `OBNS`。
