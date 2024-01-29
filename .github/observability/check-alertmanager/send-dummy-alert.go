package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"github.com/prometheus/prometheus/model/labels"
	"github.com/prometheus/prometheus/model/rulefmt"
	"github.com/prometheus/prometheus/notifier"
	"github.com/prometheus/prometheus/promql/parser"
	"github.com/prometheus/prometheus/util/strutil"
)

var ALERTMANAGER_URL = "http://127.0.0.1:9099/api/v1/alerts"

func main() {
	var RULES_FILE_PATH string
	RULES_FILE_PATH = os.Getenv("RULES_FILE_PATH")
	if RULES_FILE_PATH == "" {
		RULES_FILE_PATH = "../../../charts/mo-ruler-stack/rules/*.yaml"
	}
	fmt.Println(RULES_FILE_PATH)
	paths := []string{RULES_FILE_PATH}
	files := []string{}
	for _, pat := range paths {
		fs, err := filepath.Glob(pat)
		if err != nil {
			// The only error can be a bad pattern.
			fmt.Errorf("error retrieving rule files for %s: %w", pat, err)
		}
		files = append(files, fs...)
	}
	rules, errs := LoadAlertingRules(files...)
	if len(errs) > 0 {
		fmt.Println(errs)
	}

	sendAll(rules...)
	time.Sleep(30 * time.Second)
	fmt.Printf("%d alert sended to alertmanager", len(rules))
}

func LoadAlertingRules(filenames ...string) ([]*notifier.Alert, []error) {
	var allAlerts []*notifier.Alert
	for _, fn := range filenames {
		rgs, errs := rulefmt.ParseFile(fn)
		if errs != nil {
			return nil, errs
		}
		for _, rg := range rgs.Groups {
			curRules := make([]*notifier.Alert, 0, len(rg.Rules))
			for _, r := range rg.Rules {
				expr, err := Parse(r.Expr.Value)
				if err != nil {
					return nil, []error{fmt.Errorf("%s: %w", fn, err)}
				}
				if r.Alert.Value != "" {
					lb := labels.NewBuilder(labels.FromMap(r.Labels))
					// lb.Set(labels.MetricName, "ALERTS")
					lb.Set(labels.AlertName, r.Alert.Value)
					// lb.Set("alertstate", "firing")
					na := &notifier.Alert{
						StartsAt:     time.Now(),
						Labels:       lb.Labels(nil),
						Annotations:  labels.FromMap(r.Annotations),
						GeneratorURL: "" + strutil.TableLinkForExpression(expr.String()),
					}

					fmt.Println(na.Labels)
					curRules = append(curRules, na)
					continue
				}

			}
			allAlerts = append(allAlerts, curRules...)
		}
	}
	return allAlerts, nil
}

func Parse(query string) (parser.Expr, error) { return parser.ParseExpr(query) }

func sendAll(alerts ...*notifier.Alert) {

	var v1Payload []byte

	var (
		payload []byte
		err     error
	)

	if v1Payload == nil {
		v1Payload, err = json.Marshal(alerts)
		if err != nil {
			log.Fatal("msg", "Encoding alerts for Alertmanager API v1 failed", "err", err)
		}
	}

	payload = v1Payload
	client := http.DefaultClient

	if err := sendOne(context.Background(), client, ALERTMANAGER_URL, payload); err != nil {
		log.Fatal("alertmanager", ALERTMANAGER_URL, "count", len(alerts), "msg", "Error sending alert", "err", err)
	}

}

func sendOne(ctx context.Context, c *http.Client, url string, b []byte) error {
	req, err := http.NewRequest("POST", url, bytes.NewReader(b))
	if err != nil {
		return err
	}
	req.Header.Set("User-Agent", "userAgent")
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.Do(req.WithContext(ctx))
	if err != nil {
		return err
	}
	defer func() {
		io.Copy(io.Discard, resp.Body)
		resp.Body.Close()
	}()

	// Any HTTP status 2xx is OK.
	if resp.StatusCode/100 != 2 {
		return fmt.Errorf("bad response status %s", resp.Status)
	}

	return nil
}
