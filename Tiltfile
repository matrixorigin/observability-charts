load('ext://helm_remote', 'helm_remote')
helm_remote(
  'operator', 
  repo_url='https://operator.min.io', 
  release_name='minio-operator', 
  namespace='minio-operator', 
  version='6.0.2',
  create_namespace=True,
)

helm_remote(
  'tenant', 
  repo_url='https://operator.min.io', 
  release_name='loki-tenant', 
  namespace='loki-tenant', 
  version='6.0.2',    
  values=['./dev/loki-tenant.yaml'],
  create_namespace=True,
)

# 设置 Helm Chart 的本地路径
mo_ob_opensource_chart = './charts/mo-ob-opensource'
mo_ruler_stack_chart = './charts/mo-ruler-stack'

local('kubectl get ns mo-ob || kubectl create ns mo-ob')

k8s_yaml(
  helm(
    mo_ruler_stack_chart,
    name='mo-ruler-stack',
    namespace='mo-ob',
    values=['./dev/mo-ruler-stack.dev.yaml'],
  )
)

k8s_yaml(
  helm(
    mo_ob_opensource_chart,
    name='mo-ob-opensource',
    namespace='mo-ob',
    values=['./dev/mo-ob-opensource.dev.yaml'],
  )
)