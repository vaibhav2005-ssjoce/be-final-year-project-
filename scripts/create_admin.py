import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import SessionLocal
from backend.app.core.security import get_password_hash
from backend.app.models.user import User

def create_admin(email: str, password: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.role = "admin"
            user.hashed_password = get_password_hash(password)
            db.commit()
            print(f"User '{email}' updated to admin successfully.")
        else:
            admin_user = User(
                email=email,
                hashed_password=get_password_hash(password),
                role="admin"
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"Admin user '{email}' created successfully with ID {admin_user.id}.")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or update an admin user for FraudShield AI.")
    parser.add_argument("--email", default="admin@fraudshield.ai", help="Admin email address")
    parser.add_argument("--password", default="Admin@123", help="Admin password")
    args = parser.parse_args()

    create_admin(args.email, args.password)
