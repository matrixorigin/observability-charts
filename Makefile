

build: local

local-loki:
	helm package charts/loki

.PHONY: local-open
local-open: local-loki
	if [ ! -e  charts/mo-ob-opensource/charts ]; then mkdir -p charts/mo-ob-opensource/charts; fi
	cp -p loki-*.tgz charts/mo-ob-opensource/charts
	helm package charts/mo-ob-opensource #--dependency-update

.PHONY: local-ruler
local-ruler:
	helm package charts/mo-ruler-stack #--dependency-update

.PHONY: local-private
local-private: local-open local-ruler
	if [ ! -e  charts/mo-ob-private/charts ]; then mkdir -p charts/mo-ob-private/charts; fi
	cp -p mo-ob-opensource-*.tgz charts/mo-ob-private/charts
	cp -p mo-ruler-stack-*.tgz charts/mo-ob-private/charts
	helm package charts/mo-ob-private #--dependency-update

local: local-private

clean:
	rm -rf loki-*.tgz mo-ob-opensource-*.tgz mo-ob-private-*.tgz
