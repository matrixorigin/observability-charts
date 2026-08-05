# MO OB Private

`mo-ob-private` installs the customer observability base stack:

- Prometheus and Prometheus Operator;
- Loki, Alloy and Promtail;
- Grafana and standalone Alertmanager;
- node-exporter and kube-state-metrics.

The Chart does not create or manage a StorageClass, MinIO/S3 service, bucket,
or business monitoring content. The companion `ob-ops` content Chart owns
Kubernetes/Loki/MatrixOne/MOI/MinIO ServiceMonitors, rules and dashboards.

## Customer contract

Before installation, the customer site must provide:

1. a reachable Kubernetes cluster, Helm 3 and at least three schedulable nodes;
2. a dynamic `ReadWriteOnce` StorageClass available in every intended failure
   domain;
3. an external highly available S3-compatible service and a pre-created Loki
   bucket;
4. least-privilege S3 credentials with the required bucket operations;
5. an external highly available PostgreSQL or MySQL database for Grafana;
6. network access to every rendered image, or a fully verified customer mirror;
7. enough schedulable CPU, memory and persistent storage for the reviewed sizing;
8. an unused NodePort `30081` and a reviewed firewall or security-group rule for
   the clients that may access Grafana.

The supplied `values-customer.yaml.example` is a high-availability sizing
starting point, not a universal production recommendation. It runs Loki with
three write replicas, two read replicas, three backend replicas and two gateway
replicas; Prometheus and Grafana with two replicas each; and Alertmanager with
three replicas. The hard anti-affinity rules require at least three suitable
nodes. Each customer must review these values against its own ingest rate,
cardinality, retention, failure domains and recovery objectives.

This is node-level availability based on `kubernetes.io/hostname`, not an
automatic multi-zone or multi-datacenter disaster-recovery design. The PDBs
protect voluntary disruption such as planned node maintenance; they do not
prevent node, disk, network, object-storage or database failures, and they do
not compensate for insufficient CPU, memory or PVC capacity.

Two Grafana Pods backed by two local SQLite databases are not highly available.
Both replicas must use the same customer-managed highly available PostgreSQL or
MySQL service through the Namespace-local Secret
`mo-ob-grafana-database`. The database lifecycle, backup, restore, TLS and
availability remain the customer's responsibility. The example disables
Grafana Unified Alerting because it does not configure that subsystem's HA
coordination; alerts in this monitoring base use Prometheus and Alertmanager.
If Grafana Alerting or Grafana Live is required, design and validate their HA
separately. Install Grafana plugins through the same image or Helm values on
both replicas; do not install a plugin manually in only one Pod.

The default release Namespace is `mo-ob`. A custom Namespace is supported by
setting the same value everywhere: the Helm `--namespace` argument, `OBNS`
below, and `EXISTING_MONITORING_NAMESPACE` in the companion `ob-ops`
installer. The customer values file must also set the complete
`mo-ob-opensource.kube-prometheus-stack.prometheus.prometheusSpec.alertingEndpoints[0]`
object with that Namespace; do not override only its `namespace` field because
Helm replaces list entries as a unit. Kubernetes Secrets are Namespace-scoped
and cannot be reused from another Namespace.

## Release artifacts and reproducibility

The reviewed release contains:

| Chart | Version |
|---|---:|
| `mo-ob-private` | `1.0.5` |
| `mo-ob-opensource` | `1.0.11` |
| `mo-ruler-stack` | `1.1.0` |

Customer delivery must include all three files:

- `mo-ob-private-1.0.5.tgz`;
- `mo-ob-private-1.0.5.tgz.sha256`;
- `mo-ob-private-1.0.5.release-ref.txt`, containing the immutable 40-character
  Git commit used to build the package.

Release maintainers build only from a reviewed commit, never from a moving
branch or pull-request head. Replace the placeholder before running:

