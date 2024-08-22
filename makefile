.PHONY: local/up
local/up: cluster/up  ## (beta) deploy all containers locally via tilt (k8s cluster will be created if it doesn't exist)
	tilt up

.PHONY: local/down
local/down:  ## (beta) remove all containers deployed via tilt
	tilt down

.PHONY: cluster/up
cluster/up:  ## (beta) create a local development k8s cluster
	ctlptl apply -f dev/kind-config.yaml

.PHONY: cluster/down
cluster/down: ## (beta) delete local development k8s cluster
	ctlptl delete -f dev/kind-config.yaml