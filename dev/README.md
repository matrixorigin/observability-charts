## mo ob local debug environment

dev/**: helm values files for tilt local development env 

to install local debug environment:

```
# install local kind k8s
make cluster/up
# install charts
tilt up
```

stop and clean:

```
tilt down
make cluster/down
```