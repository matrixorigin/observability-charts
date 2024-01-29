## What type of PR is this?

* [ ] Feature
* [ ] BUG
* [ ] Alerts
* [ ] Improvement
* [ ] Documentation
* [ ] Test and CI

## Which issue(s) this PR related:

issue #

If this is a PR for adding Alert, please finish the workround below :)

### Alart Rules Checklist

为了保证应用正常接入监控与告警，请检查:

* [ ] 业务端暴露 /metrics 接口接入采集
* [ ] 编写告警规则 & 告警单元测试并验证
* [ ] [可选] 添加 Alertmanager Receiver 配置并验证
* [ ] [可选] 添加 Grafana Dashboard 并本地调试
* [ ] 在 .github/CODEOWNERS 标注告警文件的owner
* [ ] 根据 `## Alert Doc Checklist` 添加相关 README 说明

### Alert Doc Checklist

为了告警规则持续管理，请添加 README 说明:

* [ ] 采集指标信息：[Scrape List](/matrixone-cloud/observability/blob/main/docs/scrape/README.md)
* [ ] 告警信息：[Alerts List](/matrixone-cloud/observability/blob/main/docs/alerts/README.md)
* [ ] Dashboard 信息表格（如果有）：[dashboards list](/matrixone-cloud/observability/blob/main/charts/mo-ruler-stack/grafana/dashboards/README.md)
* [ ] 在 [.github/CODEOWNERS](/matrixone-cloud/observability/blob/main/.github/CODEOWNERS) 标注 dashboard.json 配置的 owner

## What this PR does / why we need it:
