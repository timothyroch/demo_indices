import os
import sys

from dotenv import load_dotenv

from app.auth import get_password_hash
from app.database import SessionLocal, User, init_db

load_dotenv()


def main() -> None:
    username = (sys.argv[1] if len(sys.argv) > 1 else None) or os.environ.get(
        "ADMIN_USERNAME", "admin"
    )
    password = (sys.argv[2] if len(sys.argv) > 2 else None) or os.environ.get(
        "ADMIN_PASSWORD", "admin"
    )

    if not username or not password:
        print(
            "Usage: poetry run python scripts/create_admin.py [USERNAME] [PASSWORD]",
            file=sys.stderr,
        )
        print("   or set ADMIN_USERNAME and ADMIN_PASSWORD in .env", file=sys.stderr)
        sys.exit(1)

    init_db()
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            existing.hashed_password = get_password_hash(password)
            existing.is_admin = True
            db.commit()
            print(f"Updated admin user '{username}' (password and is_admin=True).")
        else:
            user = User(
                username=username,
                hashed_password=get_password_hash(password),
                is_admin=True,
                partner_city=None,
            )
            db.add(user)
            db.commit()
            print(f"Created admin user '{username}'.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
