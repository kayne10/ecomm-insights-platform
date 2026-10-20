package com.ecomm.insights.abandonment.config;

import java.time.Duration;
import java.util.Map;
import java.util.Objects;
import java.util.function.Function;
import org.apache.flink.util.TimeUtils;

/**
 * Job settings, read from environment variables so they can be set in docker-compose.
 *
 * <p>Durations accept Flink's syntax, e.g. {@code 90s}, {@code 2 min}, {@code 1h}.
 *
 * @param bootstrapServers Kafka bootstrap servers ({@code KAFKA_BOOTSTRAP_SERVERS})
 * @param schemaRegistryUrl Schema Registry URL ({@code SCHEMA_REGISTRY_URL})
 * @param checkoutTopic input topic of checkout_started events ({@code CHECKOUT_TOPIC})
 * @param purchaseTopic input topic of purchase events ({@code PURCHASE_TOPIC})
 * @param outputTopic output topic of cart_abandoned events ({@code OUTPUT_TOPIC})
 * @param consumerGroup Kafka consumer group for offset commits ({@code CONSUMER_GROUP})
 * @param startFromEarliest read input from the beginning when the group has no committed offsets,
 *     instead of from the end ({@code START_FROM_EARLIEST})
 * @param abandonmentTimeout how long after checkout a cart without purchase is abandoned ({@code
 *     ABANDONMENT_TIMEOUT})
 * @param maxOutOfOrderness how late events may arrive relative to each other ({@code
 *     MAX_OUT_OF_ORDERNESS})
 * @param sourceIdleTimeout after this long without data a partition stops holding back the
 *     watermark ({@code SOURCE_IDLE_TIMEOUT})
 * @param checkpointInterval how often state is checkpointed and offsets committed ({@code
 *     CHECKPOINT_INTERVAL})
 */
public record JobConfig(
        String bootstrapServers,
        String schemaRegistryUrl,
        String checkoutTopic,
        String purchaseTopic,
        String outputTopic,
        String consumerGroup,
        boolean startFromEarliest,
        Duration abandonmentTimeout,
        Duration maxOutOfOrderness,
        Duration sourceIdleTimeout,
        Duration checkpointInterval) {

    public JobConfig {
        Objects.requireNonNull(bootstrapServers, "bootstrapServers");
        Objects.requireNonNull(schemaRegistryUrl, "schemaRegistryUrl");
        Objects.requireNonNull(checkoutTopic, "checkoutTopic");
        Objects.requireNonNull(purchaseTopic, "purchaseTopic");
        Objects.requireNonNull(outputTopic, "outputTopic");
        Objects.requireNonNull(consumerGroup, "consumerGroup");
        requirePositive(abandonmentTimeout, "abandonmentTimeout");
        requirePositive(maxOutOfOrderness, "maxOutOfOrderness");
        requirePositive(sourceIdleTimeout, "sourceIdleTimeout");
        requirePositive(checkpointInterval, "checkpointInterval");
    }

    /** Reads the configuration from the process environment. */
    public static JobConfig fromEnvironment() {
        return fromMap(System.getenv());
    }

    /** Reads the configuration from a map of environment-style keys, applying defaults. */
    public static JobConfig fromMap(Map<String, String> env) {
        Function<String, Duration> duration = TimeUtils::parseDuration;
        return new JobConfig(
                env.getOrDefault("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
                env.getOrDefault("SCHEMA_REGISTRY_URL", "http://schema-registry:8081"),
                env.getOrDefault("CHECKOUT_TOPIC", "checkout-started-events"),
                env.getOrDefault("PURCHASE_TOPIC", "purchase-events"),
                env.getOrDefault("OUTPUT_TOPIC", "cart-abandoned-events"),
                env.getOrDefault("CONSUMER_GROUP", "flink-cart-abandonment"),
                Boolean.parseBoolean(env.getOrDefault("START_FROM_EARLIEST", "false")),
                duration.apply(env.getOrDefault("ABANDONMENT_TIMEOUT", "2 min")),
                duration.apply(env.getOrDefault("MAX_OUT_OF_ORDERNESS", "5 s")),
                duration.apply(env.getOrDefault("SOURCE_IDLE_TIMEOUT", "30 s")),
                duration.apply(env.getOrDefault("CHECKPOINT_INTERVAL", "30 s")));
    }

    private static void requirePositive(Duration value, String name) {
        Objects.requireNonNull(value, name);
        if (value.isNegative() || value.isZero()) {
            throw new IllegalArgumentException(name + " must be positive: " + value);
        }
    }
}
