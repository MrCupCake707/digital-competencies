from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
from pathlib import Path

from app.core.models import EmployeeProfile


class ProfileRepository:
    def __init__(self, db_path: Path | str = "digital_trajectory.db") -> None:
        self.db_path = Path(db_path)
        self._init_schema()
        self._ensure_default_users()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    position TEXT NOT NULL,
                    department TEXT NOT NULL,
                    levels_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    login TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    position TEXT NOT NULL DEFAULT '',
                    department TEXT NOT NULL DEFAULT '',
                    role TEXT NOT NULL DEFAULT 'user',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_profiles_full_name ON profiles(full_name)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_users_login ON users(login)")
            self._migrate_users_table(connection)

    def _migrate_users_table(self, connection: sqlite3.Connection) -> None:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(users)").fetchall()]
        if "role" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
            connection.execute("UPDATE users SET role = 'admin' WHERE lower(login) = 'admin'")

    def _ensure_default_users(self) -> None:
        self._upsert_default_user("admin", "admin", "Администратор", "Администратор", "Администрирование", "admin")
        self._upsert_default_user("user", "user", "Пользователь", "Сотрудник", "Пользовательский режим", "user")

    def _upsert_default_user(self, login: str, password: str, full_name: str, position: str, department: str, role: str) -> None:
        with self._connect() as connection:
            existing = connection.execute("SELECT id FROM users WHERE lower(login) = lower(?)", (login,)).fetchone()
            if existing:
                connection.execute(
                    "UPDATE users SET full_name = ?, position = ?, department = ?, role = ? WHERE lower(login) = lower(?)",
                    (full_name, position, department, role, login),
                )
                return

            salt = secrets.token_hex(16)
            connection.execute(
                """
                INSERT INTO users(login, password_hash, salt, full_name, position, department, role)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (login, self._hash_password(password, salt), salt, full_name, position, department, role),
            )

    def save(self, profile: EmployeeProfile) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO profiles(full_name, position, department, levels_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    profile.full_name,
                    profile.position,
                    profile.department,
                    json.dumps(profile.levels, ensure_ascii=False),
                ),
            )

    def find_by_full_name(self, full_name: str) -> EmployeeProfile | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT full_name, position, department, levels_json
                FROM profiles
                WHERE lower(full_name) = lower(?)
                ORDER BY id DESC
                LIMIT 1
                """,
                (full_name.strip(),),
            ).fetchone()

        if row is None:
            return None

        name, position, department, levels = row
        return EmployeeProfile(name, position, department, json.loads(levels))

    def list_all(self) -> list[EmployeeProfile]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT full_name, position, department, levels_json FROM profiles ORDER BY id DESC"
            ).fetchall()

        return [EmployeeProfile(name, position, department, json.loads(levels)) for name, position, department, levels in rows]

    def authenticate_user(self, login: str, password: str) -> EmployeeProfile | None:
        result = self.authenticate_user_with_role(login, password)
        return result[0] if result else None

    def authenticate_user_with_role(self, login: str, password: str) -> tuple[EmployeeProfile, str] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT password_hash, salt, full_name, position, department, role
                FROM users
                WHERE lower(login) = lower(?)
                LIMIT 1
                """,
                (login.strip().lower(),),
            ).fetchone()

        if row is None:
            return None

        stored_hash, salt, full_name, position, department, role = row
        if not hmac.compare_digest(stored_hash, self._hash_password(password, salt)):
            return None

        profile = self.find_by_full_name(full_name) or EmployeeProfile(full_name, position, department, {})
        return profile, role

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            120_000,
        ).hex()