```bash
(
set -euo pipefail

DELIVERY_REF="<reviewed-40-character-commit-sha>"
if [[ ! "${DELIVERY_REF}" =~ ^[0-9a-f]{40}$ ]]; then
  echo "DELIVERY_REF must be the reviewed 40-character commit SHA" >&2
  exit 1
fi

git clone git@github.com:matrixorigin/observability-charts.git
cd observability-charts
git switch --detach "${DELIVERY_REF}"

test "$(git rev-parse HEAD)" = "${DELIVERY_REF}"
test -z "$(git status --porcelain)"

helm dependency update charts/mo-ob-opensource
helm dependency update charts/mo-ruler-stack
helm dependency update charts/mo-ob-private
helm lint charts/mo-ob-private

mkdir -p dist
helm package charts/mo-ob-private --destination dist

(
  cd dist
  sha256sum mo-ob-private-1.0.5.tgz \
    > mo-ob-private-1.0.5.tgz.sha256
  sha256sum --check mo-ob-private-1.0.5.tgz.sha256
  printf 'observability-charts-ref=%s\n' "${DELIVERY_REF}" \
    > mo-ob-private-1.0.5.release-ref.txt
)
)
```

Customers should install the reviewed `.tgz`; source-tree installation belongs
only to the release-maintainer workflow above.

## Prepare Namespace-local Secrets

Create the Grafana administrator and external-database passwords plus one stable
random Grafana security key in the customer password manager first. The block
below creates `mo-ob-loki-s3`,
`mo-ob-grafana-admin` and `mo-ob-grafana-database`. It uses a mode-`0700`
temporary directory and `--from-file`, so credentials do not appear in
`kubectl` process arguments:

```bash
(
set -euo pipefail

OBNS="${OBNS:-mo-ob}"

read -rp 'S3/MinIO endpoint (http[s]://host:port): ' LOKI_S3_ENDPOINT
read -rp 'Existing Loki bucket: ' LOKI_S3_BUCKET
read -rsp 'S3 access key: ' LOKI_S3_ACCESS_KEY; printf '\n'
read -rsp 'S3 secret key: ' LOKI_S3_SECRET_KEY; printf '\n'
read -rp 'Grafana administrator [admin]: ' GRAFANA_ADMIN_USER
GRAFANA_ADMIN_USER="${GRAFANA_ADMIN_USER:-admin}"
read -rsp 'Grafana administrator password (at least 16 characters): ' \
  GRAFANA_ADMIN_PASSWORD
printf '\n'
read -rp 'Grafana database type [postgres]: ' GRAFANA_DATABASE_TYPE
GRAFANA_DATABASE_TYPE="${GRAFANA_DATABASE_TYPE:-postgres}"
read -rp 'Grafana database host (host:port): ' GRAFANA_DATABASE_HOST
read -rp 'Grafana database name [grafana]: ' GRAFANA_DATABASE_NAME
GRAFANA_DATABASE_NAME="${GRAFANA_DATABASE_NAME:-grafana}"
read -rp 'Grafana database user: ' GRAFANA_DATABASE_USER
read -rsp 'Grafana database password: ' GRAFANA_DATABASE_PASSWORD
printf '\n'
read -rp 'Grafana database SSL mode (database-specific): ' \
  GRAFANA_DATABASE_SSL_MODE
read -rsp 'Grafana shared security secret key (at least 32 characters): ' \
  GRAFANA_SECURITY_SECRET_KEY
printf '\n'

LOKI_S3_FORCE_PATH_STYLE="true"
case "${LOKI_S3_ENDPOINT}" in
  http://*)  LOKI_S3_INSECURE="true" ;;
  https://*) LOKI_S3_INSECURE="false" ;;
  *) echo 'S3 endpoint must begin with http:// or https://' >&2; exit 1 ;;
esac

if [[ -z "${LOKI_S3_BUCKET}" || \
      -z "${LOKI_S3_ACCESS_KEY}" || \
      -z "${LOKI_S3_SECRET_KEY}" ]]; then
  echo 'S3 bucket, access key and secret key must not be empty' >&2
  exit 1
fi
if (( ${#GRAFANA_ADMIN_PASSWORD} < 16 )) || \
   [[ "${GRAFANA_ADMIN_PASSWORD}" == "${GRAFANA_ADMIN_USER}" ]]; then
  echo 'Grafana password must be at least 16 characters and differ from the username' >&2
  exit 1
fi
case "${GRAFANA_DATABASE_TYPE}" in
  postgres|mysql) ;;
  *) echo 'Grafana database type must be postgres or mysql' >&2; exit 1 ;;
esac
if [[ -z "${GRAFANA_DATABASE_HOST}" || \
      -z "${GRAFANA_DATABASE_USER}" || \
      -z "${GRAFANA_DATABASE_PASSWORD}" || \
      -z "${GRAFANA_DATABASE_SSL_MODE}" ]]; then
  echo 'Grafana database host, user, password and SSL mode must not be empty' >&2
  exit 1
fi
if (( ${#GRAFANA_SECURITY_SECRET_KEY} < 32 )); then
  echo 'Grafana shared security secret key must be at least 32 characters' >&2
  exit 1
fi

kubectl create namespace "${OBNS}" \
  --dry-run=client -o yaml | kubectl apply -f -

SECRET_DIR="$(mktemp -d)"
chmod 0700 "${SECRET_DIR}"
cleanup_secret_files() {
  rm -f -- \
    "${SECRET_DIR}/LOKI_S3_ENDPOINT" \
    "${SECRET_DIR}/LOKI_S3_BUCKET" \
    "${SECRET_DIR}/LOKI_S3_ACCESS_KEY" \
    "${SECRET_DIR}/LOKI_S3_SECRET_KEY" \
    "${SECRET_DIR}/LOKI_S3_FORCE_PATH_STYLE" \
    "${SECRET_DIR}/LOKI_S3_INSECURE" \
    "${SECRET_DIR}/admin-user" \
    "${SECRET_DIR}/admin-password" \
    "${SECRET_DIR}/GF_DATABASE_TYPE" \
    "${SECRET_DIR}/GF_DATABASE_HOST" \
    "${SECRET_DIR}/GF_DATABASE_NAME" \
    "${SECRET_DIR}/GF_DATABASE_USER" \
    "${SECRET_DIR}/GF_DATABASE_PASSWORD" \
    "${SECRET_DIR}/GF_DATABASE_SSL_MODE" \
    "${SECRET_DIR}/GF_SECURITY_SECRET_KEY"
  rmdir -- "${SECRET_DIR}" 2>/dev/null || true
}
trap cleanup_secret_files EXIT

printf '%s' "${LOKI_S3_ENDPOINT}" >"${SECRET_DIR}/LOKI_S3_ENDPOINT"
printf '%s' "${LOKI_S3_BUCKET}" >"${SECRET_DIR}/LOKI_S3_BUCKET"
printf '%s' "${LOKI_S3_ACCESS_KEY}" >"${SECRET_DIR}/LOKI_S3_ACCESS_KEY"
printf '%s' "${LOKI_S3_SECRET_KEY}" >"${SECRET_DIR}/LOKI_S3_SECRET_KEY"
printf '%s' "${LOKI_S3_FORCE_PATH_STYLE}" >"${SECRET_DIR}/LOKI_S3_FORCE_PATH_STYLE"
printf '%s' "${LOKI_S3_INSECURE}" >"${SECRET_DIR}/LOKI_S3_INSECURE"
printf '%s' "${GRAFANA_ADMIN_USER}" >"${SECRET_DIR}/admin-user"
printf '%s' "${GRAFANA_ADMIN_PASSWORD}" >"${SECRET_DIR}/admin-password"
printf '%s' "${GRAFANA_DATABASE_TYPE}" >"${SECRET_DIR}/GF_DATABASE_TYPE"
printf '%s' "${GRAFANA_DATABASE_HOST}" >"${SECRET_DIR}/GF_DATABASE_HOST"
printf '%s' "${GRAFANA_DATABASE_NAME}" >"${SECRET_DIR}/GF_DATABASE_NAME"
printf '%s' "${GRAFANA_DATABASE_USER}" >"${SECRET_DIR}/GF_DATABASE_USER"
printf '%s' "${GRAFANA_DATABASE_PASSWORD}" >"${SECRET_DIR}/GF_DATABASE_PASSWORD"
printf '%s' "${GRAFANA_DATABASE_SSL_MODE}" >"${SECRET_DIR}/GF_DATABASE_SSL_MODE"
printf '%s' "${GRAFANA_SECURITY_SECRET_KEY}" >"${SECRET_DIR}/GF_SECURITY_SECRET_KEY"

kubectl -n "${OBNS}" create secret generic mo-ob-loki-s3 \
  --from-file="${SECRET_DIR}/LOKI_S3_ENDPOINT" \
  --from-file="${SECRET_DIR}/LOKI_S3_BUCKET" \
  --from-file="${SECRET_DIR}/LOKI_S3_ACCESS_KEY" \
  --from-file="${SECRET_DIR}/LOKI_S3_SECRET_KEY" \
  --from-file="${SECRET_DIR}/LOKI_S3_FORCE_PATH_STYLE" \
  --from-file="${SECRET_DIR}/LOKI_S3_INSECURE" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "${OBNS}" create secret generic mo-ob-grafana-admin \
  --from-file="admin-user=${SECRET_DIR}/admin-user" \
  --from-file="admin-password=${SECRET_DIR}/admin-password" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "${OBNS}" create secret generic mo-ob-grafana-database \
  --from-file="${SECRET_DIR}/GF_DATABASE_TYPE" \
  --from-file="${SECRET_DIR}/GF_DATABASE_HOST" \
  --from-file="${SECRET_DIR}/GF_DATABASE_NAME" \
  --from-file="${SECRET_DIR}/GF_DATABASE_USER" \
  --from-file="${SECRET_DIR}/GF_DATABASE_PASSWORD" \
  --from-file="${SECRET_DIR}/GF_DATABASE_SSL_MODE" \
  --from-file="${SECRET_DIR}/GF_SECURITY_SECRET_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
)
```

