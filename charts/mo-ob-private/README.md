# MO OB Private

`mo-ob-private` installs the customer observability base stack:

- Prometheus and Prometheus Operator;
- Loki, Alloy and Promtail;
- Grafana and standalone Alertmanager;
- an optional three-instance CloudNativePG PostgreSQL Cluster used only by the
  high-availability Grafana profile;
- node-exporter and kube-state-metrics.

The Chart does not install the CloudNativePG Operator and does not create or
manage a StorageClass, MinIO/S3 service, bucket, or business monitoring
content. CloudNativePG is needed only when the HA profile enables PostgreSQL.
The companion `ob-ops` content Chart owns Kubernetes/Loki/MatrixOne/MOI/MinIO
ServiceMonitors, rules and dashboards.

## Deployment profiles

Two customer examples are intentionally kept side by side:

| Profile | Values | Secrets | Purpose |
|---|---|---|---|
| Standard | `values-customer-standard.yaml.example` | `customer-secrets-standard.yaml.example` | Simple single-replica deployment, Grafana SQLite, external S3/MinIO |
| HA | `values-customer-ha.yaml.example` | `customer-secrets-ha.yaml.example` | Multi-replica components, Grafana on three-instance CloudNativePG |

`values-customer.yaml.example` and `customer-secrets.yaml.example` remain HA
compatibility aliases for existing delivery documents. New documents should
use the explicit `-standard` or `-ha` names.

Standard is the default delivery mode. Kubernetes restarts or reschedules a
failed Pod when storage permits, but a single-replica component can still be
unavailable during restart, node failure or RWO-volume recovery. Standard must
not be described as zero-downtime application HA. HA is available for customers
whose recovery objectives and infrastructure justify its extra database,
storage and operational requirements.

Do not convert an active HA release to Standard in place. Use a new release or
Namespace, or first produce a reviewed data migration and rollback plan.

## Customer contract

Every profile requires:

1. a reachable Kubernetes `>=1.29.0` cluster and Helm 3;
2. a dynamic `ReadWriteOnce` StorageClass;
3. an external S3-compatible service with a pre-created Loki bucket and a
   least-privilege credential;
4. network access to every rendered image, or a fully verified customer mirror;
5. enough schedulable CPU, memory and persistent storage for the reviewed sizing;
6. an unused NodePort `30081` and a reviewed firewall or security-group rule for
   the clients that may access Grafana.

The Chart base values and customer examples explicitly use `directpv-min-io`
for every PVC instead of relying on a cluster default StorageClass. Confirm
that this StorageClass is installed and has enough capacity in every intended
scheduling topology. If a customer uses another dynamic RWO provisioner,
replace every `storageClass` and `storageClassName` value in the selected
customer values file consistently.

The HA profile additionally requires at least three suitable nodes, storage in
every intended failure domain, a separate PostgreSQL-backup bucket and
credential, and CloudNativePG Operator chart `0.29.0` / CloudNativePG `1.30.0`
installed as
   an independent two-replica, cross-node Helm release with a PDB in `mo-ob`,
   or one compatible existing cluster-wide Operator whose equivalent HA
   controls are approved for reuse.

The supplied `values-customer-ha.yaml.example` is a high-availability sizing
starting point, not a universal production recommendation. It runs Loki with
three write replicas, two read replicas, three backend replicas and two gateway
replicas; Prometheus and Grafana with two replicas each; and Alertmanager with
three replicas. The hard anti-affinity rules require at least three suitable
nodes. The bundled PostgreSQL Cluster runs one primary and two replicas with
one `20Gi` PVC per instance. Each customer must review these values against its
own ingest rate, cardinality, retention, failure domains and recovery
objectives.

This is node-level availability based on `kubernetes.io/hostname`, not an
automatic multi-zone or multi-datacenter disaster-recovery design. The PDBs
protect voluntary disruption such as planned node maintenance; they do not
prevent node, disk, network, object-storage or database failures, and they do
not compensate for insufficient CPU, memory or PVC capacity.

Two Grafana Pods backed by two local SQLite databases are not highly available.
Both replicas therefore use the same three-instance CloudNativePG PostgreSQL
Cluster created by this Chart. CloudNativePG maintains the stable write Service
`mo-ob-postgresql-rw`; Grafana reads its application password from the
Namespace-local `kubernetes.io/basic-auth` Secret
`mo-ob-postgresql-app`. PostgreSQL replication is not a backup: the customer
must provide a separate MinIO/S3 backup bucket and credential, verify the first
backup, and periodically test recovery. The example disables Grafana Unified
Alerting because it does not configure that subsystem's HA coordination;
alerts in this monitoring base use Prometheus and Alertmanager.
If Grafana Alerting or Grafana Live is required, design and validate their HA
separately. Install Grafana plugins through the same image or Helm values on
both replicas; do not install a plugin manually in only one Pod.

