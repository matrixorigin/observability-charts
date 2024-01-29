# Observability 工具代码

这里的工具代码主要是一些脚本和配置文件，用于辅助 CI 的执行，也可以支持本地测试，

---

`check-alertmanager`：该文件夹的代码主要用于支持检验 alermanager 配置的 action 的执行（即 .github/workflows/alertmanager-check.yaml ）：

1.  `echo-server`：一个假的 webhook server，ci 中当 alertmanager 发送 webhook 告警时会被修改成发送到 echo-server；echo-server 会打印出此告警对应的 curl 语句（与alertmanager 发送该告警的请求完全等价），供测试人员在自己的环境测试真实的 webhook 是否连通。
2.  `send-dummy-alert.go`：告警发送脚本，该脚本将读取给定的告警规则文件（在 ci 中默认是 charts/mo-ruler-stack/rules）并转换成 prometheus 格式的告警请求，发送至给定的 alertmanager 中，模拟这些告警的触发。
3.  `setup_env_and_start.py`：alertmanager 启动脚本，主要的工作是在 ci 环境将 charts/mo-ruler-stack/values.yaml 中的 alertmanager 配置进行文本替换，将邮箱、webhook 地址重定向后进行部署。

`grafana-playground`：该文件夹包含了一个 grafana 的本地 docker-compose 环境，在 grafana-playground/prometheus-server.yml 下添加本地的采集  endpoint，再启动 `docker-compose up -d` 即可打开 grafana 使用业务指标进行图标绘制。

`docker-compose.yaml`：一并与 mo-agent.yaml、mo-ruler.yaml、fluent-bit.conf、agent-prometheus.yml构成一个可以在本地部署的 mo-ob 环境，其中，observability/rules 下是测试告警规则。目前该  compose 被用在 .github/workflows/ci.yml 中，也可用于本地测试。

- `mo-agent.yaml`：同 docker-compose.yaml
- `mo-ruler.yaml`：同 docker-compose.yaml
- `fluent-bit.conf`：同 docker-compose.yaml
- `agent-prometheus.yml`：同 docker-compose.yaml

`script`：该文件夹下的脚本用于支持 .github/workflows/ci.yml 执行，含有 alertmanager 初始化的配置。其中 script/data_check.go 将会模拟一些数据插入，用于检验 mo-agent 的写入是否正常

`promql-test-config.yml`：在项目根目录的 makefile 中的 promql-test 用于检验 mo-ruler 对 promql 语法的支持程度，将会用到 promql-test-config.yml和 promql-test-queries.yml ，后者是语法检验的测试用例。
- `promql-test-queries.yml`: 同 promql-test-config.yml