"""
Trigger the wishlist monitoring sweep (FR-21..FR-24).

Monitoring has to be *run* — there is no price_alerts table to poll (schema
rule 10), so something has to walk the wishlist. Run this on a schedule:

    python manage.py check_monitoring            # human-readable summary
    python manage.py check_monitoring --quiet    # cron-friendly, exit code only

Safe to run repeatedly: notifications are de-duplicated per event, so a
second sweep in the same state creates nothing new.
"""

from django.core.management.base import BaseCommand

from notifications.monitoring import run_monitoring


class Command(BaseCommand):
    help = "Evaluate every wishlist item and raise price-drop / restock notifications."

    def add_arguments(self, parser):
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Print nothing; use the exit code to signal that work was done.",
        )

    def handle(self, *args, **options):
        checked, created = run_monitoring()

        if options["quiet"]:
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Checked {checked} wishlist item(s); "
                f"created {len(created)} notification(s)."
            )
        )
        for n in created:
            self.stdout.write(f"  - [{n.get_notification_type_display()}] {n.title}")