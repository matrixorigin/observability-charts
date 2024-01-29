# Alerts Information

| Alert Group               | File                                              | Watching Service | Deploy Env        | Rules Def Doc | Note              |
| --------------------------- | --------------------------------------------------- | ------------------ | ------------------- | --------------- | ------------------- |
| mo-cloud.instance.payment | charts/mo-ruler-stack/rules/instance-service.yaml | Instance-Service | control-plane     | [MO Cloud Serverless 实例计费资源管理 - 0.8](https://doc.weixin.qq.com/doc/w3_AUoAgQY-AAk2YyuftUvRRC7Q0MnrW?scode=AJsA6gc3AA8z1HfEBuAUoAgQY-AAk)              | 后续修改&优化：[#1123](https://github.com/matrixorigin/MO-Cloud/issues/1123)、[#1102](https://github.com/matrixorigin/MO-Cloud/issues/1102) |
| mo-cloud.matrix-worker    | charts/mo-ruler-stack/rules/matrix-worker.yaml    | Metric-Worker    | unit              | [#1179](https://github.com/matrixorigin/MO-Cloud/issues/1179)              |                   |
| mo-ob.general             | charts/mo-ruler-stack/rules/ob-infra.yaml         | mo-ob/promtail   | unit/controlplane | [#1296](https://github.com/matrixorigin/MO-Cloud/issues/1296)              |                   |

