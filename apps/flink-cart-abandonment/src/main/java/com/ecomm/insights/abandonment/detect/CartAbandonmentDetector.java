package com.ecomm.insights.abandonment.detect;

import com.ecomm.insights.abandonment.model.CartAbandoned;
import com.ecomm.insights.abandonment.model.CartEvent;
import java.time.Duration;
import java.util.Objects;
import org.apache.flink.api.common.functions.OpenContext;
import org.apache.flink.api.common.state.StateTtlConfig;
import org.apache.flink.api.common.state.ValueState;
import org.apache.flink.api.common.state.ValueStateDescriptor;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.api.common.typeinfo.Types;
import org.apache.flink.metrics.Counter;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.util.Collector;

/**
 * Emits a {@link CartAbandoned} event when a checkout is not followed by a purchase of the same
 * cart within {@code timeout}, measured in event time.
 *
 * <p>Keyed by cart id. Per cart it keeps:
 *
 * <ul>
 *   <li>the pending checkout, plus an event-time timer at {@code checkout + timeout}; and
 *   <li>the time of a purchase, so a checkout that arrives <em>after</em> its purchase (out of
 *       order) is not reported as abandoned.
 * </ul>
 *
 * <p>A purchase deletes the pending checkout and its timer. When the timer fires and the checkout
 * is still pending, the cart is abandoned. State is always cleared afterwards, with a TTL as a
 * safety net for carts that never resolve.
 */
public final class CartAbandonmentDetector
        extends KeyedProcessFunction<String, CartEvent, CartAbandoned> {

    private static final long serialVersionUID = 1L;

    /** State that outlives this is certainly stale (e.g. a purchase whose checkout never came). */
    private static final int STATE_TTL_MULTIPLIER = 3;

    private final Duration timeout;

    private transient ValueState<CartEvent> pendingCheckout;
    private transient ValueState<Long> purchasedAt;
    private transient Counter abandoned;
    private transient Counter converted;
    private transient Counter lateCheckouts;

    public CartAbandonmentDetector(Duration timeout) {
        Objects.requireNonNull(timeout, "timeout");
        if (timeout.isNegative() || timeout.isZero()) {
            throw new IllegalArgumentException("timeout must be positive: " + timeout);
        }
        this.timeout = timeout;
    }

    @Override
    public void open(OpenContext openContext) {
        StateTtlConfig ttl =
                StateTtlConfig.newBuilder(timeout.multipliedBy(STATE_TTL_MULTIPLIER))
                        .setUpdateType(StateTtlConfig.UpdateType.OnCreateAndWrite)
                        .setStateVisibility(StateTtlConfig.StateVisibility.NeverReturnExpired)
                        .build();

        ValueStateDescriptor<CartEvent> checkoutDescriptor =
                new ValueStateDescriptor<>("pending-checkout", TypeInformation.of(CartEvent.class));
        checkoutDescriptor.enableTimeToLive(ttl);
        pendingCheckout = getRuntimeContext().getState(checkoutDescriptor);

        ValueStateDescriptor<Long> purchasedDescriptor =
                new ValueStateDescriptor<>("purchased-at", Types.LONG);
        purchasedDescriptor.enableTimeToLive(ttl);
        purchasedAt = getRuntimeContext().getState(purchasedDescriptor);

        var metrics = getRuntimeContext().getMetricGroup();
        abandoned = metrics.counter("cartsAbandoned");
        converted = metrics.counter("cartsConverted");
        lateCheckouts = metrics.counter("checkoutsAfterPurchase");
    }

    @Override
    public void processElement(CartEvent event, Context ctx, Collector<CartAbandoned> out)
            throws Exception {
        switch (event.type()) {
            case CHECKOUT_STARTED -> onCheckout(event, ctx);
            case PURCHASE -> onPurchase(event, ctx);
        }
    }

    private void onCheckout(CartEvent checkout, Context ctx) throws Exception {
        if (purchasedAt.value() != null) {
            lateCheckouts.inc(); // purchase already seen: the cart converted
            return;
        }
        CartEvent previous = pendingCheckout.value();
        if (previous != null) {
            // A repeated checkout of the same cart restarts the clock.
            ctx.timerService().deleteEventTimeTimer(deadlineOf(previous));
        }
        pendingCheckout.update(checkout);
        ctx.timerService().registerEventTimeTimer(deadlineOf(checkout));
    }

    private void onPurchase(CartEvent purchase, Context ctx) throws Exception {
        CartEvent checkout = pendingCheckout.value();
        if (checkout != null) {
            ctx.timerService().deleteEventTimeTimer(deadlineOf(checkout));
            pendingCheckout.clear();
            converted.inc();
        }
        long purchaseMillis = purchase.eventTime().toEpochMilli();
        purchasedAt.update(purchaseMillis);
        // Remember the purchase for one timeout, to absorb a checkout that arrives late.
        ctx.timerService().registerEventTimeTimer(purchaseMillis + timeout.toMillis());
    }

    @Override
    public void onTimer(long timestamp, OnTimerContext ctx, Collector<CartAbandoned> out)
            throws Exception {
        CartEvent checkout = pendingCheckout.value();
        if (checkout != null && deadlineOf(checkout) <= timestamp) {
            out.collect(CartAbandoned.fromCheckout(checkout, timeout));
            abandoned.inc();
            pendingCheckout.clear();
        }
        Long purchased = purchasedAt.value();
        if (purchased != null && purchased + timeout.toMillis() <= timestamp) {
            purchasedAt.clear();
        }
    }

    private long deadlineOf(CartEvent checkout) {
        return checkout.eventTime().plus(timeout).toEpochMilli();
    }
}
