"""Expose job application management through MCP tools."""

from datetime import date
from pathlib import Path
from typing import Annotated


from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from jobtrack_mcp.db import (
    ApplicationNotFoundError,
    ApplicationRepository,
)

from jobtrack_mcp.models import Application, ApplicationStatus

def create_server(repo: ApplicationRepository) -> MCPServer:
    """Create an MCP server backed by the supplied repository."""

    mcp = MCPServer("jobtrack")

    @mcp.tool(
            annotations=ToolAnnotations(
                read_only_hint=False,
                destructive_hint=False,
                idempotent_hint=False,
                open_world_hint=False,
            )
    )
    def add_application(
        company: Annotated[
            str,
            Field(
                min_length=1,
                max_length=200,
                description="Hiring company name."
            ),
        ],
        role: Annotated[ 
            str,
            Field(
                min_length=1,
                max_length=200,
                description="Job position or title.",
            ),
        ],
        status: Annotated[ 
            ApplicationStatus,
            Field(
                description="Initial application status.",
            ),
        ] = ApplicationStatus.WISHLIST,
        job_url: Annotated[ 
            str | None,
            Field(
                description="URL of job posting, if available."
            ),
        ] = None,
        notes: Annotated[ 
                    str | None,
                    Field(
                        description="Additional notes about the application."),
                ] = None,
        applied_on: Annotated[ 
            date | None,
            Field(
                description="Date of the application submission.",
            ),
        ] = None,
    ) -> Application:
        """ Create a job application record.

        Use this tool when the user wants to track a new job application.
        Before creating a record, call list_applications first to check for duplicates. 
        This operation creates a new record every time it is called, even if the company and role match an existing record.
        """
        try:
            return repo.add(
                company=company,
                role=role,
                status=status,
                job_url=job_url,
                notes=notes,
                applied_on=applied_on,
            )

        except ValueError as exc:
            raise ToolError(
                f"Could not add the application: {exc}. "
                "Check the company name and role, then try again."
            ) from exc


    @mcp.tool(
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        )
    )
    def list_applications(
        status: Annotated[
            ApplicationStatus | None,
            Field(
                description="Optional status filter."
            ),
        ] = None,
        limit: Annotated[
            int,
            Field(
                ge=1,
                le=100,
                description="Maximum number of applications to return.",
            ),
        ] = 20,
    ) -> list[Application]:
        """List tracked job applications.

        Use this tool when the user wants to see their applications.
        Optionally filter by status. Results are ordered newest first.
        The default result limit is 20 and the maximum is 100.
        """
        return repo.list_all(status=status, limit=limit)


    @mcp.tool(
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        )
    )
    def get_application(
        application_id: Annotated[
            int,
            Field(
                ge=1,
                description="Unique ID of the application to retrieve.",
            ),
        ],
    ) -> Application:
        """Retrieve one job application by its ID.

        Use this tool when the user asks for details about a specific
        application. If the application is not found, use
        list_applications to discover existing application IDs.
        """
        application = repo.get(application_id)

        if application is None:
            raise ToolError(
                f"Application {application_id} was not found. "
                "Use list_applications to find valid application IDs."
            )

        return application


    @mcp.tool(
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        )
    )
    def update_application_status(
        application_id: Annotated[
            int,
            Field(
                ge=1,
                description="Unique ID of the application to update.",
            ),
        ],
        status: Annotated[
            ApplicationStatus,
            Field(
                description="New status for the application."
                ),
        ],
    ) -> Application:
        """Change the status of an existing job application.

        Use this tool when the user reports a change in the progress of
        an application, such as moving from applied to interviewing or
        receiving an offer. This changes only the status; other
        application details remain unchanged.
        """
        try:
            return repo.update_status(application_id, status)
        
        except ApplicationNotFoundError as exc:
            raise ToolError(
                f"Application {application_id} was not found. "
                "Use list_applications to find valid application IDs."
            ) from exc

    return mcp


def main() -> None:
    """Intialize persistent storage and start the MCP Server"""
    db_dir = Path.home() / ".jobtrack-mcp"
    db_dir.mkdir(parents=True, exist_ok=True)

    db_path = db_dir / "jobtrack.db"

    repo = ApplicationRepository(db_path)
    repo.init_schema()

    create_server(repo).run()


if __name__ == "__main__":
    main()