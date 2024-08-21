## 添加告警规则 (for unit)

目录分类
- 将日志告警文件放至 log 目录下
- 将指标告警文件放至 metric 目录下

> PS: 如需添加到 controlplane 请移步到同级目录 aliyun/ob-component/controlplane-resources-chart

### 编写样例

- 样例: metric/mocloud-infra-metric-rules.yaml

```
labels:
  matrixone.cloud/rule-type: metric     ## necessary, values in [log, metric]
  matrixone.cloud/unit-name: default    ## necessary, values in [default, {real-unit-name} ]
                                        ## 1) default, 即所有unit 都会启用
                                        ## 2) {real-unit-name}, 则只有该 unit会使用; 如果需要多个unit都指定, 请配置多份policy文件
groups:
- name: {group_name}                    ## 请参考 ./metric/mocloud-infra-metric-rules.yaml
                                        ## 详情请查看 https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/#alerting-rules
  ...
```
