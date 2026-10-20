from common.registry import EVENT_REGISTRY, GENERATED_EVENTS

DOMAINS = {"browsing", "cart", "orders", "feedback"}


def test_registry_keys_are_event_names():
    for name, cls in EVENT_REGISTRY.items():
        assert cls.name == name


def test_topics_are_unique_and_kebab_case():
    topics = [cls.topic for cls in EVENT_REGISTRY.values()]
    assert len(topics) == len(set(topics))
    assert all(t == t.lower() and "_" not in t and t.endswith("-events") for t in topics)


def test_every_event_belongs_to_a_known_domain():
    assert {cls.domain for cls in EVENT_REGISTRY.values()} <= DOMAINS


def test_generated_events_exclude_derived_ones():
    assert "cart_abandoned" in EVENT_REGISTRY
    assert "cart_abandoned" not in GENERATED_EVENTS
    assert all(cls.produced_by is None for cls in GENERATED_EVENTS.values())


def test_derived_events_have_no_weight_and_generated_events_do():
    for cls in EVENT_REGISTRY.values():
        if cls.produced_by:
            assert cls.weight == 0
        else:
            assert cls.weight > 0


def test_every_event_has_identity_and_time_fields():
    for cls in EVENT_REGISTRY.values():
        names = {f["name"] for f in cls.fields}
        assert {"event_id", "event_type", "user_id"} <= names, cls.name
        assert names & {"timestamp", "viewed_at", "searched_at"}, cls.name
