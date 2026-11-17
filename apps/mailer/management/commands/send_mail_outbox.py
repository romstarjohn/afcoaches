import signal
import threading
import time

from django.core.management.base import BaseCommand

from apps.mailer.services import process_due, purge_finished


class Command(BaseCommand):
    help = "Mail worker: delivers queued emails (with retry) until stopped. Run it next to the web process."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="deliver what is due now, then exit (cron, tests)")
        parser.add_argument("--interval", type=float, default=5.0, help="seconds to wait between polls")
        parser.add_argument("--limit", type=int, default=50, help="max mails per poll")

    def handle(self, *args, **options):
        stop = threading.Event()
        if threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGINT, signal.SIGTERM):
                signal.signal(sig, lambda *_: stop.set())  # finish the current mail, then leave

        last_purge = 0.0
        while not stop.is_set():
            handled = process_due(limit=options["limit"])
            if handled and options["verbosity"] >= 1:
                self.stdout.write(f"Handled {handled} queued mail(s).")
            if time.monotonic() - last_purge > 3600:  # first pass and then hourly
                purge_finished()
                last_purge = time.monotonic()
            if options["once"]:
                break
            if handled < options["limit"]:  # more work waiting? go again right away
                stop.wait(options["interval"])
