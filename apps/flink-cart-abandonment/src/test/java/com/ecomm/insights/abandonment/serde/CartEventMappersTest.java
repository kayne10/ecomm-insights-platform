package com.ecomm.insights.abandonment.serde;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.ecomm.insights.abandonment.TestSchemas;
import com.ecomm.insights.abandonment.model.CartEvent;
import java.time.Instant;
import java.util.List;
import org.apache.avro.generic.GenericData;
import org.apache.avro.generic.GenericRecordBuilder;
import org.apache.avro.util.Utf8;
import org.junit.jupiter.api.Test;

class CartEventMappersTest {

    @Test
    void mapsCheckoutStarted() {
        var record =
                new GenericRecordBuilder(TestSchemas.load("checkout_started"))
                        .set("event_id", "e1")
                        .set("event_type", "checkout_started")
                        .set("user_id", new Utf8("user-1"))
                        .set("cart_id", new Utf8("cart-1"))
                        .set("product_ids", List.of(new Utf8("sku-1"), new Utf8("sku-2")))
                        .set("item_count", 2)
                        .set("cart_value", 59.98)
                        .set("currency", "USD")
                        .set("timestamp", "2026-10-20T03:00:00.000+00:00")
                        .build();

        CartEvent event = CartEventMappers.fromCheckout(record);

        assertThat(event.type()).isEqualTo(CartEvent.Type.CHECKOUT_STARTED);
        assertThat(event.cartId()).isEqualTo("cart-1");
        assertThat(event.userId()).isEqualTo("user-1");
        assertThat(event.productIds()).containsExactly("sku-1", "sku-2");
        assertThat(event.value()).isEqualTo(59.98);
        assertThat(event.eventTime()).isEqualTo(Instant.parse("2026-10-20T03:00:00Z"));
    }

    @Test
    void mapsPurchaseWithCart() {
        var record = purchase("purchase").set("cart_id", "cart-1").build();

        CartEvent event = CartEventMappers.fromPurchase(record);

        assertThat(event.type()).isEqualTo(CartEvent.Type.PURCHASE);
        assertThat(event.cartId()).isEqualTo("cart-1");
        assertThat(event.hasCart()).isTrue();
        assertThat(event.value()).isCloseTo(12.5, within(1e-6));
    }

    @Test
    void mapsPurchaseWithoutCart() {
        assertThat(CartEventMappers.fromPurchase(purchase("purchase").build()).hasCart()).isFalse();
    }

    @Test
    void mapsPurchaseWrittenWithTheOriginalSchema() {
        // Schema v1 predates cart_id; such records must still be readable.
        assertThat(CartEventMappers.fromPurchase(purchase("purchase_v1").build()).cartId())
                .isNull();
    }

    @Test
    void failsClearlyOnMissingRequiredField() {
        // A raw record, because GenericRecordBuilder itself refuses to leave user_id empty.
        var record = new GenericData.Record(TestSchemas.load("purchase"));
        record.put("amount", 12.5f);

        assertThatThrownBy(() -> CartEventMappers.fromPurchase(record))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("user_id");
    }

    private static GenericRecordBuilder purchase(String schema) {
        return new GenericRecordBuilder(TestSchemas.load(schema))
                .set("event_id", "e2")
                .set("event_type", "purchase")
                .set("user_id", "user-1")
                .set("order_id", "order-1")
                .set("amount", 12.5f)
                .set("currency", "USD")
                .set("timestamp", "2026-10-16T05:08:14.460596");
    }
}