This HA example targets a new Namespace and a fresh Grafana database. Do not
point an existing Grafana release that uses SQLite at PostgreSQL and assume the
state will move automatically. Grafana does not automatically migrate the
existing SQLite database into this PostgreSQL Cluster. Before changing an
existing release, inventory and back up the SQLite database/PVC, define and
test an application-supported database migration plus rollback procedure, and
verify users, organizations, data sources, dashboards, alerting state, API
keys/service accounts and other persisted settings. Without that migration,
the new PostgreSQL-backed Grafana starts with a new application database and
the previous state is not transferred.

The default release Namespace is `mo-ob`. A custom Namespace is supported by
setting the same value everywhere: the Helm `--namespace` argument, `OBNS`
below, and `EXISTING_MONITORING_NAMESPACE` in the companion `ob-ops`
installer. The customer values file must also set the complete
`mo-ob-opensource.kube-prometheus-stack.prometheus.prometheusSpec.alertingEndpoints[0]`
object with that Namespace; do not override only its `namespace` field because
Helm replaces list entries as a unit. Kubernetes Secrets are Namespace-scoped
and cannot be reused from another Namespace.

## Kubernetes DNS Service compatibility

Loki's upstream Chart defaults to the DNS Service name `kube-dns` in the
`kube-system` Namespace. The DNS implementation may still be CoreDNS while the
Service remains named `kube-dns`; other distributions, including some
Kubespray installations, name the Service `coredns`. Loki gateway startup
fails with `host not found in resolver` when the configured Service name does
not exist.

Check the customer cluster before installation:

```bash
kubectl -n kube-system get service |
grep -E '(^| )(coredns|kube-dns)( |$)'
```

Set the exact Service name in the selected customer values file. This is a
cluster compatibility setting and is unrelated to domestic or upstream image
profiles:

```yaml
mo-ob-opensource:
  loki:
    global:
      # Use coredns only when the Service is actually named coredns.
      dnsService: kube-dns
      dnsNamespace: kube-system
      clusterDomain: cluster.local
```

For example, change `dnsService` to `coredns` when the command above reports a
Service named `coredns`. Keep `dnsNamespace` and `clusterDomain` unchanged
unless the customer cluster deliberately uses different values.

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

For Standard, copy `customer-secrets-standard.yaml.example`, fill all
`FILL_THIS_VALUE` entries and apply it. It creates only `mo-ob-loki-s3` and
`mo-ob-grafana-admin` in the selected Namespace. Standard does not require
CloudNativePG or PostgreSQL backup Secrets.

For HA, use the following workflow.

The simplest customer workflow is to fill the packaged Secret manifest once.
It contains every required credential location for this HA profile: Loki
S3/MinIO, the Grafana Web administrator, the bundled PostgreSQL application
user, and PostgreSQL S3/MinIO backup access.

```bash
(
set -euo pipefail

PACKAGE="./mo-ob-private-1.0.5.tgz"
WORK_DIR="$(mktemp -d)"
SECRET_FILE="/root/mo-ob-customer-secrets.yaml"

tar -xzf "${PACKAGE}" -C "${WORK_DIR}"
install -m 0600 \
  "${WORK_DIR}/mo-ob-private/customer-secrets-ha.yaml.example" \
  "${SECRET_FILE}"

printf 'Edit every FILL_THIS_VALUE in %s\n' "${SECRET_FILE}"
)
```

Edit `/root/mo-ob-customer-secrets.yaml`. The comments identify exactly where
to enter:

- the Loki S3/MinIO Endpoint, Bucket, Access Key and Secret Key;
- the Grafana administrator username and password;
- the `grafana` PostgreSQL application-user password;
- the stable `GF_SECURITY_SECRET_KEY` shared by every Grafana replica;
- the PostgreSQL backup Bucket credential. The backup Endpoint and Bucket path
  are configured in `values-customer.yaml`, not in the Secret.

Then reject incomplete input and create the Namespace plus all four Secrets:

```bash
(
set -euo pipefail

SECRET_FILE="/root/mo-ob-customer-secrets.yaml"

if grep -n 'FILL_THIS_VALUE' "${SECRET_FILE}"; then
  echo "ERROR: ${SECRET_FILE} still contains unfilled values" >&2
  exit 1
fi

test "$(stat -c '%a' "${SECRET_FILE}")" = "600"
kubectl apply -f "${SECRET_FILE}"

for SECRET_NAME in \
  mo-ob-loki-s3 \
  mo-ob-grafana-admin \
  mo-ob-postgresql-app \
  mo-ob-postgresql-backup-s3; do

  kubectl -n mo-ob get secret "${SECRET_NAME}" -o name
done
)
```

The filled manifest is plaintext. Keep mode `0600`; never pass it to Helm and
never commit, package, upload or paste it into delivery records. The
`.gitignore` protects the standard local filenames, but file permissions and
operator handling remain required.