The Secrets are updated idempotently. Rotate credentials only in a controlled
maintenance window and never commit their values to Git, values files, tickets
or delivery documents.

The database endpoint must be reachable from both Grafana Pods and must already
contain the reviewed database and user. Choose `GF_DATABASE_SSL_MODE` according
to the selected database engine and the customer's TLS policy. Do not weaken
database TLS to work around an untrusted certificate. Check only the Secret key
names, without printing their values:

`GF_SECURITY_SECRET_KEY` must be identical on every Grafana replica and remain
stable across upgrades. Store it in the customer password manager; changing it
can make previously encrypted Grafana data unreadable.

```bash
kubectl -n "${OBNS}" get secret mo-ob-grafana-database -o json |
jq '{type: .type, keys: (.data | keys)}'
```

If the HTTPS S3 endpoint uses a private CA, the CA must be trusted inside every
Loki workload through a reviewed site values override. Do not weaken TLS or
switch to HTTP merely to bypass an unknown certificate.

## Validate external S3/MinIO

The installer never creates MinIO or the Loki bucket. Validate the existing
bucket with a dedicated, least-privilege credential. This block isolates all
`mc` state in a temporary `MC_CONFIG_DIR`, uses a unique alias and cleans the
test object, alias and configuration on every exit:

```bash
(
set -euo pipefail

read -rp 'S3/MinIO endpoint (http[s]://host:port): ' LOKI_S3_ENDPOINT
read -rp 'Existing Loki bucket: ' LOKI_S3_BUCKET
read -rsp 'S3 access key: ' LOKI_S3_ACCESS_KEY; printf '\n'
read -rsp 'S3 secret key: ' LOKI_S3_SECRET_KEY; printf '\n'

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
  "${LOKI_S3_ENDPOINT}" "${LOKI_S3_ACCESS_KEY}" "${LOKI_S3_SECRET_KEY}"
printf 'mo-ob-preflight\n' >"${CHECK_FILE}"
mc --config-dir "${MC_CONFIG_DIR}" cp "${CHECK_FILE}" \
  "${MC_ALIAS}/${LOKI_S3_BUCKET}/${CHECK_OBJECT}"
mc --config-dir "${MC_CONFIG_DIR}" stat \
  "${MC_ALIAS}/${LOKI_S3_BUCKET}/${CHECK_OBJECT}"
mc --config-dir "${MC_CONFIG_DIR}" cat \
  "${MC_ALIAS}/${LOKI_S3_BUCKET}/${CHECK_OBJECT}" >/dev/null
mc --config-dir "${MC_CONFIG_DIR}" rm \
  "${MC_ALIAS}/${LOKI_S3_BUCKET}/${CHECK_OBJECT}"
)
```

## Size the customer values

Copy `values-customer.yaml.example`, then replace every example with values
approved for the customer ingest rate, cardinality, retention and recovery
objectives. The example deliberately contains this schema-enforced gate:

```yaml
customerSizingApproved: false
```

After an accountable reviewer approves the worksheet, record the change
ticket, reviewer and date in the delivery record, then change the YAML boolean
to:

```yaml
customerSizingApproved: true
```

Do not quote `true` and do not use `--skip-schema-validation`. Helm validation
rejects the customer values while this acknowledgement is absent or false.

The example is deliberately a high-availability editing worksheet, not a
production recommendation. Its replica topology is:

