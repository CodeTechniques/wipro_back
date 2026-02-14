from django.core.management.base import BaseCommand
from investments.services import fetch_and_store_gold_price

class Command(BaseCommand):
    help = "Fetch gold price from GoldAPI and store in DB"

    def handle(self, *args, **kwargs):
        fetch_and_store_gold_price()
        self.stdout.write(self.style.SUCCESS("Gold price updated successfully"))
