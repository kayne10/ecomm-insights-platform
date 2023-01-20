# E-commerce Data Insights Platform

Imagine orders from a online e-commerice site get emitted to Kafka. This data architecture is designed to process and ingest web orders at scale in real time. The targeted data marts are highly reliable for quick data-driven insights on products and customers. Insights Dashboard provides reports on which customers spent the most and which products earned and sold the most.

## Getting started

Spin up all services locally with
```
docker-compose up
```

Create kafka topic
```
docker exec -it kafka-cluster /bin/bash
kafka-topics --create --topic ecommerce-orders --partitions 3 --replication-factor 1 --bootstrap-server 127.0.0.1:9092
```

Create kafka-connect source and sink connectors
```
bin/kafka-connect source
bin/kafka-connect sink
```

Start stream or fabricated online orders
```
bin/stream
```


## Architecture
Diagram coming soon...

## Tech Stack
Kafka streaming
- Filestream Source connector
- Elasticsearch sink connector

Spark structured streaming
- read stream from `ecommerec-orders` topic
- add field `total_price`
- takes sum of qty and sum of order price per product every min (optional)
- write stream to `orders-enriched` or `product-metrics` topic
- sink to postgres

Data Marts
- Postgres
- Elasticsearch

Insights Dashboard
- Flask Api
- D3 or Dash

