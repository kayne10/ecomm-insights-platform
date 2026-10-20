package com.ecomm.insights.abandonment.serde;

import com.ecomm.insights.abandonment.model.CartAbandoned;
import com.ecomm.insights.abandonment.time.EventTimes;
import java.nio.charset.StandardCharsets;
import java.util.Objects;
import org.apache.avro.Schema;
import org.apache.avro.generic.GenericRecord;
import org.apache.avro.generic.GenericRecordBuilder;
import org.apache.flink.api.common.serialization.SerializationSchema;
import org.apache.flink.connector.kafka.sink.KafkaRecordSerializationSchema;
import org.apache.flink.formats.avro.registry.confluent.ConfluentRegistryAvroSerializationSchema;
import org.apache.kafka.clients.producer.ProducerRecord;

/**
 * Writes {@link CartAbandoned} events as Confluent wire-format Avro.
 *
 * <p>The record key is the event id. The Elasticsearch sink uses the key as the document id, so
 * at-least-once redelivery overwrites instead of duplicating.
 */
public final class CartAbandonedSerializer
        implements KafkaRecordSerializationSchema<CartAbandoned> {

    private static final long serialVersionUID = 1L;

    private final String topic;
    private final String schemaJson;
    private final SerializationSchema<GenericRecord> valueSerializer;
    private transient Schema schema;

    /**
     * @param topic output topic
     * @param schema the topic's registered value schema
     * @param schemaRegistryUrl Schema Registry URL
     */
    public CartAbandonedSerializer(String topic, Schema schema, String schemaRegistryUrl) {
        this.topic = Objects.requireNonNull(topic, "topic");
        this.schemaJson = schema.toString();
        this.valueSerializer =
                ConfluentRegistryAvroSerializationSchema.forGeneric(
                        SchemaRegistrySchemas.valueSubject(topic), schema, schemaRegistryUrl);
    }

    @Override
    public void open(
            SerializationSchema.InitializationContext context, KafkaSinkContext sinkContext)
            throws Exception {
        valueSerializer.open(context);
        schema = new Schema.Parser().parse(schemaJson);
    }

    @Override
    public ProducerRecord<byte[], byte[]> serialize(
            CartAbandoned event, KafkaSinkContext context, Long timestamp) {
        byte[] key = event.eventId().getBytes(StandardCharsets.UTF_8);
        byte[] value = valueSerializer.serialize(toAvro(event, schema));
        return new ProducerRecord<>(topic, null, event.abandonedAt().toEpochMilli(), key, value);
    }

    /**
     * Converts an event to an Avro record of the given schema. Fails fast if the schema is missing
     * a field this job writes, e.g. if the Python event class changed incompatibly.
     */
    static GenericRecord toAvro(CartAbandoned event, Schema schema) {
        return new GenericRecordBuilder(schema)
                .set("event_id", event.eventId())
                .set("event_type", CartAbandoned.EVENT_TYPE)
                .set("user_id", event.userId())
                .set("cart_id", event.cartId())
                .set("product_ids", event.productIds())
                .set("item_count", event.itemCount())
                .set("cart_value", event.cartValue())
                .set("currency", event.currency())
                .set("checkout_at", EventTimes.format(event.checkoutAt()))
                .set("timeout_seconds", event.timeoutSeconds())
                .set("timestamp", EventTimes.format(event.abandonedAt()))
                .build();
    }
}
