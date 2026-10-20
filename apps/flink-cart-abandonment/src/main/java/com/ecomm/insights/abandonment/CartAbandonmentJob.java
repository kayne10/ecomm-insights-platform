package com.ecomm.insights.abandonment;

import com.ecomm.insights.abandonment.config.JobConfig;
import com.ecomm.insights.abandonment.detect.CartAbandonmentDetector;
import com.ecomm.insights.abandonment.model.CartAbandoned;
import com.ecomm.insights.abandonment.model.CartEvent;
import com.ecomm.insights.abandonment.serde.CartAbandonedSerializer;
import com.ecomm.insights.abandonment.serde.CartEventDeserializer;
import com.ecomm.insights.abandonment.serde.SchemaRegistrySchemas;
import java.util.List;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.connector.base.DeliveryGuarantee;
import org.apache.flink.connector.kafka.sink.KafkaSink;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.kafka.clients.consumer.OffsetResetStrategy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Flink job that turns checkouts without a purchase into {@code cart_abandoned} events.
 *
 * <pre>
 *   checkout-started-events ─┐
 *                            ├─ KafkaSource ─ keyBy(cart_id) ─ CartAbandonmentDetector ─ KafkaSink ─ cart-abandoned-events
 *   purchase-events ─────────┘        (event time, bounded out-of-orderness)
 * </pre>
 *
 * <p>The output topic is sunk to Elasticsearch by the generated {@code cart_abandoned_es_sink}
 * connector like any other event.
 */
public final class CartAbandonmentJob {

    private static final Logger LOG = LoggerFactory.getLogger(CartAbandonmentJob.class);

    private CartAbandonmentJob() {}

    public static void main(String[] args) throws Exception {
        JobConfig config = JobConfig.fromEnvironment();
        LOG.info("Starting cart abandonment job with {}", config);

        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.enableCheckpointing(config.checkpointInterval().toMillis());
        buildPipeline(env, config, new SchemaRegistrySchemas(config.schemaRegistryUrl()));
        env.execute("cart-abandonment");
    }

    /**
     * Wires source, detector and sink. Separate from {@link #main} to keep the topology readable.
     */
    static void buildPipeline(
            StreamExecutionEnvironment env, JobConfig config, SchemaRegistrySchemas schemas) {
        KafkaSource<CartEvent> source =
                KafkaSource.<CartEvent>builder()
                        .setBootstrapServers(config.bootstrapServers())
                        .setTopics(List.of(config.checkoutTopic(), config.purchaseTopic()))
                        .setGroupId(config.consumerGroup())
                        .setStartingOffsets(startingOffsets(config))
                        .setDeserializer(
                                CartEventDeserializer.forTopics(
                                        config.checkoutTopic(),
                                        schemas.latestValueSchema(config.checkoutTopic()),
                                        config.purchaseTopic(),
                                        schemas.latestValueSchema(config.purchaseTopic()),
                                        config.schemaRegistryUrl()))
                        .build();

        WatermarkStrategy<CartEvent> watermarks =
                WatermarkStrategy.<CartEvent>forBoundedOutOfOrderness(config.maxOutOfOrderness())
                        .withTimestampAssigner((event, ts) -> event.eventTime().toEpochMilli())
                        .withIdleness(config.sourceIdleTimeout());

        KafkaSink<CartAbandoned> sink =
                KafkaSink.<CartAbandoned>builder()
                        .setBootstrapServers(config.bootstrapServers())
                        .setRecordSerializer(
                                new CartAbandonedSerializer(
                                        config.outputTopic(),
                                        schemas.latestValueSchema(config.outputTopic()),
                                        config.schemaRegistryUrl()))
                        // Deterministic event ids make duplicates harmless downstream.
                        .setDeliveryGuarantee(DeliveryGuarantee.AT_LEAST_ONCE)
                        .build();

        DataStream<CartEvent> events =
                env.fromSource(source, watermarks, "checkouts and purchases")
                        .uid("cart-events-source");

        events.filter(CartEvent::hasCart)
                .name("with cart_id")
                .uid("with-cart-id")
                .keyBy(CartEvent::cartId)
                .process(new CartAbandonmentDetector(config.abandonmentTimeout()))
                .name("detect abandoned carts")
                .uid("cart-abandonment-detector")
                .sinkTo(sink)
                .name("cart-abandoned-events")
                .uid("cart-abandoned-sink");
    }

    /**
     * Resume from committed offsets; without any, start at the end (or the beginning if
     * configured). Starting at the end by default avoids flagging historic checkouts from before
     * purchases carried a cart_id.
     */
    // Kafka 4 deprecates OffsetResetStrategy, but connector 5.0 offers no alternative overload.
    @SuppressWarnings("deprecation")
    private static OffsetsInitializer startingOffsets(JobConfig config) {
        return OffsetsInitializer.committedOffsets(
                config.startFromEarliest()
                        ? OffsetResetStrategy.EARLIEST
                        : OffsetResetStrategy.LATEST);
    }
}
