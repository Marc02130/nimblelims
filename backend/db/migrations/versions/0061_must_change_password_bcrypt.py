"""P0b security: must_change_password + rehash known seed passwords to bcrypt.

Revision ID: 0061
Revises: 0060
Create Date: 2026-08-20

- ADD users.must_change_password
- Mark known persona seed usernames must_change_password=true
- Rehash legacy SHA256 hashes for well-known UAT passwords to bcrypt when matched
"""
from alembic import op
import sqlalchemy as sa

revision = "0061"
down_revision = "0060"
branch_labels = None
depends_on = None

# Well-known persona seeds (dev/demo/UAT)
SEED_USERNAMES = (
    "admin",
    "lab-manager",
    "lab-tech",
    "client",
)

# Plaintext → legacy SHA256 (from early migrations) for upgrade detection
KNOWN_SHA256 = {
    # admin123
    "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9": "admin123",
    # labmanager123
    "7dd63afe29407aa45af7fdd4388b71195b552688c2750abd42bdf3b231c13b69": "labmanager123",
    # labtech123
    "d81968c60a8a41bdafcb3c5825bf8bc4a76dccc932d673e3f9a7b71ce4538596": "labtech123",
}


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    connection = op.get_bind()

    # Persona seeds must change password on first login (Q2/Q7)
    connection.execute(
        sa.text(
            """
            UPDATE users
            SET must_change_password = true
            WHERE username IN ('admin', 'lab-manager', 'lab-tech', 'client')
            """
        ),
    )

    # Rehash known legacy SHA256 seed passwords to bcrypt
    import bcrypt

    rows = connection.execute(
        sa.text("SELECT id, username, password_hash FROM users")
    ).fetchall()
    for row in rows:
        user_id, username, password_hash = row[0], row[1], row[2]
        plain = KNOWN_SHA256.get(password_hash)
        if not plain:
            continue
        new_hash = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        connection.execute(
            sa.text(
                """
                UPDATE users
                SET password_hash = :h, must_change_password = true
                WHERE id = :id
                """
            ),
            {"h": new_hash, "id": user_id},
        )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
