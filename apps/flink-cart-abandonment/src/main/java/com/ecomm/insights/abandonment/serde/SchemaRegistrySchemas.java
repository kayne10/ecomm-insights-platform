package com.ecomm.insights.abandonment.serde;

import io.confluent.kafka.schemaregistry.client.CachedSchemaRegistryClient;
import io.confluent.kafka.schemaregistry.client.SchemaRegistryClient;
import org.apache.avro.Schema;

/**
 * Looks up Avro schemas in Schema Registry.
 *
 * <p>Event schemas are owned by the Python event classes in {@code common/events} and registered by
 * bootstrap. The job reads them back instead of keeping its own copy, so the two cannot drift.
 */
public final class SchemaRegistrySchemas {

    private static final int CACHE_CAPACITY = 16;

    private final SchemaRegistryClient client;
    private final String url;

    public SchemaRegistrySchemas(String url) {
        this.url = url;
        this.client = new CachedSchemaRegistryClient(url, CACHE_CAPACITY);
    }

    /** Subject name used for a topic's values (Confluent TopicNameStrategy). */
    public static String valueSubject(String topic) {
        return topic + "-value";
    }

    /**
     * Returns the latest registered value schema of {@code topic}.
     *
     * @throws IllegalStateException if the subject does not exist (bootstrap has not run)
     */
    public Schema latestValueSchema(String topic) {
        String subject = valueSubject(topic);
        try {
            String schema = client.getLatestSchemaMetadata(subject).getSchema();
            return new Schema.Parser().parse(schema);
        } catch (Exception e) {
            throw new IllegalStateException(
                    "Could not load schema '"
                            + subject
                            + "' from "
                            + url
                            + ". Run `make bootstrap` first.",
                    e);
        }
    }
}
