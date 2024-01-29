

# config list

| json file                              | title                                                  |
| -------------------------------------- | ------------------------------------------------------ |
| alertmanager-overview.json             | Alertmanager / Overview                                |
| alertmanager-alertinfo.json            | Alertmanager / AlertInfo                               |
| etcd.json                              | Etcd / etcd                                            |
| k8s-apiserver.json                     | kubernetes / API server                                |
| k8s-controller-manager.json            | kubernetes / Controller Manager                        |
| k8s-coredns.json                       | CoreDNS                                                |
| k8s-kubelet.json                       | kubernetes / Kubelet                                   |
| k8s-namespace-by-workload.json         | kubernetes / Networking - Namespace (Workloads)        |
| k8s-network-cluster-total.json         | kubernetes / Networking - Cluster                      |
| k8s-network-namespace-by-pod.json      | kubernetes / Networking - Namespace (Pods)             |
| k8s-network-namespace-by-workload.json | Kubernetes / Networking / Namespace (Workload)         |
| k8s-network-pod-total.json             | kubernetes / Networking - Pod                          |
| k8s-network-workload-total.json        | kubernetes / Networking - Workload                     |
| k8s-persistentvolumesusage.json        | kubernetes / Persistent Volumes                        |
| k8s-proxy.json                         | kubernetes / Proxy                                     |
| k8s-resources-cluster.json             | kubernetes / Compute Resources - Cluster               |
| k8s-resources-namespace.json           | kubernetes / Compute Resources - Namespace (Pods)      |
| k8s-resources-node.json                | kubernetes / Compute Resources - Node (Pods)           |
| k8s-resources-pod.json                 | kubernetes / Compute Resources - Pod                   |
| k8s-resources-workload.json            | kubernetes / Compute Resources - Workload              |
| k8s-resources-workloads-namespace.json | kubernetes / Compute Resources - Namespace (Workloads) |
| k8s-scheduler.json                     | kubernetes / Scheduler                                 |
| moc-auth-service.json                  | MOCloud / Auth-Service                                 |
| moc-instance-service.json              | MOCloud / Instance-Service                                 |
| moc-cluster-service.json               | MOCloud / Cluster-Service                              |
| moc-logs.json                          | MOCloud / Logs                                         |
| moc-nodes.json                         | MOCloud / Nodes                                        |
| moc-cAdvisor.json                      | MOCloud / cAdvisor                                     |
| node-cluster-rsrc-use.json             | Node Exporter / USE Method Cluster                     |
| node-rsrc-use.json                     | Node Exporter / USE Method Node                        |
| nodes.json                             | Node Exporter / Nodes                                  |
| nodes-darwin.json                      | Node Exporter / MacOS                                  |
| prometheus-overview.json               | Prometheus / Overview                                  |

## How to add new config ?

1. edit your new datshbord in grafana

2. download the json config file

Dashboard settting -> JSON Model -> Manually copy the JSON model context, save as file your_dashboard.json

3. rename config file

`{module}-{Dashboard-title}.json`

4. copy the json file here, and commit
