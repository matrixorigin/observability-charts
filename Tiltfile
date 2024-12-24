
command = os.getenv('TILT_COMMAND', 'default')
load('ext://helm_remote', 'helm_remote')

def deploy_minio():
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

def deploy_moc_ob():
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

  k8s_yaml("./dev/loki_test_rule.yaml")

def deploy_ob_private():
  local('kubectl get ns mo-ob || kubectl create ns mo-ob')
  mo_ob_private_chart = './charts/mo-ob-private'

  k8s_yaml(
    helm(
      mo_ob_private_chart,
      name='mo-ob-private',
      namespace='mo-ob',
      values=['./dev/mo-ob-private.dev.yaml'],
    )
  )

if command == 'moc':
    deploy_minio()
    deploy_moc_ob()
elif command == 'ob-single':
    deploy_moc_ob()
elif command == 'private':
    deploy_minio()
    deploy_ob_private()
elif command == 'minio':
    deploy_minio()
else:
    print('Unknown command, please use TILT_COMMAND=moc or TILT_COMMAND=private')