Loki uses its dedicated S3/MinIO Bucket. PostgreSQL uses a different Bucket for
base backups and WAL. Prometheus and Alertmanager use PVCs. Grafana uses PVCs
for per-Pod local files and `mo-ob-postgresql-rw:5432` for shared application
state. Never reuse the Loki Bucket or its credential for PostgreSQL backups.

### Optional interactive alternative

The block below creates the same four Secrets without keeping a filled
manifest. Use either workflow, not both during the same credential change.
Create and save the Grafana administrator password, PostgreSQL application
password, stable Grafana security key and PostgreSQL-backup S3 credential in
the customer password manager first. The mode-`0700` temporary directory and
`--from-file` keep credentials out of `kubectl` process arguments:

```bash
(
set -euo pipefail

OBNS="${OBNS:-mo-ob}"

read -rp 'S3/MinIO endpoint (http[s]://host:port): ' LOKI_S3_ENDPOINT
read -rp 'Existing Loki bucket: ' LOKI_S3_BUCKET
read -rsp 'S3 access key: ' LOKI_S3_ACCESS_KEY; printf '\n'
read -rsp 'S3 secret key: ' LOKI_S3_SECRET_KEY; printf '\n'
read -rp 'PostgreSQL backup S3 access key: ' PG_BACKUP_ACCESS_KEY
read -rsp 'PostgreSQL backup S3 secret key: ' PG_BACKUP_SECRET_KEY; printf '\n'
read -rp 'Grafana administrator [admin]: ' GRAFANA_ADMIN_USER
GRAFANA_ADMIN_USER="${GRAFANA_ADMIN_USER:-admin}"
read -rsp 'Grafana administrator password (at least 16 characters): ' \
  GRAFANA_ADMIN_PASSWORD
printf '\n'
read -rsp 'Bundled PostgreSQL grafana-user password: ' \
  POSTGRESQL_APP_PASSWORD
printf '\n'
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
      -z "${LOKI_S3_SECRET_KEY}" || \
      -z "${PG_BACKUP_ACCESS_KEY}" || \
      -z "${PG_BACKUP_SECRET_KEY}" ]]; then
  echo 'Loki and PostgreSQL-backup S3 credentials must not be empty' >&2
  exit 1
fi
if (( ${#GRAFANA_ADMIN_PASSWORD} < 16 )) || \
   [[ "${GRAFANA_ADMIN_PASSWORD}" == "${GRAFANA_ADMIN_USER}" ]]; then
  echo 'Grafana password must be at least 16 characters and differ from the username' >&2
  exit 1
fi
if [[ -z "${POSTGRESQL_APP_PASSWORD}" ]]; then
  echo 'Bundled PostgreSQL application password must not be empty' >&2
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
    "${SECRET_DIR}/username" \
    "${SECRET_DIR}/password" \
    "${SECRET_DIR}/GF_SECURITY_SECRET_KEY" \
    "${SECRET_DIR}/ACCESS_KEY_ID" \
    "${SECRET_DIR}/ACCESS_SECRET_KEY"
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
printf '%s' 'grafana' >"${SECRET_DIR}/username"
printf '%s' "${POSTGRESQL_APP_PASSWORD}" >"${SECRET_DIR}/password"
printf '%s' "${GRAFANA_SECURITY_SECRET_KEY}" >"${SECRET_DIR}/GF_SECURITY_SECRET_KEY"
printf '%s' "${PG_BACKUP_ACCESS_KEY}" >"${SECRET_DIR}/ACCESS_KEY_ID"
printf '%s' "${PG_BACKUP_SECRET_KEY}" >"${SECRET_DIR}/ACCESS_SECRET_KEY"

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

kubectl -n "${OBNS}" create secret generic mo-ob-postgresql-app \
  --type=kubernetes.io/basic-auth \
  --from-file="${SECRET_DIR}/username" \
  --from-file="${SECRET_DIR}/password" \
  --from-file="${SECRET_DIR}/GF_SECURITY_SECRET_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "${OBNS}" label secret mo-ob-postgresql-app \
  cnpg.io/reload=true --overwrite

kubectl -n "${OBNS}" create secret generic mo-ob-postgresql-backup-s3 \
  --from-file="${SECRET_DIR}/ACCESS_KEY_ID" \
  --from-file="${SECRET_DIR}/ACCESS_SECRET_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "${OBNS}" label secret mo-ob-postgresql-backup-s3 \
  cnpg.io/reload=true --overwrite
)
```

The Secrets are updated idempotently. Rotate credentials only in a controlled
maintenance window and never commit their values to Git, values files, tickets
or delivery documents.

`GF_SECURITY_SECRET_KEY` must be identical on every Grafana replica and remain
stable across upgrades. Store it in the customer password manager; changing it
can make previously encrypted Grafana data unreadable.

```bash
for SECRET_NAME in mo-ob-postgresql-app mo-ob-postgresql-backup-s3; do
  kubectl -n "${OBNS}" get secret "${SECRET_NAME}" -o json |
    jq '{type: .type, keys: (.data | keys)}'
done
```

