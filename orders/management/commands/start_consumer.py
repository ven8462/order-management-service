from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Start Kafka consumer for Order Service"

    def handle(self, *args, **options):
        # import inside method to avoid top-level execution issues
        from kafka_utils.consumer import start_consumer

        self.stdout.write(self.style.SUCCESS("Starting Order Service Kafka Consumer..."))
        start_consumer()