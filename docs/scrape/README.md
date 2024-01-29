# Scrape Metric Information

Please copy the template at the bottom and fill the information : )

> 如果所提供的文档已经有包含以下的详细信息，则无需填写以下表格，只需填写基本信息并附上链接即可

ps: [types of metrics](https://prometheus.io/docs/tutorials/understanding_metric_types/#types-of-metrics)

## Instance-Worker

Deploy Environment：contorl-plane

Namespace/Service：mo-cloud/instanceservice

Releated Doc (if exists) ：[MO Cloud Serverless 实例计费资源管理 - 0.8](https://doc.weixin.qq.com/doc/w3_AUoAgQY-AAk2YyuftUvRRC7Q0MnrW?scode=AJsA6gc3AA8z1HfEBuAUoAgQY-AAk)

| 指标名                                             | 指标类型 | 意义                     | 备注 |
| ---------------------------------------------------- | ---------- | -------------------------- | ------ |
| controlplane_instance_detail_info                  | gauge    | 实例、集群信息           |      |
| controlplane_instance_daily_cu                     | gauge    | 各个实例当日 CU 消耗总量 |      |
| controlplane_instance_monthly_cu                   | gauge    | 各个实例当月 CU 消耗总量 |      |
| controlplane_instance_creation_duration_seconds    | gauge    | 实例 Creation 时长       |      |
| controlplane_instance_termination_duration_seconds | gauge    | 实例 Terminate 时长      |      |
| controlplane_instance_update_duration_seconds      | gauge    | 实例 Update 时长         |      |
| controlplane_instance_recovery_duration_seconds    | gauge    | 实例 Recover 时长        |      |



## mo-agent

Deploy Environment：contorl-plane or unit

Namespace/Service：mo-ob/mo-agent-service

Releated Doc (if exists) ：

> 如果所提供的文档已经有包含以下信息，则无需填写以下表格

| 指标名                        | 指标类型  | 意义                                        | 备注 |
| ----------------------------- | --------- | ------------------------------------------- | ---- |
| agent_batch_insert_latency_ms | Histogram | 执行Batch insert到MO的延迟，单位：ms        |      |
| agent_collect_bytes           | Counter   | agent http api 接受的数据，单位：byte       |      |
| agent_processed_bytes         | Counter   | agent完成Batch Insert的 SQL大小，单位：byte |      |
| agent_batch_insert_count      | Counter   | agent完成Batch Insert的次数                 |      |
| api_response_latency_ms       | Histogram | agent http api 响应延迟，单位：ms           |      |
| <br />                        | <br />    | <br />                                      |      |
| <br />                        | <br />    | <br />                                      |      |





## [ empty template ]

Deploy Environment：contorl-plane or unit

Namespace/Service：

Releated Doc (if exists) ：

> 如果所提供的文档已经有包含以下信息，则无需填写以下表格

| 指标名 | 指标类型 | 意义 | 备注 |
| -------- | ---------- | ------ | ------ |
| <br />     | <br />       | <br />   |      |
| <br />     | <br />       | <br />   |      |
| <br />     | <br />       | <br />   |      |
| <br />     | <br />       | <br />   |      |
| <br />     | <br />       | <br />   |      |
| <br />     | <br />       | <br />   |      |
| <br />     | <br />       | <br />   |      |