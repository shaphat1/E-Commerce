"""
Proves SMTPNotificationBackend actually sends valid SMTP mail -- against a
LOCAL test server (aiosmtpd), since no real SMTP relay is network-reachable
from this sandbox. This is the honest substitute described in
notifications.py's module docstring: real protocol-level verification,
just not against a real inbox.

Run: python tests/test_notifications.py
"""
import asyncio
import os
import sys
import threading
import time

from aiosmtpd.controller import Controller


received_messages = []


class CapturingHandler:
    async def handle_DATA(self, server, session, envelope):
        received_messages.append({
            "mail_from": envelope.mail_from,
            "rcpt_tos": envelope.rcpt_tos,
            "content": envelope.content.decode("utf-8", errors="replace"),
        })
        return "250 Message accepted for delivery"


def main():
    handler = CapturingHandler()
    controller = Controller(handler, hostname="127.0.0.1", port=1025)
    controller.start()
    time.sleep(0.3)

    os.environ["MAUMART_NOTIFY_SYNC"] = "1"  # deterministic: deliver inline instead of via the thread pool
    os.environ["MAUMART_NOTIFY_BACKEND"] = "smtp"
    os.environ["MAUMART_SMTP_HOST"] = "127.0.0.1"
    os.environ["MAUMART_SMTP_PORT"] = "1025"
    os.environ["MAUMART_SMTP_TLS"] = "false"
    os.environ["MAUMART_SMTP_FROM"] = "no-reply@maumart.ng"

    sys.path.insert(0, ".")
    import notifications
    notifications.reset_backend_cache()

    ok = notifications.get_backend().send(
        "buyer@maumart.ng", "Your MAUMart order is confirmed", "Order abc123 has been placed."
    )

    time.sleep(0.3)
    controller.stop()

    print(f"send() returned: {ok}")
    print(f"messages received by test SMTP server: {len(received_messages)}")

    passed = ok is True and len(received_messages) == 1
    if received_messages:
        msg = received_messages[0]
        subject_present = "Your MAUMart order is confirmed" in msg["content"]
        rcpt_correct = "buyer@maumart.ng" in msg["rcpt_tos"][0]
        body_present = "Order abc123 has been placed." in msg["content"]
        print(f"subject present in raw message: {subject_present}")
        print(f"recipient correct: {rcpt_correct}")
        print(f"body present: {body_present}")
        passed = passed and subject_present and rcpt_correct and body_present

    print("\nPASS" if passed else "\nFAIL")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
