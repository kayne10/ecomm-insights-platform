package com.ecomm.insights.abandonment;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import org.apache.avro.Schema;

/** Avro schemas exported from the Python event classes (see src/test/resources/schemas). */
public final class TestSchemas {

    private TestSchemas() {}

    public static Schema load(String name) {
        try (InputStream in = TestSchemas.class.getResourceAsStream("/schemas/" + name + ".avsc")) {
            if (in == null) {
                throw new IllegalArgumentException("No test schema " + name);
            }
            return new Schema.Parser().parse(in);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
