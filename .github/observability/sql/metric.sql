
CREATE DATABASE IF NOT EXISTS observability;

CREATE EXTERNAL TABLE IF NOT EXISTS `observability`.`metrics`(
`name` VARCHAR(1024) NOT NULL COMMENT "metric name",
`timestamp` DATETIME(6) NOT NULL COMMENT "metric data collect time",
`value` DOUBLE DEFAULT "0.0" COMMENT "metric value",
`labels` JSON NOT NULL COMMENT "key-value json mark labels",
`series_id` VARCHAR(1024) NOT NULL COMMENT "abstract of json labels"
) infile {"filepath"="etl:/sys/*/*/*/*/observability.metrics/*.csv","compression"="none"} FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 0 lines;
