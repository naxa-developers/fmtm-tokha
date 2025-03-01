# Copyright (c) 2022, 2023 Humanitarian OpenStreetMap Team
#
# This file is part of FMTM.
#
#     FMTM is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     FMTM is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with FMTM.  If not, see <https:#www.gnu.org/licenses/>.
#

"""User roles authorisation Depends methods.

These methods use FastAPI Depends for dependency injection
and always return an AuthUser object in a standard format.
"""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException
from loguru import logger as log
from psycopg import Connection
from psycopg.rows import class_row
from pydantic import Field

from app.auth.auth_deps import login_required, mapper_login_required
from app.auth.auth_schemas import AuthUser, OrgUserDict, ProjectUserDict
from app.db.database import db_conn
from app.db.enums import HTTPStatus, ProjectRole, ProjectVisibility
from app.db.models import DbProject, DbUser
from app.organisations.organisation_deps import get_organisation
from app.projects.project_deps import get_project, get_project_by_id


async def get_uid(user_data: AuthUser | DbUser) -> int:
    """Extract user id from returned OSM user."""
    try:
        user_id = user_data.id
        return user_id

    except Exception as e:
        log.exception(
            f"Failed to get user id from auth object: {user_data}. Error: {e}",
            stack_info=True,
        )
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Auth failed. No user id present",
        ) from e


async def check_access(
    user: AuthUser,
    db: Connection,
    org_id: Optional[int] = None,
    project_id: Optional[int] = None,
    role: Optional[ProjectRole] = None,
) -> Optional[DbUser]:
    """Check if the user has access to a project or organisation.

    Access is determined based on the user's role and permissions:
    - If the user has an 'ADMIN' role, access is granted.
    - If the user has a 'READ_ONLY' role, access is denied.
    - For other roles, access is granted if the user is an organisation manager
      for the specified organisation (org_id) or has the specified role
      in the specified project (project_id).
    - If only project_id is provided, the user's organization manager status
      for the organization linked to the project is also checked.

    Args:
        user (AuthUser): AuthUser object, or user ID.
        db (Connection): The database connection.
        org_id (Optional[int]): Org ID for organisation-specific access.
        project_id (Optional[int]): Project ID for project-specific access.
        role (Optional[ProjectRole]): Role to check for project-specific access.

    Returns:
        Optional[DbUser]: The user details if access is granted,
            otherwise None.
    """
    user_id = await get_uid(user)

    sql = """
        WITH role_hierarchy AS (
            SELECT 'MAPPER' AS role, 0 AS level
            UNION ALL SELECT 'VALIDATOR', 1
            UNION ALL SELECT 'FIELD_MANAGER', 2
            UNION ALL SELECT 'ASSOCIATE_PROJECT_MANAGER', 3
            UNION ALL SELECT 'PROJECT_MANAGER', 4
        )

        SELECT *
        FROM users
        WHERE id = %(user_id)s
            AND (
                CASE
                    -- Simple check to see if ADMIN or blocked (READ_ONLY)
                    WHEN role = 'ADMIN'::public.userrole THEN true
                    WHEN role = 'READ_ONLY'::public.userrole THEN false
                    ELSE

                        -- Check to see if user is org admin
                        EXISTS (
                            SELECT 1
                            FROM organisation_managers
                            WHERE organisation_managers.user_id = %(user_id)s
                            AND organisation_managers.organisation_id = %(org_id)s
                        )

                        -- Check to see if user has equal or greater than project role
                        OR EXISTS (
                            SELECT 1
                            FROM user_roles
                            JOIN role_hierarchy AS user_role_h
                                ON user_roles.role::public.projectrole
                                    = user_role_h.role::public.projectrole
                            JOIN role_hierarchy AS required_role_h
                                ON %(role)s::public.projectrole
                                    = required_role_h.role::public.projectrole
                            WHERE user_roles.user_id = %(user_id)s
                            AND user_roles.project_id = %(project_id)s
                            AND user_role_h.level >= required_role_h.level
                        )

                        -- Extract organisation id from project,
                        -- then check to see if user is org admin
                        OR (
                            %(org_id)s IS NULL
                            AND EXISTS (
                                SELECT 1
                                FROM organisation_managers
                                JOIN projects
                                    ON projects.organisation_id =
                                        organisation_managers.organisation_id
                                WHERE organisation_managers.user_id = %(user_id)s
                                AND projects.id = %(project_id)s
                            )
                        )
                END
            );
    """

    async with db.cursor(row_factory=class_row(DbUser)) as cur:
        await cur.execute(
            sql,
            {
                "user_id": user_id,
                "project_id": project_id,
                "org_id": org_id,
                "role": getattr(role, "name", None),
            },
        )
        db_user = await cur.fetchone()

    return db_user if db_user else None