If the HTTPS S3 endpoint uses a private CA, follow the procedure below for
PostgreSQL and mount the CA into every Loki workload through an approved site
values override. Do not weaken TLS or switch to HTTP merely to bypass an
unknown certificate.

## Validate external S3/MinIO

The installer never creates MinIO, the Loki bucket or the PostgreSQL backup
bucket. Validate each existing bucket with its own dedicated, least-privilege
credential. This block isolates all
`mc` state in a temporary `MC_CONFIG_DIR`, uses a unique alias and cleans the
test object, alias and configuration on every exit:

```bash
(
set -euo pipefail

OBNS="${OBNS:-mo-ob}"

read -rp 'S3/MinIO endpoint (http[s]://host:port): ' LOKI_S3_ENDPOINT
read -rp 'Existing Loki bucket: ' LOKI_S3_BUCKET
read -rsp 'S3 access key: ' LOKI_S3_ACCESS_KEY; printf '\n'
read -rsp 'S3 secret key: ' LOKI_S3_SECRET_KEY; printf '\n'

read -rp 'PostgreSQL backup endpoint [same as Loki]: ' PG_S3_ENDPOINT
PG_S3_ENDPOINT="${PG_S3_ENDPOINT:-${LOKI_S3_ENDPOINT}}"
read -rp 'Existing PostgreSQL backup bucket: ' PG_S3_BUCKET
read -rsp 'PostgreSQL backup access key: ' PG_S3_ACCESS_KEY; printf '\n'
read -rsp 'PostgreSQL backup secret key: ' PG_S3_SECRET_KEY; printf '\n'
read -rp 'Loki endpoint private CA file [empty when not required]: ' \
  LOKI_S3_CA_FILE
read -rp 'PostgreSQL backup private CA file [empty; same as Loki when endpoints match]: ' \
  PG_S3_CA_FILE
if [[ -z "${PG_S3_CA_FILE}" && \
      "${LOKI_S3_ENDPOINT%/}" == "${PG_S3_ENDPOINT%/}" ]]; then
  PG_S3_CA_FILE="${LOKI_S3_CA_FILE}"
fi

for ENDPOINT in "${LOKI_S3_ENDPOINT}" "${PG_S3_ENDPOINT}"; do
  case "${ENDPOINT}" in
    http://*|https://*) ;;
    *) echo "Endpoint must begin with http:// or https://: ${ENDPOINT}" >&2; exit 1 ;;
  esac
done

if [[ -z "${LOKI_S3_BUCKET}" || \
      -z "${LOKI_S3_ACCESS_KEY}" || \
      -z "${LOKI_S3_SECRET_KEY}" || \
      -z "${PG_S3_BUCKET}" || \
      -z "${PG_S3_ACCESS_KEY}" || \
      -z "${PG_S3_SECRET_KEY}" ]]; then
  echo 'Both bucket names and both dedicated credential pairs are required' >&2
  exit 1
fi

if [[ "${LOKI_S3_ENDPOINT%/}" == "${PG_S3_ENDPOINT%/}" && \
      "${LOKI_S3_BUCKET}" == "${PG_S3_BUCKET}" ]]; then
  echo 'Loki and PostgreSQL backups must not use the same Endpoint/Bucket' >&2
  exit 1
fi

for CA_FILE in "${LOKI_S3_CA_FILE}" "${PG_S3_CA_FILE}"; do
  if [[ -n "${CA_FILE}" && ! -s "${CA_FILE}" ]]; then
    echo "Private CA file does not exist or is empty: ${CA_FILE}" >&2
    exit 1
  fi
done

MC_CONFIG_DIR="$(mktemp -d)"
chmod 0700 "${MC_CONFIG_DIR}"
mkdir -p "${MC_CONFIG_DIR}/certs/CAs"
if [[ -n "${LOKI_S3_CA_FILE}" ]]; then
  install -m 0644 "${LOKI_S3_CA_FILE}" \
    "${MC_CONFIG_DIR}/certs/CAs/loki-private-ca.crt"
fi
if [[ -n "${PG_S3_CA_FILE}" ]]; then
  install -m 0644 "${PG_S3_CA_FILE}" \
    "${MC_CONFIG_DIR}/certs/CAs/postgresql-private-ca.crt"
fi
LOKI_ALIAS="mo-ob-loki-check-$$"
PG_ALIAS="mo-ob-pg-check-$$"
LOKI_CHECK_OBJECT="mo-ob-loki-preflight-$(date +%s)-$$.txt"
PG_CHECK_OBJECT="mo-ob-pg-preflight-$(date +%s)-$$.txt"
CHECK_FILE="$(mktemp)"

cleanup_ob_preflight() {
  mc --config-dir "${MC_CONFIG_DIR}" rm \
    "${LOKI_ALIAS}/${LOKI_S3_BUCKET}/${LOKI_CHECK_OBJECT}" \
    >/dev/null 2>&1 || true
  mc --config-dir "${MC_CONFIG_DIR}" rm \
    "${PG_ALIAS}/${PG_S3_BUCKET}/${PG_CHECK_OBJECT}" \
    >/dev/null 2>&1 || true
  mc --config-dir "${MC_CONFIG_DIR}" alias rm "${LOKI_ALIAS}" \
    >/dev/null 2>&1 || true
  mc --config-dir "${MC_CONFIG_DIR}" alias rm "${PG_ALIAS}" \
    >/dev/null 2>&1 || true
  rm -f -- "${CHECK_FILE}"
  find "${MC_CONFIG_DIR}" -depth -mindepth 1 -delete 2>/dev/null || true
  rmdir -- "${MC_CONFIG_DIR}" 2>/dev/null || true
}
trap cleanup_ob_preflight EXIT

printf 'mo-ob-preflight\n' >"${CHECK_FILE}"

validate_bucket() {
  local ALIAS_NAME="$1"
  local ENDPOINT="$2"
  local BUCKET="$3"
  local ACCESS_KEY="$4"
  local SECRET_KEY="$5"
  local OBJECT_NAME="$6"

  mc --config-dir "${MC_CONFIG_DIR}" alias set "${ALIAS_NAME}" \
    "${ENDPOINT}" "${ACCESS_KEY}" "${SECRET_KEY}"
  mc --config-dir "${MC_CONFIG_DIR}" cp "${CHECK_FILE}" \
    "${ALIAS_NAME}/${BUCKET}/${OBJECT_NAME}"
  mc --config-dir "${MC_CONFIG_DIR}" stat \
    "${ALIAS_NAME}/${BUCKET}/${OBJECT_NAME}"
  mc --config-dir "${MC_CONFIG_DIR}" cat \
    "${ALIAS_NAME}/${BUCKET}/${OBJECT_NAME}" >/dev/null
  mc --config-dir "${MC_CONFIG_DIR}" rm \
    "${ALIAS_NAME}/${BUCKET}/${OBJECT_NAME}"
}

validate_bucket \
  "${LOKI_ALIAS}" "${LOKI_S3_ENDPOINT}" "${LOKI_S3_BUCKET}" \
  "${LOKI_S3_ACCESS_KEY}" "${LOKI_S3_SECRET_KEY}" "${LOKI_CHECK_OBJECT}"

validate_bucket \
  "${PG_ALIAS}" "${PG_S3_ENDPOINT}" "${PG_S3_BUCKET}" \
  "${PG_S3_ACCESS_KEY}" "${PG_S3_SECRET_KEY}" "${PG_CHECK_OBJECT}"

if [[ -n "${PG_S3_CA_FILE}" ]]; then
  kubectl create namespace "${OBNS}" \
    --dry-run=client -o yaml | kubectl apply -f -
  kubectl -n "${OBNS}" create secret generic mo-ob-postgresql-backup-ca \
    --from-file="ca.crt=${PG_S3_CA_FILE}" \
    --dry-run=client -o yaml | kubectl apply -f -
fi
)
```

