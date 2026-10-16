from kafka import create_topics, register_schemas
from elastic import bootstrap_elasticsearch


if __name__ == "__main__":
    create_topics()
    register_schemas()
    bootstrap_elasticsearch()
    print("\n✅ Bootstrap complete — READY FOR INSIGHTS 🚀")
