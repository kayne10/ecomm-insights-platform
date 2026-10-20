package com.ecomm.insights.abandonment.model;

import java.time.Instant;
import java.util.List;
import java.util.Objects;

/**
 * The subset of {@code checkout_started} and {@code purchase} events the detector needs.
 *
 * @param type which event this is
 * @param cartId the cart the event belongs to; {@code null} for purchases not made through a cart
 * @param userId the shopper
 * @param productIds products in the cart; empty for purchases
 * @param value cart value for a checkout, order amount for a purchase
 * @param currency ISO currency code
 * @param eventTime when the event happened (event time, used for watermarks and timers)
 */
public record CartEvent(
        Type type,
        String cartId,
        String userId,
        List<String> productIds,
        double value,
        String currency,
        Instant eventTime) {

    /** The source event type. */
    public enum Type {
        CHECKOUT_STARTED,
        PURCHASE
    }

    public CartEvent {
        Objects.requireNonNull(type, "type");
        Objects.requireNonNull(userId, "userId");
        Objects.requireNonNull(currency, "currency");
        Objects.requireNonNull(eventTime, "eventTime");
        productIds = productIds == null ? List.of() : List.copyOf(productIds);
    }

    /** Creates a checkout event. */
    public static CartEvent checkoutStarted(
            String cartId,
            String userId,
            List<String> productIds,
            double cartValue,
            String currency,
            Instant eventTime) {
        Objects.requireNonNull(cartId, "cartId");
        return new CartEvent(
                Type.CHECKOUT_STARTED, cartId, userId, productIds, cartValue, currency, eventTime);
    }

    /** Creates a purchase event; {@code cartId} may be null. */
    public static CartEvent purchase(
            String cartId, String userId, double amount, String currency, Instant eventTime) {
        return new CartEvent(Type.PURCHASE, cartId, userId, List.of(), amount, currency, eventTime);
    }

    /** Whether the event can be correlated by cart. */
    public boolean hasCart() {
        return cartId != null;
    }
}
