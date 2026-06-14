"""Migration ADDITIVE et IDEMPOTENTE — features « monstre QM ».

Sûr à rejouer : n'utilise que ADD COLUMN IF NOT EXISTS / CREATE TABLE IF NOT EXISTS.
Ne supprime ni ne modifie aucune donnée existante. Compatible avec la démo live.

Usage : python scripts/migrate_qm.py   (charge DATABASE_URL depuis .env)
"""
import os
import sys

import psycopg2

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # noqa: BLE001
    pass

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:242261@localhost:5430/hospital_complaints",
)

STATEMENTS = [
    # --- Lot B : réponse officielle + accusé de réception ---
    "ALTER TABLE plaintes ADD COLUMN IF NOT EXISTS reponse_redigee TEXT",
    "ALTER TABLE plaintes ADD COLUMN IF NOT EXISTS reponse_envoyee BOOLEAN DEFAULT FALSE",
    "ALTER TABLE plaintes ADD COLUMN IF NOT EXISTS date_reponse_envoyee TIMESTAMP",
    "ALTER TABLE plaintes ADD COLUMN IF NOT EXISTS accuse_reception_envoye BOOLEAN DEFAULT FALSE",
    "ALTER TABLE plaintes ADD COLUMN IF NOT EXISTS date_accuse_reception TIMESTAMP",
    # --- Lot C : notes d'instruction ---
    """CREATE TABLE IF NOT EXISTS notes_plaintes (
        id SERIAL PRIMARY KEY,
        plainte_id BIGINT NOT NULL REFERENCES plaintes(id) ON DELETE CASCADE,
        auteur_id INTEGER REFERENCES utilisateurs(id),
        contenu TEXT NOT NULL,
        date_creation TIMESTAMP DEFAULT now()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_notes_plainte ON notes_plaintes(plainte_id)",
]


def main() -> int:
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    for stmt in STATEMENTS:
        cur.execute(stmt)
        print("OK:", " ".join(stmt.split())[:80])
    cur.close()
    conn.close()
    print("✅ Migration QM appliquée (additive, idempotente).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