The block fails if both uses resolve to the same Endpoint/Bucket and validates
write, stat, read and delete with each dedicated credential before continuing.

When a private CA file is supplied, the block copies it into the fresh
`${MC_CONFIG_DIR}/certs/CAs/` trust directory before `mc alias set`; it never
uses `--insecure`. The same PostgreSQL CA file is then stored as `ca.crt` in
the Namespace-local `mo-ob-postgresql-backup-ca` Secret. Reference it from the
customer values:

```yaml
postgresql:
  backups:
    endpointCA:
      name: mo-ob-postgresql-backup-ca
      key: ca.crt
```

Leave `endpointCA.name` empty only for HTTP or an HTTPS endpoint whose issuing
CA is already trusted. This optional CA Secret is additional to the four
required credential Secrets.

## Size the customer values

For HA, copy `values-customer-ha.yaml.example`, then replace every example with values
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

The HA example is deliberately a high-availability editing worksheet, not a
production recommendation. Its replica topology is:

- Loki write/backend: 3 each; Loki read/gateway: 2 each;
- Prometheus/Grafana: 2 each;
- Alertmanager: 3;
- bundled PostgreSQL: 3 instances.

Only Loki write/backend, Prometheus, Grafana and Alertmanager request persistent
volumes in the original profile. The bundled PostgreSQL Cluster adds one PVC
per instance. Capacity is approximately:

```text
(Loki write replicas × write PVC size)
+ (Loki backend replicas × backend PVC size)
+ (Prometheus replicas × Prometheus PVC size)
+ (Grafana replicas × Grafana PVC size)
+ (Alertmanager replicas × Alertmanager PVC size)
+ (PostgreSQL instances × PostgreSQL PVC size)

= (3 × 10Gi) + (3 × 10Gi) + (2 × 40Gi) + (2 × 5Gi) + (3 × 1Gi)
  + (3 × 20Gi)
= approximately 213Gi across 16 ReadWriteOnce PVCs
```

