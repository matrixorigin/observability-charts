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

1. a reachable Kubernetes cluster and Helm 3;
2. a dynamic `ReadWriteOnce` StorageClass;
3. an external S3-compatible service and a pre-created Loki bucket;
4. least-privilege S3 credentials with the required bucket operations;
5. network access to every rendered image, or a fully verified customer mirror;
6. enough schedulable CPU, memory and persistent storage for the reviewed sizing.

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

Create the Grafana password in the customer password manager first. The block
below uses a mode-`0700` temporary directory and `--from-file`, so credentials
do not appear in `kubectl` process arguments:

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
    "${SECRET_DIR}/admin-password"
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
)
```

The Secrets are updated idempotently. Rotate credentials only in a controlled
maintenance window and never commit their values to Git, values files, tickets
or delivery documents.

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

The default numbers are an editing worksheet, not a production recommendation.
Capacity is approximately:

```text
(Loki write replicas × write PVC size)
+ (Loki backend replicas × backend PVC size)
+ (Prometheus replicas × Prometheus PVC size)
+ (Grafana replicas × Grafana PVC size)
+ at least 20%-30% site headroom
```

Confirm StorageClass topology, expansion support, failure domains and the
available capacity on every schedulable node. Do not copy node names or sizes
from another cluster.

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

HELM_VALUE_ARGS=(-f "${VALUES_FILE}")
if [[ -f ./values-registry.yaml ]]; then
  HELM_VALUE_ARGS+=(-f ./values-registry.yaml)
fi

helm lint "${PACKAGE}" "${HELM_VALUE_ARGS[@]}"
helm template mo-ob-private "${PACKAGE}" \
  --namespace "${OBNS}" \
  "${HELM_VALUE_ARGS[@]}" >"${RENDERED_MANIFEST}"

if grep -Eq \
  'obtest-|test-bucket|admin:admin|smtp\.exmail|it@matrixorigin|baseAuthChecksum: required' \
  "${RENDERED_MANIFEST}"; then
  echo 'Unsafe legacy value found in rendered manifests' >&2
  exit 1
fi

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
kubectl -n "${OBNS}" port-forward \
  service/mo-ob-private-grafana 3000:80
```

Verify all Pods are Ready, PVCs use the approved StorageClass, Loki can retain
and retrieve data across a controlled restart, and Grafana has healthy
`prometheus` and `loki` datasources.

The bundled Alertmanager is standalone and does not consume
`AlertmanagerConfig`. With `mo-ob-private 1.0.5`, the companion `ob-ops`
content values must keep:

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
