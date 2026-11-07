"""Provide SQLite persistence for job applications."""

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from collections.abc import Iterator

from jobtrack_mcp.models import Application, ApplicationStatus

class ApplicationNotFoundError(LookupError):
    """Raise when a requested application does not exist."""

class ApplicationRepository:
    """Manage job application records in a SQLite database."""

    def __init__(self, db_path: str | Path) -> None:
        """Intialize the repository eith a database file path.
        
        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        """Create a new SQLite connection with named-column access."""

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        return conn

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Provide a transactional conncetion and ensure it is closed."""
        conn = self._connect()

        try:
            with conn:
                yield conn

        finally:
            conn.close()

    @staticmethod
    def _row_to_application(row: sqlite3.Row) -> Application:
        """Convert a SQLite row into an Application model."""

        return Application.model_validate(dict(row))

    def init_schema(self) -> None:
        """Create the Application table if it does not exist."""

        schema = """
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            company TEXT NOT NULL
                CHECK (length(trim(company)) > 0),

            role TEXT NOT NULL
                CHECK (length(trim(role)) > 0),

            status TEXT NOT NULL DEFAULT 'wishlist'
                CHECK (
                    status IN (
                        'wishlist',
                        'applied',
                        'interviewing',
                        'offer',
                        'rejected',
                        'withdrawn'
                    )
                ),

            job_url TEXT,
            notes TEXT,
            applied_on TEXT,

            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL   
        );
        """

        with self._connection() as conn:
            conn.execute(schema)
    
    
    def add(
            self,
            company: str,
            role: str,
            status: ApplicationStatus = ApplicationStatus.WISHLIST,
            job_url: str | None = None,
            notes: str | None = None,
            applied_on: date | None = None,
    ) -> Application:
        """Create and persist a new job application.
        
        Args:
            company: Name of the hiring company.
            role: Job position or title.
            status: Initial application status.
            job_url: Original job posting URL, if available.
            notes: Additional application notes.
            applied_on: Date the application was submitted.

        Returns:
            The newly created Application object.

        Raises:
            ValueError: If company or role is empty.
        """

        company = company.strip()
        role = role.strip()

        if not company or not role:
            raise ValueError("Company and role cannot be empty.")

        status = ApplicationStatus(status)

        now = datetime.now(timezone.utc).isoformat()

        applied_on_value = (
            applied_on.isoformat() if applied_on is not None else None
        )

        with self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO applications (
                company,
                role,
                status, 
                job_url,
                notes,
                applied_on,
                created_at,
                updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company,
                    role,
                    status.value,
                    job_url, 
                    notes,
                    applied_on_value,
                    now, 
                    now,
                ),
            )

            row = conn.execute(
                "SELECT * FROM applications WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()

            if row is None:
                raise RuntimeError("Failed to create the application.")

            return self._row_to_application(row)

    def get(self, app_id: int) -> Application | None:
        """Retrieve a job applicaiton by its ID.
        
        Args:
            app_id: Unique application identifier.

        Returns:
            The matching Application, or None if it does not exist.
        """

        with self._connection() as conn:
            row = conn.execute(
                            "SELECT * FROM applications WHERE id = ?",
                            (app_id,),
                        ).fetchone()

            if row is None:
                return None

            return self._row_to_application(row)


    def list_applications(self, status: ApplicationStatus | None = None) -> list[Application]:
        """Retrieve all applications, optionally filtered by status.

        Args:
            status: Status used to filter applications.

        Returns:
            Applications ordered by creation time, newest first.
        """

        with self._connection() as conn:
            if status is None:
                rows = conn.execute(
                    """
                    SELECT * FROM applications
                    ORDER BY created_at DESC, id DESC
                    """
                ).fetchall()

            else:
                status = ApplicationStatus(status)

                rows = conn.execute(
                    """
                    SELECT * FROM applications
                    WHERE status = ?
                    ORDER BY created_at DESC, id DESC
                    """,
                    (status.value,),
                ).fetchall()

            return [self._row_to_application(row) for row in rows]


    def update_status(
            self,
            app_id: int,
            status: ApplicationStatus,
    ) -> Application:
        """Update the status of an existing job application.

        Args:
            app_id: Unique application identifier.
            status: New application status.

        Returns:
            The updated Application object.

        Raises:
            ApplicationNotFoundError: If the application does not exist.
        """
        status = ApplicationStatus(status)
        updated_at = datetime.now(timezone.utc).isoformat()

        with self._connection() as conn:
            cursor = conn.execute(
                """
                UPDATE applications
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status.value, updated_at, app_id),
            )

            if cursor.rowcount == 0:
                raise ApplicationNotFoundError(
                    f"Application with ID {app_id} was not found."
                )

            row = conn.execute(
                "SELECT * FROM applications WHERE id = ?",
                (app_id,),
            ).fetchone()

            if row is None:
                raise RuntimeError("Failed to retrieve the updarted application.")

            return self._row_to_application(row)