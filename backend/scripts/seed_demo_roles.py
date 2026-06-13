"""
Seed three demo accounts with different roles.

Run this after database is configured:
    python -m scripts.seed_demo_roles
"""
import asyncio
import uuid

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.user import UserProfile, Role, UserRole

# Demo account UUIDs from Supabase
DEMO_ACCOUNTS = [
    {
        "id": uuid.UUID("e906678c-21c2-44c1-bcf5-a172c69d17f7"),
        "email": "demo.student@campusos.app",
        "name": "Demo Student",
        "role": "STUDENT",
    },
    {
        "id": uuid.UUID("cb253015-0448-49ec-aee6-70faef5e9113"),
        "email": "demo.admin@campusos.app",
        "name": "Demo Admin",
        "role": "ACADEMIC_ADMIN",
    },
    {
        "id": uuid.UUID("f0103df7-cd9b-4988-bb6f-e92458e90502"),
        "email": "demo.professor@campusos.app",
        "name": "Demo Professor",
        "role": "FACULTY",
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        for account in DEMO_ACCOUNTS:
            # Check if profile exists
            result = await db.execute(
                select(UserProfile).where(UserProfile.id == account["id"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"✓ {account['name']} profile already exists")
                continue

            # Create profile
            profile = UserProfile(
                id=account["id"],
                email=account["email"],
                full_name=account["name"],
                role=account["role"],
                is_demo=True,
            )
            db.add(profile)
            await db.flush()
            print(f"✓ Created {account['name']} profile")

        # Commit all profiles
        await db.commit()
        print("\n✅ All demo accounts seeded successfully!")
        print("\nDemo Credentials:")
        print("=" * 50)
        for account in DEMO_ACCOUNTS:
            print(
                f"\n{account['name']} ({account['role']}):"
            )
            print(f"  Email:    {account['email']}")
            print(f"  Password: demo1234")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(seed())
