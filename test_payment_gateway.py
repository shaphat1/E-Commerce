"""
Verifies verify_webhook_signature() against Paystack's actual documented
signing scheme (HMAC-SHA512 of the raw request body, keyed by the secret
key). This is fully testable without network access -- it's the same
computation Paystack's servers do, just reimplemented and checked here.

Run: python tests/test_payment_gateway.py
"""
import hmac
import hashlib
import sys

sys.path.insert(0, ".")
from payment_gateway import verify_webhook_signature

SECRET = "sk_test_fake_secret_for_testing_only"
BODY = b'{"event":"charge.success","data":{"reference":"abc123","amount":500000}}'

# Compute the signature the same way Paystack's own servers would.
correct_signature = hmac.new(SECRET.encode(), BODY, hashlib.sha512).hexdigest()

cases = [
    ("Correct signature is accepted", verify_webhook_signature(BODY, correct_signature, SECRET) is True),
    ("Wrong signature is rejected", verify_webhook_signature(BODY, "0" * 128, SECRET) is False),
    ("Empty signature is rejected", verify_webhook_signature(BODY, "", SECRET) is False),
    ("Tampered body is rejected (signature no longer matches)",
     verify_webhook_signature(BODY + b"tampered", correct_signature, SECRET) is False),
    ("Wrong secret key is rejected",
     verify_webhook_signature(BODY, correct_signature, "wrong_secret") is False),
]

print(f"{'Result':<6} Description")
print("-" * 60)
n_fail = 0
for desc, passed in cases:
    status = "PASS" if passed else "FAIL"
    if not passed:
        n_fail += 1
    print(f"{status:<6} {desc}")

print(f"\n{len(cases) - n_fail}/{len(cases)} passed")
sys.exit(1 if n_fail else 0)
