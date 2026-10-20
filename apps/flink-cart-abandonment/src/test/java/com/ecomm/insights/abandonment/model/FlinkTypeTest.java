package com.ecomm.insights.abandonment.model;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.time.Instant;
import java.util.List;
import org.apache.flink.api.common.serialization.SerializerConfigImpl;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.api.common.typeutils.TypeSerializer;
import org.apache.flink.api.java.typeutils.GenericTypeInfo;
import org.apache.flink.core.memory.DataInputDeserializer;
import org.apache.flink.core.memory.DataOutputSerializer;
import org.junit.jupiter.api.Test;

/**
 * Guards against model changes that silently fall back to slow, fragile Kryo serialization (e.g.
 * adding a field type Flink cannot analyse), which would also break state compatibility.
 */
class FlinkTypeTest {

    @Test
    void cartEventIsSerializedWithoutKryo() throws IOException {
        CartEvent event =
                CartEvent.checkoutStarted(
                        "cart-1", "user-1", List.of("sku-1"), 9.99, "USD", Instant.EPOCH);

        assertThat(roundTrip(event, CartEvent.class)).isEqualTo(event);
    }

    @Test
    void cartAbandonedIsSerializedWithoutKryo() throws IOException {
        CartAbandoned event =
                new CartAbandoned(
                        "id",
                        "user-1",
                        "cart-1",
                        List.of("sku-1", "sku-2"),
                        9.99,
                        "USD",
                        Instant.EPOCH,
                        120,
                        Instant.EPOCH.plusSeconds(120));

        assertThat(roundTrip(event, CartAbandoned.class)).isEqualTo(event);
    }

    private static <T> T roundTrip(T value, Class<T> type) throws IOException {
        TypeInformation<T> info = TypeInformation.of(type);
        assertThat(info).isNotInstanceOf(GenericTypeInfo.class);

        SerializerConfigImpl config = new SerializerConfigImpl();
        config.setGenericTypes(false); // fail instead of falling back to Kryo anywhere inside
        TypeSerializer<T> serializer = info.createSerializer(config);

        DataOutputSerializer out = new DataOutputSerializer(128);
        serializer.serialize(value, out);
        return serializer.deserialize(new DataInputDeserializer(out.getCopyOfBuffer()));
    }
}
