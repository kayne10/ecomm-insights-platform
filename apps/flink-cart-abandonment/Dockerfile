# syntax=docker/dockerfile:1

# --- Build: compile, test (mvn verify also checks formatting) and shade the job jar ------------
FROM maven:3.9.11-eclipse-temurin-17 AS build
WORKDIR /build

# Resolve dependencies in their own layer so source-only changes rebuild quickly.
COPY pom.xml .
RUN --mount=type=cache,target=/root/.m2 mvn -B -ntp -q dependency:go-offline

COPY src ./src
RUN --mount=type=cache,target=/root/.m2 mvn -B -ntp verify

# --- Runtime: Flink in application mode runs the job jar from /opt/flink/usrlib --------------
# Keep this tag in sync with flink.version in pom.xml.
FROM flink:2.2.1-java17
COPY --from=build --chown=flink:flink /build/target/flink-cart-abandonment.jar /opt/flink/usrlib/
