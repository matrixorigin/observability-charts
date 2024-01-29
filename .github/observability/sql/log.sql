CREATE DATABASE IF NOT EXISTS observability;

CREATE EXTERNAL TABLE IF NOT EXISTS `observability`.`logs`(
`trace_id` varchar(36) DEFAULT "0" COMMENT "related request's TraceId",
`span_id` varchar(16) DEFAULT "0" COMMENT "related request's SpanId",
`timestamp` DATETIME(6) NOT NULL COMMENT "log recorded timestamp",
`collect_time` DATETIME(6) NOT NULL COMMENT "log recorded timestamp",
`logger_name` VARCHAR(1024) NOT NULL COMMENT "logger name",
`level` VARCHAR(1024) NOT NULL COMMENT "log level, enum: debug, info, warn, error, panic, fatal",
`caller` VARCHAR(1024) NOT NULL COMMENT "log caller, like: package/file.go:123",
`message` TEXT NOT NULL COMMENT "log message content",
`stack` VARCHAR(1024) NOT NULL COMMENT "log caller stack info",
`labels` JSON NOT NULL COMMENT "key-value json mark labels"
) infile {"filepath"="etl:/sys/*/*/*/*/observability.logs/*.csv","compression"="none"} FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 0 lines;