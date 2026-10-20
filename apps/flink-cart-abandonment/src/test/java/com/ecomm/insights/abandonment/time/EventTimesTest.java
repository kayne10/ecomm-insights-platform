package com.ecomm.insights.abandonment.time;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Instant;
import org.junit.jupiter.api.Test;

class EventTimesTest {

    @Test
    void parsesTimestampWithOffset() {
        assertThat(EventTimes.parse("2026-10-20T03:09:17.311+00:00"))
                .isEqualTo(Instant.parse("2026-10-20T03:09:17.311Z"));
        assertThat(EventTimes.parse("2026-10-20T05:09:17+02:00"))
                .isEqualTo(Instant.parse("2026-10-20T03:09:17Z"));
    }

    @Test
    void treatsTimestampWithoutOffsetAsUtc() {
        assertThat(EventTimes.parse("2026-10-16T05:08:14.460596"))
                .isEqualTo(Instant.parse("2026-10-16T05:08:14.460596Z"));
    }

    @Test
    void rejectsGarbage() {
        assertThatThrownBy(() -> EventTimes.parse("yesterday"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("yesterday");
    }

    @Test
    void formatsLikeThePythonProducer() {
        assertThat(EventTimes.format(Instant.parse("2026-10-20T03:09:17.311987Z")))
                .isEqualTo("2026-10-20T03:09:17.311Z");
    }
}
