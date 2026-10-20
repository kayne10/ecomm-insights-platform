package com.ecomm.insights.abandonment.serde;

import com.ecomm.insights.abandonment.model.CartEvent;
import java.io.IOException;
import java.io.Serializable;
import java.util.Map;
import java.util.function.Function;
import org.apache.avro.Schema;
import org.apache.avro.generic.GenericRecord;
import org.apache.flink.api.common.serialization.DeserializationSchema;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.connector.kafka.source.reader.deserializer.KafkaRecordDeserializationSchema;
import org.apache.flink.formats.avro.registry.confluent.ConfluentRegistryAvroDeserializationSchema;
import org.apache.flink.util.Collector;
import org.apache.kafka.clients.consumer.ConsumerRecord;

/**
 * Deserializes checkout and purchase records from one Kafka source into {@link CartEvent}s.
 *
 * <p>Each topic has its own Avro reader schema and mapper; the record's topic picks which one is
 * used. Values are Confluent wire-format Avro, so writer schemas are resolved via Schema Registry
 * and older records (e.g. purchases without {@code cart_id}) are read with the field's default.
 */
public final class CartEventDeserializer implements KafkaRecordDeserializationSchema<CartEvent> {

    private static final long serialVersionUID = 1L;

    private final Map<String, TopicReader> readers;

    private CartEventDeserializer(Map<String, TopicReader> readers) {
        this.readers = Map.copyOf(readers);
    }

    /** Creates a deserializer for the checkout and purchase topics. */
    public static CartEventDeserializer forTopics(
            String checkoutTopic,
            Schema checkoutSchema,
            String purchaseTopic,
            Schema purchaseSchema,
            String schemaRegistryUrl) {
        return new CartEventDeserializer(
                Map.of(
                        checkoutTopic,
                        new TopicReader(
                                ConfluentRegistryAvroDeserializationSchema.forGeneric(
                                        checkoutSchema, schemaRegistryUrl),
                                CartEventMappers::fromCheckout),
                        purchaseTopic,
                        new TopicReader(
                                ConfluentRegistryAvroDeserializationSchema.forGeneric(
                                        purchaseSchema, schemaRegistryUrl),
                                CartEventMappers::fromPurchase)));
    }

    @Override
    public void open(DeserializationSchema.InitializationContext context) throws Exception {
        for (TopicReader reader : readers.values()) {
            reader.avro.open(context);
        }
    }

    @Override
    public void deserialize(ConsumerRecord<byte[], byte[]> record, Collector<CartEvent> out)
            throws IOException {
        TopicReader reader = readers.get(record.topic());
        if (reader == null) {
            throw new IOException("Unexpected topic: " + record.topic());
        }
        if (record.value() == null) {
            return; // tombstone
        }
        out.collect(reader.mapper.apply(reader.avro.deserialize(record.value())));
    }

    @Override
    public TypeInformation<CartEvent> getProducedType() {
        return TypeInformation.of(CartEvent.class);
    }

    /** A record mapper that can be shipped to the task managers. */
    @FunctionalInterface
    interface RecordMapper extends Function<GenericRecord, CartEvent>, Serializable {}

    private record TopicReader(DeserializationSchema<GenericRecord> avro, RecordMapper mapper)
            implements Serializable {
        private static final long serialVersionUID = 1L;
    }
}
