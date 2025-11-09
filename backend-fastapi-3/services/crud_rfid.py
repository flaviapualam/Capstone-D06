# services/crud_rfid.py
import asyncpg
from uuid import UUID
from typing import List, Tuple

async def upsert_rfid_tags(db: asyncpg.Connection, rfid_batch: List[Tuple]):
    query = """
    INSERT INTO rfid_tag (rfid_id, created_at)
    VALUES ($1, NOW())
    ON CONFLICT (rfid_id) DO NOTHING;
    """
    try:
        await db.executemany(query, rfid_batch)
        print(f"(RFID REGISTER) Processed {len(rfid_batch)} RFID tags.")
    except Exception as e:
        print(f"Error during RFID tag UPSERT: {e}")


async def assign_rfid_to_cow(
    db: asyncpg.Connection, 
    rfid_id: str, 
    cow_id: UUID
) -> asyncpg.Record | None:
    try:
        async with db.transaction():
            await db.execute(
                """
                UPDATE rfid_ownership
                SET time_end = NOW()
                WHERE rfid_id = $1 AND time_end IS NULL;
                """,
                rfid_id
            )
            new_assignment = await db.fetchrow(
                """
                INSERT INTO rfid_ownership (rfid_id, time_start, cow_id, time_end)
                VALUES ($1, NOW(), $2, NULL)
                RETURNING *;
                """,
                rfid_id,
                cow_id
            )
            return dict(new_assignment)
    except asyncpg.exceptions.ForeignKeyViolationError as e:
        # Ini akan error jika rfid_id atau cow_id tidak ada
        print(f"Error: Foreign key violation. {e}")
        return None
    except Exception as e:
        print(f"Error during RFID assignment transaction: {e}")
        return None