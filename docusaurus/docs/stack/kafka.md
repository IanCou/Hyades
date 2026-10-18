---
title: Kafka
sidebar_position: 46
---

# Kafka

Single-node Apache Kafka broker (KRaft mode, no ZooKeeper) with the Provectus Kafka UI
for topic and message inspection.

Config: [services/test/kafka/](https://github.com/IanCou/Hyades/tree/main/services/test/kafka) · IP/LXC/route: [network.md](../network.md)

## Gotchas

- **No auth or TLS on the broker**: all listeners are `PLAINTEXT`, so client access is
  restricted to the Compose network and host. The `kafka.example.com` route fronts
  only the UI; only `:9092` is published to the host for clients.
- `KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092`: clients reach the broker via the
  `kafka` service name on the Compose network.
- `KAFKA_AUTO_CREATE_TOPICS_ENABLE=true`: topics are created on first produce.
- The UI waits on the broker's healthcheck (`kafka-topics.sh --list`) before starting.

## References

- [Apache Kafka documentation](https://kafka.apache.org/documentation/)
- [KRaft mode](https://kafka.apache.org/documentation/#kraft)
- [Provectus Kafka UI](https://github.com/provectus/kafka-ui)
