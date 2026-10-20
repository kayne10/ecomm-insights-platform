package com.ecomm.insights.abandonment.serde;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.ecomm.insights.abandonment.TestSchemas;
import com.ecomm.insights.abandonment.model.CartAbandoned;
import com.ecomm.insights.abandonment.model.CartEvent;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import org.apache.avro.Schema;
import org.apache.avro.generic.GenericData;
import org.apache.avro.generic.GenericRecord;
import org.junit.jupiter.api.Test;

class CartAbandonedSerializerTest {

    private static final CartAbandoned EVENT =
            CartAbandoned.fromCheckout(
                    CartEvent.checkoutStarted(
                            "cart-1",
                            "user-1",
                            List.of("sku-1", "sku-2"),
                            59.98,
                            "USD",
                            Instant.parse("2026-10-20T03:00:00Z")),
                    Duration.ofMinutes(2));

    @Test
    void fillsEveryFieldOfThePythonDefinedSchema() {
        Schema schema = TestSchemas.load("cart_abandoned");

        GenericRecord record = CartAbandonedSerializer.toAvro(EVENT, schema);

        assertThat(GenericData.get().validate(schema, record)).isTrue();
        assertThat(record.get("event_type")).isEqualTo("cart_abandoned");
        assertThat(record.get("cart_id")).isEqualTo("cart-1");
        assertThat(record.get("item_count")).isEqualTo(2);
        assertThat(record.get("timeout_seconds")).isEqualTo(120L);
        assertThat(record.get("checkout_at")).isEqualTo("2026-10-20T03:00:00Z");
        assertThat(record.get("timestamp")).isEqualTo("2026-10-20T03:02:00Z");
    }

    @Test
    void failsFastWhenTheSchemaLacksAField() {
        Schema incompatible =
                new Schema.Parser()
                        .parse(
                                """
                                {"type": "record", "name": "cart_abandoned", "fields": [
                                  {"name": "event_id", "type": "string"}
                                ]}
                                """);

        assertThatThrownBy(() -> CartAbandonedSerializer.toAvro(EVENT, incompatible))
                .isInstanceOf(RuntimeException.class);
    }
}
