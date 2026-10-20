package com.ecomm.insights.abandonment.time;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.temporal.ChronoUnit;
import java.util.Objects;

/**
 * Parses and formats the ISO-8601 timestamps carried in event payloads.
 *
 * <p>Producers write either an offset timestamp ({@code 2026-10-20T03:09:17.311+00:00}) or, for
 * older events, a local timestamp without offset ({@code 2026-10-16T05:08:14.460596}) that is
 * implicitly UTC. Both are accepted.
 */
public final class EventTimes {

    private EventTimes() {}

    /**
     * Parses an event timestamp.
     *
     * @throws IllegalArgumentException if the value is not an ISO-8601 date-time
     */
    public static Instant parse(CharSequence value) {
        Objects.requireNonNull(value, "timestamp");
        String text = value.toString();
        try {
            return OffsetDateTime.parse(text).toInstant();
        } catch (DateTimeParseException withoutOffset) {
            try {
                return LocalDateTime.parse(text).toInstant(ZoneOffset.UTC);
            } catch (DateTimeParseException e) {
                throw new IllegalArgumentException("Not an ISO-8601 timestamp: " + text, e);
            }
        }
    }

    /** Formats an instant as an ISO-8601 UTC timestamp with at most millisecond precision. */
    public static String format(Instant instant) {
        return DateTimeFormatter.ISO_OFFSET_DATE_TIME.format(
                instant.truncatedTo(ChronoUnit.MILLIS).atOffset(ZoneOffset.UTC));
    }
}
