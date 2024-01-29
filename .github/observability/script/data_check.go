package main

import (
	"database/sql"
	"fmt"
	"log"
	"time"

	"github.com/go-sql-driver/mysql"
)

const pingCnt = 60
const pingInterval = 3 * time.Second
const retryCnt = 60
const retryInterval = 3 * time.Second

func main() {

	log.Printf("waiting 150s for mo-agent prepare to insert")
	time.Sleep(150 * time.Second)

	db, err := CreateDbConn(6001, "127.0.0.1", "dump", "111", "observability")
	log.Printf("connect db done.")
	if err != nil {
		log.Fatalf("failed to connect db: %s", err)
	}

	defer db.Close()

	sqls := []string{
		// metrics from prometheus agent
		// counter type metric
		"SELECT * FROM mo_ob_metrics.prometheus_agent_samples_appended_total LIMIT 10;",
		// gauge type metric
		"SELECT * FROM mo_ob_metrics.prometheus_target_metadata_cache_bytes  LIMIT 10;",
		// summary type metric
		"SELECT * FROM mo_ob_metrics.prometheus_agent_data_replay_duration_seconds LIMIT 10;",
		// histogram type metric
		"SELECT * FROM mo_ob_metrics.prometheus_http_request_duration_seconds_bucket  LIMIT 10;",
		// logs from fluentbit
		"SELECT * FROM mo_ob_logs.default_service WHERE message='test1' LIMIT 10;",
		"SELECT * FROM mo_ob_logs.default_service WHERE message='test2' LIMIT 10;",
		"SELECT * FROM mo_ob_logs.default_service WHERE message='test3' LIMIT 10;",
		"SELECT * FROM mo_ob_logs.default_service WHERE message='test4' LIMIT 10;",
		"SELECT * FROM mo_ob_logs.default_service WHERE message='test5' LIMIT 10;",
	}

	for _, sql := range sqls {
		for idx := 0; idx <= retryCnt; idx++ {
			log.Printf("exec sql %d time: %s", idx, sql)
			rows, err := db.Query(sql)
			if err != nil {
				if idx == retryCnt {
					log.Fatalf("query from mo failed err: %v, try again", err)
				}
				time.Sleep(retryInterval)
				continue
			}
			count := 0
			for rows.Next() {
				count += 1
			}
			if count == 0 {
				if idx == retryCnt {
					log.Fatalf("no specific data")
				}
				log.Printf("no specific data, try again")
				time.Sleep(retryInterval)
				continue
			}
			log.Printf("exec sql got rows: %d", count)
			rows.Close()
			break
		}
	}
	log.Printf("metric and log data from mo-agent is ready")
}

func CreateDbConn(port int, host, user, password, database string) (conn *sql.DB, err error) {

	log.Printf("connect db...")
	mysql.SetLogger(log.Default()) //设置go-mysql-driver的日志

	timeout := 6000 * time.Second
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?parseTime=true&readTimeout=%s&writeTimeout=%s&timeout=%s",
		user, password, host, port, database, timeout, timeout, timeout)

	if conn, err = sql.Open("mysql", dsn); err != nil { //创建db
		log.Printf("waiting mysql to start...")
		return nil, err
	}
	conn.SetMaxIdleConns(100)
	conn.SetMaxOpenConns(100)

	// ping and return
	for i := 0; ; {
		if err = conn.Ping(); err == nil {
			return conn, nil
		}
		if i++; i >= pingCnt {
			log.Printf("Ping failed over %d time(s)", pingCnt)
			return nil, err
		}
		log.Printf("Ping %d time(s): %s, try again", i, err)
		time.Sleep(pingInterval)
	}
}
