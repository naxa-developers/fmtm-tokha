# Copyright (c) 2023 Humanitarian OpenStreetMap Team
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
"""Routes to relay requests to ODK Central server."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from loguru import logger as log
from psycopg import Connection

from app.auth.auth_deps import login_required
from app.auth.auth_schemas import AuthUser, ProjectUserDict
from app.auth.roles import project_manager
from app.central import central_crud
from app.db.database import db_conn
from app.db.enums import HTTPStatus
from app.db.models import DbProject
from app.projects.project_schemas import ProjectUpdate

router = APIRouter(
    prefix="/central",
    tags=["central"],
    responses={404: {"description": "Not found"}},
)


@router.get("/projects")
async def list_projects():
    """List projects in Central."""
    # TODO update for option to pass credentials by user
    # NOTE runs in separate thread using run_in_threadpool
    projects = await run_in_threadpool(lambda: central_crud.list_odk_projects())
    if projects is None:
        return {"message": "No projects found"}
    return JSONResponse(content={"projects": projects})


@router.get("/list-forms")
async def get_form_lists(
    current_user: Annotated[AuthUser, Depends(login_required)],
    db: Annotated[Connection, Depends(db_conn)],
) -> list:
    """Get a list of all XLSForms available in FMTM.

    Returns:
        dict: JSON of {id:title} with each XLSForm record.
    """
    forms = await central_crud.get_form_list(db)
    return forms


@router.post("/refresh-appuser-token")
async def refresh_appuser_token(
    current_user: Annotated[AuthUser, Depends(project_manager)],
    db: Annotated[Connection, Depends(db_conn)],
):
    """Refreshes the token for the app user associated with a specific project.

    Response:
        {
            "status_code": HTTPStatus.OK,
            "message": "App User token has been successfully refreshed.",
        }
    """
    project = current_user.get("project")
    project_id = project.id
    project_odk_id = project.odkid
    project_xform_id = project.odk_form_id
    project_odk_creds = project.odk_credentials

    try:
        odk_token = await central_crud.get_appuser_token(
            project_xform_id,
            project_odk_id,
            project_odk_creds,
        )
        await DbProject.update(
            db,
            project_id,
            ProjectUpdate(
                odk_token=odk_token,
            ),
        )

        return JSONResponse(
            content={
                "message": "App User token has been successfully refreshed.",
            }
        )

    except Exception as e:
        log.exception(f"Error: {e}", stack_info=True)
        msg = f"failed to refresh the appuser token for project {project_id}"
        log.error(msg)
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=msg,
        ) from e


@router.delete("/entity/{entity_uuid}")
async def delete_odk_entity(
    entity_uuid: str,
    project_user_dict: Annotated[
        ProjectUserDict, Depends(project_manager)
    ],
    dataset_name: str = "features",
):
    """Delete an Entity from ODK."""
    # TODO: The user that created the entity should also be able to delete it.
    try:
        project = project_user_dict.get("project")
        project_odk_id = project.odkid
        project_odk_creds = project.odk_credentials

        # Call the refactored delete_entity function
        success = await central_crud.delete_entity(
            odk_creds=project_odk_creds,
            odk_id=project_odk_id,
            entity_uuid=entity_uuid,
            dataset_name=dataset_name,
        )

        if not success:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Entity deletion unsuccessful",
            )

        return {"detail": "Entity deleted successfully", "uuid": entity_uuid}

    except HTTPException as http_err:
        log.error(f"HTTP error during deletion: {http_err.detail}")
        raise
    except Exception as e:
        log.exception("Unexpected error during entity deletion")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Entity deletion failed",
        ) from e
