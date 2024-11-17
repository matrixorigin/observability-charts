.PHONY: moc/up
moc/up: cluster/up  ## (beta) deploy all containers locally via tilt (k8s cluster will be created if it doesn't exist)
	TILT_COMMAND=moc tilt up

.PHONY: moc/down
moc/down:  ## (beta) remove all containers deployed via tilt
	TILT_COMMAND=moc tilt down

.PHONY: private/up
private/up: cluster/up
	TILT_COMMAND=private tilt up

.PHONY: private/down
private/down:  ## (beta) remove all containers deployed via tilt
	TILT_COMMAND=private tilt down

.PHONY: minio/up
minio/up: cluster/up
	TILT_COMMAND=minio tilt up

.PHONY: minio/down
minio/down:  ## (beta) remove all containers deployed via tilt
	TILT_COMMAND=minio tilt down

.PHONY: cluster/up
cluster/up:  ## (beta) create a local development k8s cluster
	ctlptl apply -f dev/kind-config.yaml

.PHONY: cluster/down
cluster/down: ## (beta) delete local development k8s cluster
	ctlptl delete -f dev/kind-config.yaml