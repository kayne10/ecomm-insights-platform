package com.ecomm.insights.abandonment.serde;

import com.ecomm.insights.abandonment.model.CartEvent;
import com.ecomm.insights.abandonment.time.EventTimes;
import java.util.Collection;
import java.util.List;
import org.apache.avro.generic.GenericRecord;

/**
 * Maps Avro records of the input topics to {@link CartEvent}s. Field names follow the Python
 * events.
 */
public final class CartEventMappers {

    private CartEventMappers() {}

    /** Maps a {@code checkout_started} record. */
    public static CartEvent fromCheckout(GenericRecord record) {
        return CartEvent.checkoutStarted(
                requiredString(record, "cart_id"),
                requiredString(record, "user_id"),
                stringList(record, "product_ids"),
                ((Number) required(record, "cart_value")).doubleValue(),
                requiredString(record, "currency"),
                EventTimes.parse(requiredString(record, "timestamp")));
    }

    /** Maps a {@code purchase} record. {@code cart_id} is optional (added in schema v2). */
    public static CartEvent fromPurchase(GenericRecord record) {
        return CartEvent.purchase(
                optionalString(record, "cart_id"),
                requiredString(record, "user_id"),
                ((Number) required(record, "amount")).doubleValue(),
                requiredString(record, "currency"),
                EventTimes.parse(requiredString(record, "timestamp")));
    }

    private static Object required(GenericRecord record, String field) {
        Object value = record.hasField(field) ? record.get(field) : null;
        if (value == null) {
            throw new IllegalArgumentException(
                    "Missing field '" + field + "' in " + record.getSchema().getName());
        }
        return value;
    }

    // Avro strings arrive as org.apache.avro.util.Utf8, hence toString().
    private static String requiredString(GenericRecord record, String field) {
        return required(record, field).toString();
    }

    private static String optionalString(GenericRecord record, String field) {
        Object value = record.hasField(field) ? record.get(field) : null;
        return value == null ? null : value.toString();
    }

    private static List<String> stringList(GenericRecord record, String field) {
        Object value = record.hasField(field) ? record.get(field) : null;
        if (value == null) {
            return List.of();
        }
        return ((Collection<?>) value).stream().map(Object::toString).toList();
    }
}