The `213Gi` and 16-PVC figures are example requested capacity before customer
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

The standalone Chart defaults to `imageSource: domestic`. Every enabled
workload uses a verified domestic public mirror, including the PostgreSQL
operand and the otherwise easy-to-miss Thanos base image passed as a Prometheus
Operator argument. The independent CloudNativePG Operator has a matching
domestic values file. Each active domestic image in `values.yaml` and
`values-images-domestic.yaml` is immediately followed by a comment containing
its foreign upstream address.

Two complete and directly usable profiles are included in the Chart package:

- `values-images-domestic.yaml`: default and recommended for customer delivery;
- `values-images-upstream.yaml`: original `docker.io`, `quay.io`,
  `registry.k8s.io` and `ghcr.io` addresses.

Use exactly one profile after the customer values file, so the last file wins:

```bash
PACKAGE=./mo-ob-private-1.0.5.tgz

# Extract the selected customer worksheet and edit every marked value before
# installation. Use values-customer-ha.yaml.example only for HA.
tar -xOf "${PACKAGE}" \
  mo-ob-private/values-customer-standard.yaml.example \
  >./values-customer-standard.yaml

# The profiles are files inside the Chart package. Extract them once before
# using -f; this works even when the customer receives only the immutable tgz.
for IMAGE_PROFILE in domestic upstream; do
  tar -xOf "${PACKAGE}" \
    "mo-ob-private/values-images-${IMAGE_PROFILE}.yaml" \
    >"./values-images-${IMAGE_PROFILE}.yaml"
done

# Standard domestic mode.
helm upgrade --install mo-ob-private "${PACKAGE}" \
  --namespace mo-ob --create-namespace \
  -f ./values-customer-standard.yaml \
  -f ./values-images-domestic.yaml

# Standard foreign-upstream mode; use only when the customer network can reach it.
helm upgrade --install mo-ob-private "${PACKAGE}" \
  --namespace mo-ob --create-namespace \
  -f ./values-customer-standard.yaml \
  -f ./values-images-upstream.yaml

# HA uses values-customer-ha.yaml instead and additionally requires the
# CloudNativePG Operator plus all four HA Secrets.
```

The domestic profile is a public network accelerator, not an offline
guarantee. Verify every repository, tag and CPU architecture from the customer
network. The companion `ob-ops` installer uses the same
`IMAGE_SOURCE=domestic|upstream` model and also defaults to `domestic`.

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

## Install or reuse the CloudNativePG Operator

`mo-ob-private` creates the PostgreSQL `Cluster` and `ScheduledBackup` custom
resources, but deliberately does not install the cluster-scoped CRDs,
validating webhook or CloudNativePG Operator. Inspect the cluster before
installing anything:

```bash
OBNS="${OBNS:-mo-ob}"

kubectl get deployment -A \
  -l app.kubernetes.io/name=cloudnative-pg \
  -o 'custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,IMAGE:.spec.template.spec.containers[0].image'
kubectl get crd clusters.postgresql.cnpg.io scheduledbackups.postgresql.cnpg.io \
  2>/dev/null || true
kubectl get validatingwebhookconfiguration \
  cnpg-validating-webhook-configuration 2>/dev/null || true
```

If a compatible cluster-wide CloudNativePG `1.30.x` Operator already exists,
reuse it and do not install a second Operator. If an Operator is Namespace-local
outside `OBNS`, multiple Operators are present, or the detected version is not
approved, stop and have the platform owner resolve ownership first.
For a reused cluster-wide Operator, the platform owner must also confirm its
replica count, cross-node scheduling, requests/limits and a PDB equivalent to
`minAvailable: 1`; this document must not mutate a shared platform Operator.

If no Operator exists, install the reviewed Operator chart as an independent
release in `OBNS` (`mo-ob` by default). With `config.clusterWide=false`, the
Operator watches its own Namespace, so it must be installed in the same
Namespace as the PostgreSQL Cluster:

```bash
(
set -euo pipefail

OBNS="${OBNS:-mo-ob}"
PACKAGE="${PACKAGE:-./mo-ob-private-1.0.5.tgz}"
# domestic is the default; change to upstream only when foreign registries are
# reachable. Use the same IMAGE_SOURCE for the Operator and mo-ob-private.
IMAGE_SOURCE="${IMAGE_SOURCE:-domestic}"

case "${IMAGE_SOURCE}" in
  domestic|upstream) ;;
  *)
    echo 'IMAGE_SOURCE must be domestic or upstream' >&2
    exit 1
    ;;
esac

OPERATOR_VALUES="/root/mo-ob-cnpg-operator-values-${IMAGE_SOURCE}.yaml"
umask 077
tar -xOf "${PACKAGE}" \
  "mo-ob-private/cnpg-operator-values-${IMAGE_SOURCE}.yaml" \
  >"${OPERATOR_VALUES}"
test -s "${OPERATOR_VALUES}"

helm repo add cnpg https://cloudnative-pg.github.io/charts
helm repo update cnpg

helm upgrade --install mo-ob-postgresql-operator cnpg/cloudnative-pg \
  --version 0.29.0 \
  --namespace "${OBNS}" \
  --create-namespace \
  -f "${OPERATOR_VALUES}" \
  --wait \
  --timeout 10m

kubectl apply -f - <<EOF
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: mo-ob-postgresql-operator
  namespace: ${OBNS}
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: cloudnative-pg
      app.kubernetes.io/instance: mo-ob-postgresql-operator
EOF

kubectl -n "${OBNS}" rollout status \
  deployment/mo-ob-postgresql-operator --timeout=300s
kubectl -n "${OBNS}" get pod \
  -l app.kubernetes.io/instance=mo-ob-postgresql-operator -o wide
kubectl -n "${OBNS}" get poddisruptionbudget \
  mo-ob-postgresql-operator
kubectl wait --for=condition=Established \
  crd/clusters.postgresql.cnpg.io --timeout=120s
kubectl wait --for=condition=Established \
  crd/scheduledbackups.postgresql.cnpg.io --timeout=120s
kubectl wait --for=condition=Established \
  crd/backups.postgresql.cnpg.io --timeout=120s
)
```

The reviewed PostgreSQL image is pinned to CloudNativePG `1.30` and this
release uses the in-tree Barman object-store integration for backups. That
integration is deprecated and is expected to be removed in CloudNativePG
`1.31`. Do not upgrade the Operator to `1.31` until this Chart has migrated to
the official backup plugin and a full backup-and-recovery test has passed.
Never uninstall the Operator while `Cluster` resources still exist.

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

# 国内镜像是默认值。只有客户网络能够稳定访问国外 Registry 时才改为 upstream。
IMAGE_SOURCE="${IMAGE_SOURCE:-domestic}"
case "${IMAGE_SOURCE}" in
  domestic|upstream) ;;
  *)
    echo 'IMAGE_SOURCE must be domestic or upstream' >&2
    exit 1
    ;;
esac

IMAGE_VALUES_FILE="./values-images-${IMAGE_SOURCE}.yaml"

sha256sum --check "${PACKAGE}.sha256"

tar -xOf "${PACKAGE}" \
  "mo-ob-private/values-images-${IMAGE_SOURCE}.yaml" \
  >"${IMAGE_VALUES_FILE}"
test -s "${IMAGE_VALUES_FILE}"

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

if grep -n 'FILL_THIS_VALUE' "${VALUES_FILE}"; then
  echo 'Customer values still contain an unfilled PostgreSQL backup Endpoint or Bucket' >&2
  exit 1
fi

kubectl get nodes
kubectl get storageclass
kubectl get pvc -A

for REQUIRED_SECRET in \
  mo-ob-loki-s3 \
  mo-ob-grafana-admin \
  mo-ob-postgresql-app \
  mo-ob-postgresql-backup-s3; do
  kubectl -n "${OBNS}" get secret "${REQUIRED_SECRET}" >/dev/null
done

OPERATOR_JSON="$(
  kubectl get deployment -A \
    -l app.kubernetes.io/name=cloudnative-pg \
    -o json
)"

OPERATOR_COUNT="$(jq '.items | length' <<<"${OPERATOR_JSON}")"
if [[ "${OPERATOR_COUNT}" -ne 1 ]]; then
  echo "Expected exactly one CloudNativePG Operator, found ${OPERATOR_COUNT}" >&2
  exit 1
fi

OPERATOR_VERSION="$(
  jq -r '.items[0].metadata.labels["app.kubernetes.io/version"] // ""' \
    <<<"${OPERATOR_JSON}"
)"
WATCH_NAMESPACE="$(
  jq -r '
    [
      .items[0].spec.template.spec.containers[]
      | select(.name == "manager")
      | (.env // [])[]
      | select(.name == "WATCH_NAMESPACE")
      | .value
    ][0] // ""
  ' <<<"${OPERATOR_JSON}"
)"

if [[ ! "${OPERATOR_VERSION}" =~ ^1\.30\. ]]; then
  echo "CloudNativePG 1.30.x is required; found ${OPERATOR_VERSION}" >&2
  exit 1
fi

if [[ -n "${WATCH_NAMESPACE}" ]] && \
   ! tr ',' '\n' <<<"${WATCH_NAMESPACE}" | grep -Fxq "${OBNS}"; then
  echo "CloudNativePG does not watch Namespace ${OBNS}: ${WATCH_NAMESPACE}" >&2
  exit 1
fi

kubectl get crd \
  clusters.postgresql.cnpg.io \
  scheduledbackups.postgresql.cnpg.io \
  backups.postgresql.cnpg.io >/dev/null

