package main

import (
	"log"
	"os"
	"text/template"
)

func main() {
	var CI_SMTP_HOST, CI_SMTP_USER, CI_SMTP_PASSWORD string
	CI_SMTP_USER = os.Getenv("CI_SMTP_USER")
	CI_SMTP_HOST = os.Getenv("CI_SMTP_HOST")
	CI_SMTP_PASSWORD = os.Getenv("CI_SMTP_PASSWORD")
	kv := map[string]string{
		"CI_SMTP_USER":     CI_SMTP_USER,
		"CI_SMTP_HOST":     CI_SMTP_HOST,
		"CI_SMTP_PASSWORD": CI_SMTP_PASSWORD,
	}
	tmpl, err := template.ParseFiles("./.github/observability/script/alertmanager_template.yml")
	if err != nil {
		log.Fatalf("create template failed, err:%v", err)
		os.Exit(1)
	}
	f, err := os.OpenFile("./.github/observability/alertmanager.yml", os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0644)
	if err != nil {
		log.Fatalf("create template failed, err:%v", err)
		os.Exit(1)
	}
	defer f.Close()
	// 利用给定数据渲染模板，并将结果写入w
	tmpl.Execute(f, kv)
}