async def super_admin(
    current_user: Annotated[AuthUser, Depends(login_required)],
    db: Annotated[Connection, Depends(db_conn)],
) -> DbUser:
    """Super admin role, with access to all endpoints.

    Returns:
        current_user: DbUser Pydantic model.
    """
    db_user = await check_access(current_user, db)

    if db_user:
        return db_user

    log.error(
        f"User {current_user.username} requested an admin endpoint, but is not admin"
    )
    raise HTTPException(
        status_code=HTTPStatus.FORBIDDEN, detail="User must be an administrator"
    )


async def check_org_admin(
    db: Connection,
    user: AuthUser,
    org_id: int,
) -> OrgUserDict:
    """Database check to determine if org admin role.

    Returns:
        dict: in format {'user': DbUser, 'org': DbOrganisation}.
    """
    db_org = await get_organisation(db, org_id)

    # Check if org admin, or super admin
    db_user = await check_access(
        user,
        db,
        org_id=org_id,
    )

    if not db_user:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="User is not organisation admin",
        )

    return {"user": db_user, "org": db_org}


async def org_admin(
    db: Annotated[Connection, Depends(db_conn)],
    current_user: Annotated[AuthUser, Depends(login_required)],
    project_id: Annotated[Optional[int], Field(gt=0)] = None,
    org_id: Annotated[Optional[int], Field(gt=0)] = None,
) -> OrgUserDict:
    """Organisation admin with full permission for projects in an organisation.

    Returns:
        dict: in format {'user': DbUser, 'org': DbOrganisation}.
    """
    if not (project_id or org_id):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Either org_id or project_id must be provided",
        )

    if project_id and org_id:
        log.error("Both org_id and project_id cannot be passed at the same time")
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Both org_id and project_id cannot be passed at the same time",
        )

    # Extract org id from project if passed
    project = None
    if project_id:
        # NOTE this is a wrapper around DbProject.one with error handling
        project = await get_project_by_id(db, project_id)
        org_id = project.organisation_id

    # Ensure org_id is provided, raise an exception otherwise
    if not org_id:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="org_id must be provided to check organisation admin role",
        )

    org_user_dict = await check_org_admin(
        db,
        current_user,
        org_id=org_id,
    )

    if project:
        org_user_dict["project"] = project

    return org_user_dict


async def wrap_check_access(
    project: DbProject,
    db: Connection,
    user_data: AuthUser,
    role: ProjectRole,
) -> ProjectUserDict:
    """Wrap check_access call with HTTPException."""
    db_user = await check_access(
        user_data,
        db,
        project_id=project.id,
        role=role,
    )

    if not db_user:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="User does not have permission to access the project.",
        )

    return {
        "user": db_user,
        "project": project,
    }


async def project_manager(
    project: Annotated[DbProject, Depends(get_project)],
    db: Annotated[Connection, Depends(db_conn)],
    current_user: Annotated[AuthUser, Depends(login_required)],
) -> ProjectUserDict:
    """A project manager for a specific project."""
    return await wrap_check_access(
        project,
        db,
        current_user,
        ProjectRole.PROJECT_MANAGER,
    )


