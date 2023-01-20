# E-commerce Data Insights Platform

Imagine orders from a online e-commerice site get emitted to Kafka. This data architecture is designed to process and ingest web orders at scale in real time. The targeted data marts are highly reliable for quick data-driven insights on products and customers. Insights Dashboard provides reports on which customers spent the most and which products earned and sold the most.

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

