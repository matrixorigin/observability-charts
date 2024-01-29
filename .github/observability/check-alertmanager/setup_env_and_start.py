import yaml
import os
import re
import subprocess
import base64

# test in local
# os.chdir('../../../')
os.system("pwd")
os.system("ls")
email_to=os.getenv('EMAIL_TO')
smtp=os.getenv('CI_SMTP_PASSWORD')
base64_smtp = base64.b64encode(smtp.encode("ascii")).decode("ascii")

yamlPath="charts/mo-ruler-stack/values.yaml"
valuesFileReader = open(yamlPath, 'r', encoding='utf-8')
cfg=yaml.full_load(valuesFileReader.read())["alertmanager"]
os.system("kubectl create namespace mo-ob --dry-run=client -o yaml | kubectl apply -f -")
serviceFile = open(".github/observability/check-alertmanager/echo-server/echo-server-service.yaml", "a")  # append mode
url_re=r"(^[a-z][a-z0-9+\-.]*):\/\/([a-z0-9\-._~%!$&'()*+,;=]+@)?([a-z0-9\-._~%]+|\[[a-z0-9\-._~%!$&'()*+,;=:]+\]):?([0-9]+)?"
# change webhook dns to echoserver
receivers=cfg["config"]["receivers"]
cmd="helm install mo-ruler-stack ./charts/mo-ruler-stack --wait -n mo-ob --set moRuler.enabled=false,grafana.enabled=false,alertmanager.persistence.enabled=false,secretValue.alertmanager_email_secret={}".format(base64_smtp)
alias=""
hasWebhook=False
print("detect receivers:")
hostNameIndex=0
change_email=[]
for receiver in receivers:
  print(receiver)
  if receiver.get("email_configs") is not None:
    for config in receiver["email_configs"]:
      change_email.append(config["to"])
    # {'name': 'default-receiver', 'email_configs': [{'to': 'moc-warning@matrixone.cloud'}]}
  if receiver.get("webhook_configs") is not None:
    hasWebhook=True
    # {'name': 'notify-user', 'webhook_configs': [{'url': 'http://mailservice.mo-cloud:8020/alerts', 'http_config': {'authorization': {'type': 'Bearer', 'credentials_file': '/tmp/instance-service-webhook-authorization/instance-service'}}}]}
    for config in receiver["webhook_configs"]:
      url=config["url"]
      res=re.search(url_re,url)
      host=res.group(3)
      port=res.group(4)
      if port != None:
        serviceFile.write("\n")
        serviceFile.write("    - name: %s\n"%host.replace(".","-"))
        serviceFile.write("      protocol: TCP\n")
        serviceFile.write("      port: %s\n"%port)
        serviceFile.write("      targetPort: 3246")
      alias +=' --set alertmanager.hostAliases[0].hostnames[%d]=' % hostNameIndex +'"%s"' % host
      hostNameIndex=hostNameIndex+1
serviceFile.close()
valuesFileReader.close()
for email in change_email:
  c="sed -i '' 's/{old}/{new}/g' {file}".format(old=email,new=email_to,file=yamlPath)
  print(c)
  os.system(c)
if hasWebhook:
  os.system("kubectl apply -n mo-ob -f .github/observability/check-alertmanager/echo-server/echo-server-statefulset.yaml")
  os.system("kubectl apply -n mo-ob -f .github/observability/check-alertmanager/echo-server/echo-server-service.yaml")
  serviceIP=subprocess.check_output("kubectl get svc -n mo-ob echo-server -o jsonpath='{.spec.clusterIP}'",shell=True).decode()
  alias =' --set alertmanager.hostAliases[0].ip="%s"' % serviceIP +alias
  
cmd = cmd +alias
print("final helm cmd:")
print(cmd)
os.system(cmd)