- Loki write/backend: 3 each; Loki read/gateway: 2 each;
- Prometheus/Grafana: 2 each;
- Alertmanager: 3.

Only Loki write/backend, Prometheus, Grafana and Alertmanager request persistent
volumes in this profile. Capacity is approximately:

```text
(Loki write replicas × write PVC size)
+ (Loki backend replicas × backend PVC size)
+ (Prometheus replicas × Prometheus PVC size)
+ (Grafana replicas × Grafana PVC size)
+ (Alertmanager replicas × Alertmanager PVC size)

= (3 × 10Gi) + (3 × 10Gi) + (2 × 40Gi) + (2 × 5Gi) + (3 × 1Gi)
= approximately 153Gi across 13 ReadWriteOnce PVCs
```

The `153Gi` and 13-PVC figures are example requested capacity before customer
headroom, snapshots, storage-system overhead and external Loki object storage.
They must not be treated as proof that a customer storage system has enough
usable capacity. Confirm StorageClass topology, expansion support, failure
domains and capacity on every schedulable node using the customer's storage
provider procedures. Do not copy node names, free-space figures or sizing from
another cluster.

With node-local `ReadWriteOnce` storage, an existing PVC normally cannot move
to another node after a node or disk failure. HA keeps service available through
the remaining replicas; recovery of the failed replica must follow the customer
storage provider's documented procedure.

The following Grafana dashboard-discovery protocol is not a sizing knob. Keep
it aligned with the companion `ob-ops` Dashboard ConfigMaps so MatrixOne, MOI,
K8s and Loki dashboards remain in their intended folders:

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

Changing either `folderAnnotation` or `foldersFromFilesStructure` without the
matching content-Chart change breaks folder placement. The customer HA example
therefore keeps `folderAnnotation: grafana_folder` and
`foldersFromFilesStructure: true` explicitly.

The same example exposes Grafana as `NodePort` `30081`. Confirm that the port is
unused and restrict node firewall or security-group access to approved client
networks. A client that can route to a cluster node can then use
`http://<reachable-node-ip>:30081`. NodePort does not provide HTTPS by itself.

## Image sources and private registries

The standalone Chart defaults to upstream `docker.io`, `quay.io` and
`registry.k8s.io` images. When deploying through the companion `ob-ops`
installer, `IMAGE_SOURCE=upstream|domestic` selects its reviewed image profile.
The domestic profile is a public network accelerator, not an offline guarantee;
verify every repository, tag and CPU architecture from the customer network.

For a private registry, mirror every exact rendered image and provide a tested
image override file. An image pull Secret is Namespace-scoped, so create it in
`OBNS` and reference it from every enabled subchart. A Secret in another
Namespace is not usable. If a companion content release runs an optional image
in a different Namespace, create and reference an equivalent Secret there as
well. A private registry CA must also be trusted by the
container runtime on every node; imagePullSecret handles authentication only.

The following flow keeps the Harbor password off process arguments by using
`docker login --password-stdin` and a protected temporary Docker config. It
requires a Docker CLI that supports `--password-stdin`:

```bash
(
set -euo pipefail

OBNS="${OBNS:-mo-ob}"
read -rp 'Registry host[:port]: ' HARBOR_REGISTRY
read -rp 'Registry username: ' HARBOR_USERNAME
read -rsp 'Registry password: ' HARBOR_PASSWORD; printf '\n'

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
    --username "${HARBOR_USERNAME}" --password-stdin
chmod 0600 "${REGISTRY_DIR}/config.json"

kubectl -n "${OBNS}" create secret generic harbor-image-secret \
  --type=kubernetes.io/dockerconfigjson \
  --from-file=".dockerconfigjson=${REGISTRY_DIR}/config.json" \
  --dry-run=client -o yaml | kubectl apply -f -
)
```

## Preflight and install

Install the immutable package, not a working tree:

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
  echo 'Missing reviewed immutable Git commit record' >&2
  exit 1
fi

if ! grep -Eq '^customerSizingApproved:[[:space:]]+true[[:space:]]*$' \
     "${VALUES_FILE}"; then
  echo 'Production sizing review has not been recorded' >&2
  exit 1
fi

kubectl get nodes
kubectl get storageclass
kubectl get pvc -A

for REQUIRED_SECRET in \
  mo-ob-loki-s3 \
  mo-ob-grafana-admin \
  mo-ob-grafana-database; do
  kubectl -n "${OBNS}" get secret "${REQUIRED_SECRET}" >/dev/null
