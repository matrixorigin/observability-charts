
local('kubectl get ns mo-ob || kubectl create ns mo-ob')
local('kubectl get ns minio-operator || kubectl create ns minio-operator')
local('kubectl get ns minio-tenant-loki || kubectl create ns minio-tenant-loki')
# minio for loki
k8s_yaml(
  helm('dev/minio-operator',
       name='minio-operator', 
       namespace='minio-operator',
       values=['./dev/minios.yaml']
  )
)

k8s_yaml(
  helm('dev/minio-tenant',
       name='minio-tenant', 
       namespace='minio-tenant-loki',
       values=['./dev/loki-tenant.yaml']
  )
)

helm upgrade minio-tenant apps/minio-tenant -f apps/minio-tenant/custom/test1.yaml -n s3-minio-tenant-test1 --create-namespace --install --wait
# helm upgrade minio-tenant apps/minio-tenant -f apps/minio-tenant/custom/test1.yaml -n s3-minio-tenant-test1 --create-namespace --install --wait

# helm upgrade minio-tenant apps/minio-tenant -f apps/minio-tenant/custom/test2.yaml -n s3-minio-tenant-test2 --create-namespace --install --wait


# 设置 Helm Chart 的本地路径

mo_ob_opensource_chart = './charts/mo-ob-opensource'
mo_ruler_stack_chart = './charts/mo-ruler-stack'

k8s_yaml(
  helm(mo_ruler_stack_chart,
       name='mo-ruler-stack', 
       namespace='mo-ob', 
       values=['./dev/values.dev.yaml']
  )
)