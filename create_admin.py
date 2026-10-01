"""
Create (or promote) an administrator account WITHOUT any demo data. Safe for production.

    python create_admin.py admin@yourdomain.ng "Full Name" +2348012345678

The password is read from the MAUMART_ADMIN_PASSWORD environment variable, or prompted for
interactively, so it never appears in shell history or the process list.
"""
import getpass
import os
import sys

from database import SessionLocal, init_db
import models
import schemas
from auth_utils import hash_password


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    email, name, phone = sys.argv[1:4]
    password = os.environ.get("MAUMART_ADMIN_PASSWORD") or getpass.getpass("Admin password: ")
    try:
        schemas._check_password(password)
    except ValueError as e:
        sys.exit(str(e))
    if len(password) < 12:
        sys.exit("Use at least 12 characters for an administrator password.")

    init_db()
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if user:
            user.role, user.status = "admin", "active"
            user.password_hash = hash_password(password)
            print(f"Updated existing account {email} -> admin")
        else:
            db.add(models.User(
                name=name, email=email, phone=phone, password_hash=hash_password(password),
                role="admin", status="active", email_verified=True, agreed_to_terms=True,
            ))
            print(f"Created admin {email}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
