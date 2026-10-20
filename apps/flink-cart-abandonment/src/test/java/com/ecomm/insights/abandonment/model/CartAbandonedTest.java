package com.ecomm.insights.abandonment.model;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;

class CartAbandonedTest {

    private static final Instant CHECKOUT_AT = Instant.parse("2026-10-20T03:00:00Z");

    @Test
    void copiesTheCheckoutAndAddsTheTimeout() {
        CartEvent checkout =
                CartEvent.checkoutStarted(
                        "cart-1", "user-7", List.of("sku-1", "sku-2"), 42.5, "USD", CHECKOUT_AT);

        CartAbandoned abandoned = CartAbandoned.fromCheckout(checkout, Duration.ofMinutes(2));

        assertThat(abandoned.cartId()).isEqualTo("cart-1");
        assertThat(abandoned.userId()).isEqualTo("user-7");
        assertThat(abandoned.productIds()).containsExactly("sku-1", "sku-2");
        assertThat(abandoned.itemCount()).isEqualTo(2);
        assertThat(abandoned.cartValue()).isEqualTo(42.5);
        assertThat(abandoned.checkoutAt()).isEqualTo(CHECKOUT_AT);
        assertThat(abandoned.timeoutSeconds()).isEqualTo(120);
        assertThat(abandoned.abandonedAt()).isEqualTo(CHECKOUT_AT.plusSeconds(120));
    }

    @Test
    void eventIdIsDeterministicPerCart() {
        assertThat(CartAbandoned.eventIdFor("cart-1"))
                .isEqualTo(CartAbandoned.eventIdFor("cart-1"))
                .isNotEqualTo(CartAbandoned.eventIdFor("cart-2"));
    }

    @Test
    void onlyCheckoutsCanBeAbandoned() {
        CartEvent purchase = CartEvent.purchase("cart-1", "user-7", 10, "USD", CHECKOUT_AT);

        assertThatThrownBy(() -> CartAbandoned.fromCheckout(purchase, Duration.ofMinutes(2)))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
