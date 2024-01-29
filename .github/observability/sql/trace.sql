
CREATE DATABASE IF NOT EXISTS observability;

CREATE EXTERNAL TABLE IF NOT EXISTS `observability`.`spans`(
`trace_id` varchar(36) DEFAULT "0" COMMENT "TraceId",
`span_id` varchar(16) DEFAULT "0" COMMENT "SpanId",
`parent_trace_id` varchar(36) DEFAULT "0" COMMENT "Parent TraceId",
`span_kind` VARCHAR(1024) DEFAULT "internal" COMMENT "Parent TraceId",
`span_name` VARCHAR(1024) NOT NULL COMMENT "span name",
`start_time` DATETIME(6) NOT NULL COMMENT "start time",
`end_time` DATETIME(6) NOT NULL COMMENT "end time",
`duration` BIGINT UNSIGNED DEFAULT "0" COMMENT "exec time, unit: ns",
`resource` JSON NOT NULL COMMENT "key-value json",
`attributes` JSON NOT NULL COMMENT "key-value json",
`status` JSON NOT NULL COMMENT "key-value json",
`event` JSON NOT NULL COMMENT "key-value json",
`links` JSON NOT NULL COMMENT "array json"
) infile {"filepath"="etl:/sys/*/*/*/*/observability.spans/*.csv","compression"="none"} FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 0 lines;