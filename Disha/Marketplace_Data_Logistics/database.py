import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional


DEFAULT_DB_PATH = Path("agriweave.db")


class Database:
    """
    Lightweight SQLite database layer for AGRIWEAVE.

    The database stores marketplace state persistently so that
    farmer, buyer, supply, demand and order information survives
    application restarts.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS farmers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    location TEXT NOT NULL,
                    phone TEXT,
                    reliability_score REAL NOT NULL DEFAULT 0.0
                );

                CREATE TABLE IF NOT EXISTS buyers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    location TEXT NOT NULL,
                    phone TEXT,
                    reliability_score REAL NOT NULL DEFAULT 0.0
                );

                CREATE TABLE IF NOT EXISTS supplies (
                    id TEXT PRIMARY KEY,
                    farmer_id TEXT NOT NULL,
                    crop TEXT NOT NULL,
                    quantity_kg REAL NOT NULL,
                    location TEXT NOT NULL,
                    available_from TEXT NOT NULL,
                    available_until TEXT NOT NULL,
                    quality TEXT NOT NULL,
                    expected_price_per_kg REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'available',
                    FOREIGN KEY (farmer_id) REFERENCES farmers(id)
                );

                CREATE TABLE IF NOT EXISTS demands (
                    id TEXT PRIMARY KEY,
                    buyer_id TEXT NOT NULL,
                    crop TEXT NOT NULL,
                    quantity_kg REAL NOT NULL,
                    destination TEXT NOT NULL,
                    deadline TEXT NOT NULL,
                    max_price_per_kg REAL NOT NULL,
                    quality_required TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    FOREIGN KEY (buyer_id) REFERENCES buyers(id)
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    demand_id TEXT NOT NULL,
                    quantity_kg REAL NOT NULL,
                    selling_price_per_kg REAL NOT NULL,
                    transport_cost REAL NOT NULL DEFAULT 0.0,
                    collection_cost REAL NOT NULL DEFAULT 0.0,
                    packaging_cost REAL NOT NULL DEFAULT 0.0,
                    spoilage_cost REAL NOT NULL DEFAULT 0.0,
                    platform_fee REAL NOT NULL DEFAULT 0.0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    FOREIGN KEY (demand_id) REFERENCES demands(id)
                );

                CREATE TABLE IF NOT EXISTS order_supplies (
                    order_id TEXT NOT NULL,
                    supply_id TEXT NOT NULL,
                    PRIMARY KEY (order_id, supply_id),
                    FOREIGN KEY (order_id) REFERENCES orders(id),
                    FOREIGN KEY (supply_id) REFERENCES supplies(id)
                );

                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    address TEXT,
                    UNIQUE(entity_type, entity_id)
                );
                """
            )

    def execute(
        self,
        query: str,
        parameters: Iterable[Any] = (),
    ) -> None:
        with self._connect() as connection:
            connection.execute(query, tuple(parameters))

    def fetch_one(
        self,
        query: str,
        parameters: Iterable[Any] = (),
    ) -> Optional[sqlite3.Row]:
        with self._connect() as connection:
            cursor = connection.execute(query, tuple(parameters))
            return cursor.fetchone()

    def fetch_all(
        self,
        query: str,
        parameters: Iterable[Any] = (),
    ) -> list[sqlite3.Row]:
        with self._connect() as connection:
            cursor = connection.execute(query, tuple(parameters))
            return cursor.fetchall()