done

HELM_VALUE_ARGS=(-f "${VALUES_FILE}")
if [[ -f ./values-registry.yaml ]]; then
  HELM_VALUE_ARGS+=(-f ./values-registry.yaml)
fi

helm lint "${PACKAGE}" "${HELM_VALUE_ARGS[@]}"
helm template mo-ob-private "${PACKAGE}" \
  --namespace "${OBNS}" \
  --api-versions policy/v1/PodDisruptionBudget \
  "${HELM_VALUE_ARGS[@]}" >"${RENDERED_MANIFEST}"

if grep -Eq \
  'obtest-|test-bucket|admin:admin|smtp\.exmail|it@matrixorigin|baseAuthChecksum: required' \
  "${RENDERED_MANIFEST}"; then
  echo 'Unsafe legacy value found in rendered manifests' >&2
  exit 1
fi

for REQUIRED_GRAFANA_VALUE in \
  'name: mo-ob-grafana-database' \
  'foldersFromFilesStructure: true' \
  'value: "grafana_folder"' \
  'nodePort: 30081'; do
  if ! grep -Fq "${REQUIRED_GRAFANA_VALUE}" "${RENDERED_MANIFEST}"; then
    echo "Missing required Grafana HA value: ${REQUIRED_GRAFANA_VALUE}" >&2
    exit 1
  fi
done

grep -E '^[[:space:]]*image:' "${RENDERED_MANIFEST}" | sort -u

helm upgrade --install mo-ob-private "${PACKAGE}" \
  --namespace "${OBNS}" \
  --create-namespace \
  "${HELM_VALUE_ARGS[@]}" \
  --wait \
  --timeout 30m
)
```

The first installation intentionally omits `--atomic`, preserving failed Pods,
PVCs and Events for diagnosis. On first failure, inspect the release, images,
PVCs and Loki S3 errors and rerun the same upgrade after correction. Do not run
`destroy`, uninstall the base, delete the Namespace, or delete customer MinIO,
StorageClass, MatrixOne or MOI resources as a troubleshooting shortcut.

## Verify and integrate monitoring content

```bash
OBNS="${OBNS:-mo-ob}"
helm -n "${OBNS}" status mo-ob-private
kubectl -n "${OBNS}" get pods,pvc,service -o wide
kubectl -n "${OBNS}" get events \
  --sort-by=.metadata.creationTimestamp | tail -n 50
kubectl -n "${OBNS}" logs statefulset/loki-write \
  --all-containers --tail=100
kubectl -n "${OBNS}" logs statefulset/loki-backend \
  --all-containers --tail=100
kubectl -n "${OBNS}" get service mo-ob-private-grafana -o wide
kubectl get nodes -o wide

# From a client allowed by the node firewall/security group:
GRAFANA_NODE_IP="<reachable-node-ip>"
curl --fail "http://${GRAFANA_NODE_IP}:30081/api/health"

kubectl -n "${OBNS}" get configmap \
  mo-ob-private-grafana-config-dashboards \
  -o jsonpath='{.data.provider\.yaml}'
```

Verify all Pods are Ready, PVCs use the approved StorageClass, Loki can retain
and retrieve data across a controlled restart, and both Grafana replicas are
Ready and reference `mo-ob-grafana-database`. The provider output must contain
`foldersFromFilesStructure: true`; the Grafana dashboard sidecar must contain
`FOLDER_ANNOTATION=grafana_folder`. Verify that Grafana has healthy `prometheus`
and `loki` datasources and remains functional after either Grafana Pod is
restarted.

The bundled Alertmanager is a standalone Chart deployment and does not consume
`AlertmanagerConfig`; "standalone" does not mean one replica—the HA customer
example runs three clustered replicas. With `mo-ob-private 1.0.5`, the companion
`ob-ops` content values must keep:

```yaml
notifications:
  enabled: false
  alertmanagerConfigSupported: false
```

Only an external Prometheus Operator-managed Alertmanager with verified
`alertmanagerConfigSelector` and Namespace selector may enable the `ob-ops`
notification resources. A healthy standalone Alertmanager does not mean that
email or webhook delivery has been configured.

Install the matching `ob-ops` content Chart only after the base workloads and
external object-storage writes are healthy. Set its
`EXISTING_MONITORING_NAMESPACE` to the same `OBNS` value.