async def associate_project_manager(
    project: Annotated[DbProject, Depends(get_project)],
    db: Annotated[Connection, Depends(db_conn)],
    current_user: Annotated[AuthUser, Depends(login_required)],
) -> ProjectUserDict:
    """An associate project manager for a specific project."""
    return await wrap_check_access(
        project,
        db,
        current_user,
        ProjectRole.ASSOCIATE_PROJECT_MANAGER,
    )


async def field_manager(
    project: Annotated[DbProject, Depends(get_project)],
    db: Annotated[Connection, Depends(db_conn)],
    current_user: Annotated[AuthUser, Depends(login_required)],
) -> ProjectUserDict:
    """A field manager for a specific project."""
    return await wrap_check_access(
        project,
        db,
        current_user,
        ProjectRole.FIELD_MANAGER,
    )


async def validator(
    project: Annotated[DbProject, Depends(get_project)],
    db: Annotated[Connection, Depends(db_conn)],
    current_user: Annotated[AuthUser, Depends(login_required)],
) -> ProjectUserDict:
    """A validator for a specific project."""
    return await wrap_check_access(
        project,
        db,
        current_user,
        ProjectRole.VALIDATOR,
    )


async def mapper(
    project: Annotated[DbProject, Depends(get_project)],
    db: Annotated[Connection, Depends(db_conn)],
    # Here temp auth token/cookie is allowed
    current_user: Annotated[AuthUser, Depends(mapper_login_required)],
) -> ProjectUserDict:
    """A mapper for a specific project.

    FIXME is this approach flawed?
    FIXME if the user accesses a /tasks/ endpoint but provides a
    FIXME ?project_id=xxx for another project, then won't this
    FIXME given them permission when they shouldn't have it?
    """
    # If project is public, skip permission check
    if project.visibility == ProjectVisibility.PUBLIC:
        return {
            "user": await DbUser.one(db, current_user.id),
            "project": project,
        }

    # As the default user for temp auth (svcfmtm) does not have valid permissions
    # on any project, this will block access for temp login users on projects
    # that are not public
    return await wrap_check_access(
        project,
        db,
        current_user,
        ProjectRole.MAPPER,
    )


async def project_contributors(
    project: Annotated[DbProject, Depends(get_project)],
    db: Annotated[Connection, Depends(db_conn)],
    current_user: Annotated[AuthUser, Depends(login_required)],
) -> ProjectUserDict:
    """A contributor to a specific project."""
    user_id = current_user.id
    project_id = project.id
    org_id = project.organisation_id

    query = """
        SELECT * FROM users
        WHERE id = %(user_id)s
            AND (
                CASE WHEN role = 'ADMIN' THEN true
                ELSE
                    EXISTS (
                        SELECT 1 FROM organisation_managers
                        WHERE organisation_managers.user_id = %(user_id)s
                          AND organisation_managers.organisation_id = %(org_id)s
                    )
                    OR EXISTS (
                        SELECT 1 FROM user_roles
                        WHERE user_roles.user_id = %(user_id)s
                          AND user_roles.project_id = %(project_id)s
                          AND user_roles.role = 'PROJECT_MANAGER'
                    )
                    OR EXISTS (
                        SELECT 1 FROM projects
                        WHERE projects.author_id = %(user_id)s
                    )
                    OR EXISTS (
                        SELECT 1 FROM task_events
                        WHERE task_events.user_id = %(user_id)s
                          AND task_events.project_id = %(project_id)s
                    )
                END
            );
    """
    async with db.cursor() as cur:
        await cur.execute(
            query,
            {"user_id": user_id, "project_id": project_id, "org_id": org_id},
        )
        db_user = await cur.fetchone()

    if db_user:
        return {
            "user": db_user,
            "project": project,
        }

    raise HTTPException(
        status_code=HTTPStatus.FORBIDDEN,
        detail="You must be a project contributor to access this resource.",
    )
