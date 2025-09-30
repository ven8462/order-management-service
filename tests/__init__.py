import os

_defaults = {
    "POSTGRES_USER": "test",
    "POSTGRES_PASSWORD": "test",
    "POSTGRES_DB": "test_db",
    "DATABASE_URL": "sqlite:///:memory:",
    "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
    "INVENTORY_SERVICE_URL": "http://fake-inventory",
    "SECRET_KEY": "testsecret",
    "PAYMENT_SERVICE_BASE_URL": "http://fake-payment",
}

for k, v in _defaults.items():
    os.environ.setdefault(k, v)
