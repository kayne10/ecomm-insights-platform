package com.ecomm.insights.abandonment.model;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

/**
 * A checkout that was not followed by a purchase within the abandonment timeout.
 *
 * @param eventId deterministic id derived from the cart, so a replay produces the same document
 * @param userId the shopper
 * @param cartId the abandoned cart
 * @param productIds products left in the cart
 * @param cartValue value of the cart
 * @param currency ISO currency code
 * @param checkoutAt when checkout started
 * @param timeoutSeconds the abandonment timeout that elapsed, in seconds (a {@code long} rather
 *     than {@link Duration} because Flink serializes {@code Duration} with Kryo)
 * @param abandonedAt {@code checkoutAt + timeout}, the event time of this event
 */
public record CartAbandoned(
        String eventId,
        String userId,
        String cartId,
        List<String> productIds,
        double cartValue,
        String currency,
        Instant checkoutAt,
        long timeoutSeconds,
        Instant abandonedAt) {

    /** Value of the {@code event_type} field, matching the Python event name. */
    public static final String EVENT_TYPE = "cart_abandoned";

    public CartAbandoned {
        Objects.requireNonNull(eventId, "eventId");
        Objects.requireNonNull(userId, "userId");
        Objects.requireNonNull(cartId, "cartId");
        Objects.requireNonNull(currency, "currency");
        Objects.requireNonNull(checkoutAt, "checkoutAt");
        Objects.requireNonNull(abandonedAt, "abandonedAt");
        productIds = productIds == null ? List.of() : List.copyOf(productIds);
    }

    /** Builds the abandoned-cart event for a checkout whose timeout has elapsed. */
    public static CartAbandoned fromCheckout(CartEvent checkout, Duration timeout) {
        if (checkout.type() != CartEvent.Type.CHECKOUT_STARTED) {
            throw new IllegalArgumentException("Expected a checkout, got " + checkout.type());
        }
        return new CartAbandoned(
                eventIdFor(checkout.cartId()),
                checkout.userId(),
                checkout.cartId(),
                checkout.productIds(),
                checkout.value(),
                checkout.currency(),
                checkout.eventTime(),
                timeout.toSeconds(),
                checkout.eventTime().plus(timeout));
    }

    /**
     * A name-based UUID: re-emitting the same cart (e.g. after a restart with at-least-once
     * delivery) overwrites the same Elasticsearch document instead of duplicating it.
     */
    static String eventIdFor(String cartId) {
        return UUID.nameUUIDFromBytes((EVENT_TYPE + ":" + cartId).getBytes(StandardCharsets.UTF_8))
                .toString();
    }

    /** Number of products in the cart. */
    public int itemCount() {
        return productIds.size();
    }
}
