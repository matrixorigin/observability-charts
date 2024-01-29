# Observability
MOCloud Observability Charts

## 安装

### Helm 安装

添加helm仓库

```shell
helm repo add mo-ob https://matrixone-cloud.github.io/observability-charts
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
```

安装MO Agent

```shell
helm install <RELEASE_NAME> mo-ob/mo-agent-stack --version <VERSION>
```


安装MO Ruler

```shell
helm install <RELEASE_NAME> mo-ob/mo-ruler-stack --version <VERSION>
```

安装MO OB

```shell
helm install <RELEASE_NAME> mo-ob/mo-ob-opensource --version <VERSION>
```
