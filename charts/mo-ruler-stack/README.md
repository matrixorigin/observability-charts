## mo-ruler-stack 目录说明

```
mo-ruler-stack
├── Chart.lock
├── Chart.yaml
├── README.md
├── alertmanager-webhook-adapter/alert-template
├── charts
├── grafana
├── mo.yaml
├── rules
├── templates
└── values.yaml
```

- `rules`: 存放告警规则文件，会被自动识别读取
- `alertmanager-webhook-adapter`: alertmanager-webhook-adapter 一个开源的 alertmanager 的 webhook server，他可以将 alertmanager 格式的告警转化成企业微信机器人、飞书等格式的信息并发送，这个目录下alert-template 存放企业微信告警信息模板
- `grafana`: 存放 grafana dashboard 文件