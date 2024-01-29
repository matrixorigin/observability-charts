# Observability Workflow 说明

在 `.github/workflows` 下定义了全部 workflow，以下是简要说明。

---

`ci.yml`：默认的 ci 检查，提 PR 时自动执行。包括执行单元测试、测试功能是否正常执行、SCA Test。该 action 仅在涉及核心代码变更时自动执行，若仅是增加告警规则或更新 chart 则不会执行。

`email_chack.yml`：定时任务，在每天在东八区的早上 9：30 执行，主要是检查邮件是否能正常发送。

`docker-image.yml`：手动执行任务，根据输入打包 docker 镜像至 matrixorigin/observability 中，主要用于测试目的。

`chart_release_check.yml`：提 PR 时自动执行，检查 ./charts 下的 helm chart 是否有误，检查通过则代表能顺利打包。

`release_chart.yml`：PR 合并后自动执行，对./charts 下的 helm chart 进行打包发布至 release 。

`alertmanager-check.yaml`：手动执行，用于验证 alertmanager 配置的正确性。该 action 将会在 ci 环境启动 minikube 并使用当前的 charts/mo-ruler-stack 进行部署：
1.  该 action 的输入是告警规则路径 `file_path`（默认为 charts/mo-ruler-stack/rules/*.yaml）；邮件送达地址 `email_to`（默认为 null，即不发送）
2.  该 action 会将实际配置中全部 email_receiver 的邮件接收人替换成`email_to`，这样就不会打扰到无关人士。将全部 webhook 的 hostname 重定义到一个 echo-server 中（功能：打印接收到的请求对应的 curl 语句）。
3.  执行时，action 会加载 `file_path` 的所有告警规则，然后模拟触发这些告警发送到 alertmanager，将由 alertmanager 根据配置执行相应的告警行为
4.  针对邮件告警，可以通过查看特定邮箱确认配置的正确性；针对 webhook ，可以在 action 中查看打印 curl 语句然后自行在外部环境验证其正确性。

`alertrules-check.yaml`：提交 PR 时自动执行，用于验证告警规则的语法以及正确性：
1. 读取 charts/mo-ruler-stack/rules 下所有告警规则文件，使用 promtool 校验其语法是否正确
2. 读取 test/rule-check 下所有告警规则的单元测试，使用 promtool 验证告警规则的正确性