# 如何添加 dashboard

## 准备:
1. dashboard 的 json 配置文件
2. dashboard 的 owner

## 添加配置

1. `{your_dashboard_name}.json` 配置文件
2. `{your_dashboard_name}_labels.yaml` 配置文件

样例说明:
1. [dashboards/example.json](./dashboards/example.json) 从grafana中导出的json 配置

2. [dashboards/example_labels.yaml](dashboards/example_labels.yaml) 配置该dashboard的configmap 的 labels (例如: app.kubernetes.io/managed-by)