HELM_VALUE_ARGS=(
  -f "${VALUES_FILE}"
  -f "${IMAGE_VALUES_FILE}"
)
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
  'kind: Cluster' \
  'name: mo-ob-postgresql' \
  'name: mo-ob-postgresql-app' \
  'kind: ScheduledBackup' \
  'foldersFromFilesStructure: true' \
  'value: "grafana_folder"' \
  'nodePort: 30081'; do
  if ! grep -Fq "${REQUIRED_GRAFANA_VALUE}" "${RENDERED_MANIFEST}"; then
    echo "Missing required Grafana HA value: ${REQUIRED_GRAFANA_VALUE}" >&2
    exit 1
  fi
done

case "${IMAGE_SOURCE}" in
  domestic)
    EXPECTED_POSTGRESQL_IMAGE='ghcr.m.daocloud.io/cloudnative-pg/postgresql:17.10-202608030910-system-bookworm@sha256:8561d04754c2caf8ed203b52e96163a24ff045782ca726d01b01bbcb0649222c'
    EXPECTED_OPERATOR_IMAGE='ghcr.m.daocloud.io/cloudnative-pg/cloudnative-pg:1.30.0'
    ;;
  upstream)
    EXPECTED_POSTGRESQL_IMAGE='ghcr.io/cloudnative-pg/postgresql:17.10-202608030910-system-bookworm@sha256:8561d04754c2caf8ed203b52e96163a24ff045782ca726d01b01bbcb0649222c'
    EXPECTED_OPERATOR_IMAGE='ghcr.io/cloudnative-pg/cloudnative-pg:1.30.0'
    ;;
esac

if [[ -f ./values-registry.yaml ]]; then
  if ! grep -Eq \
    '^[[:space:]]*imageName:[[:space:]]+[^[:space:]]+@sha256:[0-9a-f]{64}[[:space:]]*$' \
    "${RENDERED_MANIFEST}"; then
    echo 'Private PostgreSQL imageName must use an immutable @sha256 digest' >&2
    exit 1
  fi
  if ! grep -Fq 'name: harbor-image-secret' "${RENDERED_MANIFEST}"; then
    echo 'Private-registry workloads must reference harbor-image-secret' >&2
    exit 1
  fi
elif ! grep -Fq "${EXPECTED_POSTGRESQL_IMAGE}" \
  "${RENDERED_MANIFEST}"; then
  echo "The reviewed ${IMAGE_SOURCE} PostgreSQL image is missing" >&2
  exit 1
fi

grep -E \
  '^[[:space:]]*image(Name)?:|--prometheus-config-reloader=|--thanos-default-base-image=' \
  "${RENDERED_MANIFEST}" | sort -u
printf '%s\n' \
  "CloudNativePG Operator image (separate release): ${EXPECTED_OPERATOR_IMAGE}"

helm upgrade --install mo-ob-private "${PACKAGE}" \
  --namespace "${OBNS}" \
  --create-namespace \
  "${HELM_VALUE_ARGS[@]}" \
  --wait \
  --timeout 30m
)
```

The rendered `imageName:` entry is the PostgreSQL operand image; it is not
matched by an `image:`-only inventory. The Operator belongs to its separate
Helm release, so the matching domestic or upstream Operator values file must
be used and its image must also be reachable or mirrored independently.

The first installation intentionally omits `--atomic`, preserving failed Pods,
PVCs and Events for diagnosis. On first failure, inspect the release, images,
PVCs, PostgreSQL status and S3 errors and rerun the same upgrade after
correction. Do not run `destroy`, uninstall the base, uninstall the
CloudNativePG Operator, delete the Namespace, delete the PostgreSQL `Cluster`
or PVCs, or delete customer MinIO, StorageClass, MatrixOne or MOI resources as
a troubleshooting shortcut. The `helm.sh/resource-policy: keep` annotations
are a final safety net, not an uninstall workflow.

## Verify and integrate monitoring content

```bash
OBNS="${OBNS:-mo-ob}"
helm -n "${OBNS}" status mo-ob-private
kubectl -n "${OBNS}" get pods,pvc,service -o wide
kubectl -n "${OBNS}" get clusters.postgresql.cnpg.io
kubectl -n "${OBNS}" get \
  scheduledbackups.postgresql.cnpg.io,backups.postgresql.cnpg.io
kubectl -n "${OBNS}" get events \
  --sort-by=.metadata.creationTimestamp | tail -n 50
kubectl -n "${OBNS}" logs statefulset/loki-write \
  --all-containers --tail=100
kubectl -n "${OBNS}" logs statefulset/loki-backend \
  --all-containers --tail=100
kubectl -n "${OBNS}" get service mo-ob-private-grafana -o wide
kubectl -n "${OBNS}" get service mo-ob-postgresql-rw -o wide
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
Ready and reference `mo-ob-postgresql-app`. The PostgreSQL Cluster must report
Ready with three instances, `mo-ob-postgresql-rw` must exist, and at least one
scheduled or on-demand MinIO/S3 backup must complete before acceptance. The
provider output must contain
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
