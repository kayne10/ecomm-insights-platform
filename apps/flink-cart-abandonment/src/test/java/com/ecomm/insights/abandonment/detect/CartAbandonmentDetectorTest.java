package com.ecomm.insights.abandonment.detect;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.ecomm.insights.abandonment.model.CartAbandoned;
import com.ecomm.insights.abandonment.model.CartEvent;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import org.apache.flink.api.common.typeinfo.Types;
import org.apache.flink.streaming.util.KeyedOneInputStreamOperatorTestHarness;
import org.apache.flink.streaming.util.ProcessFunctionTestHarnesses;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class CartAbandonmentDetectorTest {

    private static final Duration TIMEOUT = Duration.ofMinutes(2);
    private static final Instant T0 = Instant.parse("2026-10-20T03:00:00Z");

    private KeyedOneInputStreamOperatorTestHarness<String, CartEvent, CartAbandoned> harness;

    @BeforeEach
    void setUp() throws Exception {
        harness =
                ProcessFunctionTestHarnesses.forKeyedProcessFunction(
                        new CartAbandonmentDetector(TIMEOUT), CartEvent::cartId, Types.STRING);
    }

    @AfterEach
    void tearDown() throws Exception {
        harness.close();
    }

    @Test
    void checkoutWithoutPurchaseIsAbandonedWhenTheTimeoutPasses() throws Exception {
        send(checkout("cart-1", T0));

        advanceWatermarkTo(T0.plus(TIMEOUT).minusMillis(1));
        assertThat(harness.extractOutputValues()).isEmpty();

        advanceWatermarkTo(T0.plus(TIMEOUT));
        List<CartAbandoned> output = harness.extractOutputValues();
        assertThat(output).hasSize(1);
        assertThat(output.get(0).cartId()).isEqualTo("cart-1");
        assertThat(output.get(0).abandonedAt()).isEqualTo(T0.plus(TIMEOUT));
        assertThat(harness.numKeyedStateEntries()).isZero();
    }

    @Test
    void purchaseWithinTheTimeoutConvertsTheCart() throws Exception {
        send(checkout("cart-1", T0));
        send(purchase("cart-1", T0.plusSeconds(30)));

        advanceWatermarkTo(T0.plus(TIMEOUT.multipliedBy(3)));

        assertThat(harness.extractOutputValues()).isEmpty();
        assertThat(harness.numKeyedStateEntries()).isZero();
    }

    @Test
    void purchaseArrivingBeforeItsCheckoutStillConvertsTheCart() throws Exception {
        send(purchase("cart-1", T0.plusSeconds(30)));
        send(checkout("cart-1", T0));

        advanceWatermarkTo(T0.plus(TIMEOUT.multipliedBy(3)));

        assertThat(harness.extractOutputValues()).isEmpty();
    }

    @Test
    void cartsAreTrackedIndependently() throws Exception {
        send(checkout("cart-1", T0));
        send(checkout("cart-2", T0.plusSeconds(10)));
        send(purchase("cart-2", T0.plusSeconds(20)));

        advanceWatermarkTo(T0.plus(TIMEOUT.multipliedBy(3)));

        assertThat(harness.extractOutputValues())
                .extracting(CartAbandoned::cartId)
                .containsExactly("cart-1");
    }

    @Test
    void repeatedCheckoutRestartsTheClock() throws Exception {
        send(checkout("cart-1", T0));
        send(checkout("cart-1", T0.plusSeconds(60)));

        advanceWatermarkTo(T0.plus(TIMEOUT));
        assertThat(harness.extractOutputValues()).isEmpty();

        advanceWatermarkTo(T0.plusSeconds(60).plus(TIMEOUT));
        assertThat(harness.extractOutputValues())
                .singleElement()
                .extracting(CartAbandoned::checkoutAt)
                .isEqualTo(T0.plusSeconds(60));
    }

    @Test
    void rejectsNonPositiveTimeout() {
        assertThatThrownBy(() -> new CartAbandonmentDetector(Duration.ZERO))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private void send(CartEvent event) throws Exception {
        harness.processElement(event, event.eventTime().toEpochMilli());
    }

    private void advanceWatermarkTo(Instant time) throws Exception {
        harness.processWatermark(time.toEpochMilli());
    }

    private static CartEvent checkout(String cartId, Instant at) {
        return CartEvent.checkoutStarted(cartId, "user-1", List.of("sku-1"), 25.0, "USD", at);
    }

    private static CartEvent purchase(String cartId, Instant at) {
        return CartEvent.purchase(cartId, "user-1", 25.0, "USD", at);
    }
}
