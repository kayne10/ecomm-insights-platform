package com.ecomm.insights.abandonment.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Duration;
import java.util.Map;
import org.junit.jupiter.api.Test;

class JobConfigTest {

    @Test
    void appliesDefaultsForTheComposeNetwork() {
        JobConfig config = JobConfig.fromMap(Map.of());

        assertThat(config.bootstrapServers()).isEqualTo("kafka:9092");
        assertThat(config.schemaRegistryUrl()).isEqualTo("http://schema-registry:8081");
        assertThat(config.checkoutTopic()).isEqualTo("checkout-started-events");
        assertThat(config.purchaseTopic()).isEqualTo("purchase-events");
        assertThat(config.outputTopic()).isEqualTo("cart-abandoned-events");
        assertThat(config.startFromEarliest()).isFalse();
        assertThat(config.abandonmentTimeout()).isEqualTo(Duration.ofMinutes(2));
    }

    @Test
    void readsOverridesAndFlinkDurationSyntax() {
        JobConfig config =
                JobConfig.fromMap(
                        Map.of(
                                "ABANDONMENT_TIMEOUT", "15 min",
                                "MAX_OUT_OF_ORDERNESS", "10s",
                                "START_FROM_EARLIEST", "true",
                                "OUTPUT_TOPIC", "abandoned"));

        assertThat(config.abandonmentTimeout()).isEqualTo(Duration.ofMinutes(15));
        assertThat(config.maxOutOfOrderness()).isEqualTo(Duration.ofSeconds(10));
        assertThat(config.startFromEarliest()).isTrue();
        assertThat(config.outputTopic()).isEqualTo("abandoned");
    }

    @Test
    void rejectsNonPositiveDurations() {
        assertThatThrownBy(() -> JobConfig.fromMap(Map.of("ABANDONMENT_TIMEOUT", "0 s")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("abandonmentTimeout");
    }
}
