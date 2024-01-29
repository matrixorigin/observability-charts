package main

import (
	"io"
	"log"
	"math"
	"net/http"
	"os"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
	// 定义一个空的采集
	reg = prometheus.NewRegistry()
	// Counter类型的指标
	opsProcessed = prometheus.NewCounter(prometheus.CounterOpts{
		Name: "myapp_processed_ops_total",
		Help: "The total number of processed events",
	})
	// Gauge类型的指标
	opsQueued = prometheus.NewGauge(prometheus.GaugeOpts{
		Namespace: "mo",
		Subsystem: "blob_storage",
		Name:      "ops_queued",
		Help:      "Number of blob storage operations waiting to be processed.",
	})
	// Histogram类型的指标
	temps = prometheus.NewHistogram(prometheus.HistogramOpts{
		Name:    "pond_temperature_celsius",
		Help:    "The temperature of the frog pond.", // Sorry, we can't measure how badly it smells.
		Buckets: prometheus.LinearBuckets(20, 5, 5),  // 5 buckets, each 5 centigrade wide.
	})
	// Summary类型的指标
	temps_summary = prometheus.NewSummary(prometheus.SummaryOpts{
		Name:       "pond_temperature_celsius_summary",
		Help:       "The temperature of the frog pond.",
		Objectives: map[float64]float64{0.5: 0.05, 0.9: 0.01, 0.99: 0.001},
	})
)

// 模拟数据变化
func metricsChange() {
	go func() {
		for {
			opsProcessed.Inc()
			// 10 operations queued by the goroutine managing incoming requests.
			opsQueued.Add(1)
			time.Sleep(2 * time.Second)
			// A worker goroutine has picked up a waiting operation.
			opsQueued.Dec()

			// Simulate some observations.
			for i := 0; i < 20; i++ {
				temps.Observe(30 + math.Floor(120*math.Sin(float64(i)*0.1))/10)
			}

			// Simulate some observations.
			for i := 0; i < 20; i++ {
				temps_summary.Observe(30 + math.Floor(120*math.Sin(float64(i)*0.1))/10)
			}

		}
	}()
}

func main() {
	metricsChange()
	// 将所有采集器注册到reg里
	reg.MustRegister(opsProcessed, opsQueued, temps, temps_summary)
	// 同时采集多指标需要这样写handler
	http.Handle("/metrics", promhttp.HandlerFor(reg, promhttp.HandlerOpts{Registry: reg}))
	go func() {
		// curl http://localhost:2112/metrics
		http.ListenAndServe(":2112", nil)
	}()
	time.Sleep(5 * time.Second)
	resp, err := http.Get("http://localhost:2112/metrics")
	if err != nil {
		log.Printf("mock server fail to mock")
		os.Exit(1)
	}
	defer resp.Body.Close()
	b, err := io.ReadAll(resp.Body)
	// b, err := ioutil.ReadAll(resp.Body)  Go.1.15 and earlier
	if err != nil {
		log.Printf("mock server fail to mock")
		os.Exit(1)
	}
	log.Printf(string(b))
}
