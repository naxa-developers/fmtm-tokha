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
"""Routes associated with data submission to and from ODK Central."""

import json
from io import BytesIO
from typing import Annotated, Optional

import geojson
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from psycopg import Connection

from app.auth.auth_schemas import ProjectUserDict
from app.auth.roles import mapper, project_contributors, project_manager
from app.central import central_crud
from app.db import postgis_utils
from app.db.database import db_conn
from app.db.enums import HTTPStatus
from app.db.models import DbBackgroundTask, DbTask
from app.projects import project_crud, project_schemas
from app.submissions import submission_crud, submission_schemas
from app.db.models import DbTask
from app.projects import project_crud
from app.submissions import submission_crud, submission_deps, submission_schemas
from app.tasks.task_deps import get_task

router = APIRouter(
    prefix="/submission",
    tags=["submission"],
    responses={404: {"description": "Not found"}},
)


@router.get("")
async def read_submissions(
    project_user: Annotated[ProjectUserDict, Depends(mapper)],
) -> list[dict]:
    """Get all submissions made for a project.

    Returns:
        list[dict]: The list of submissions.
    """
    project = project_user.get("project")
    data = await submission_crud.get_submission_by_project(project, {})
    return data.get("value", [])


@router.get("/download")
async def download_submission(
    project_user: Annotated[ProjectUserDict, Depends(project_contributors)],
    export_json: bool = True,
    submitted_date_range: Optional[str] = Query(
        None,
        title="Submitted Date Range",
        description="Date range in format (e.g., 'YYYY-MM-DD,YYYY-MM-DD')",
    ),
):
    """Download the submissions for a given project.

    Returned as either a JSONResponse, or a file to download.

    Returns:
        Union[list[dict], File]: JSON of submissions, or submission file.
    """
    project = project_user.get("project")
    filters = None
    if submitted_date_range:
        start_date, end_date = submitted_date_range.split(",")
        filters = {
            "$filter": (
                f"__system/submissionDate ge {start_date}T00:00:00+00:00 "
                f"and __system/submissionDate le {end_date}T23:59:59.999+00:00"
            )
        }
    if not export_json:
        file_content = await submission_crud.gather_all_submission_csvs(
            project, filters
        )
        headers = {"Content-Disposition": f"attachment; filename={project.slug}.zip"}
        return Response(file_content, headers=headers)

    return await submission_crud.download_submission_in_json(project, filters)


# # FIXME 07/06/2024 since osm-fieldwork update
# @router.get("/convert-to-osm")
# async def convert_to_osm(
#     db: Annotated[Connection, Depends(db_conn)],
#     current_user: Annotated[AuthUser, Depends(login_required)],
#     project_id: int,
#     task_id: Optional[int] = None,
# ):
#     """Convert JSON submissions to OSM XML for a project.

#     Args:
#         project_id (int): The ID of the project.
#         task_id (int, optional): The ID of the task.
#             If provided, returns the submissions made for a specific task only.
#         db (Connection): The database connection.
#         current_user (AuthUser): Check if user is logged in.

#     Returns:
#         File: an OSM XML of submissions.
#     """
#     # NOTE runs in separate thread using run_in_threadpool
#     return FileResponse(
#         await run_in_threadpool(
#             lambda: submission_crud.convert_to_osm(db, project_id, task_id)
#         )
#     )


@router.get("/get-submission-count")
async def get_submission_count(
    project_user: Annotated[ProjectUserDict, Depends(mapper)],
):
    """Get the submission count for a project."""
    project = project_user.get("project")
    return await submission_crud.get_submission_count_of_a_project(project)


# FIXME 07/06/2024 since osm-fieldwork update
# @router.post("/conflate_data")
# async def conflate_osm_data(
#     db: Annotated[Connection, Depends(db_conn)],
#     project_id: int,
#     current_user: Annotated[AuthUser, Depends(login_required)],
# ):
#     """Conflate submission data against existing OSM data."""
#     # All Submissions JSON
#     # NOTE runs in separate thread using run_in_threadpool
#     # FIXME we probably need to change this func
#     submission = await run_in_threadpool(
#         lambda: submission_crud.get_all_submissions_json(db, project_id)
#     )

#     # Data extracta file
#     data_extracts_file = "/tmp/data_extracts_file.geojson"

#     await project_crud.get_extracted_data_from_db(db, project_id, data_extracts_file)

#     # Output file
#     outfile = "/tmp/output_file.osm"
#     # JSON FILE PATH
#     jsoninfile = "/tmp/json_infile.json"

#     # # Delete if these files already exist
#     if os.path.exists(outfile):
#         os.remove(outfile)
#     if os.path.exists(jsoninfile):
#         os.remove(jsoninfile)

#     # Write the submission to a file
#     with open(jsoninfile, "w") as f:
#         f.write(json.dumps(submission))

#     # Convert the submission to osm xml format
#     osmoutfile = await submission_crud.convert_json_to_osm(jsoninfile)

#     # Remove the extra closing </osm> tag from the end of the file
#     with open(osmoutfile, "r") as f:
#         osmoutfile_data = f.read()
#         # Find the last index of the closing </osm> tag
#         last_osm_index = osmoutfile_data.rfind("</osm>")
#         # Remove the extra closing </osm> tag from the end
#         processed_xml_string = (
#             osmoutfile_data[:last_osm_index]
#             + osmoutfile_data[last_osm_index + len("</osm>") :]
#         )

#     # Write the modified XML data back to the file
#     with open(osmoutfile, "w") as f:
#         f.write(processed_xml_string)

#     odkf = OsmFile(outfile)
#     osm = odkf.loadFile(osmoutfile)
#     if osm:
#         odk_merge = OdkMerge(data_extracts_file, None)
#         data = odk_merge.conflateData(osm)
#         return data
#     return []


# FIXME 07/06/2024 since osm-fieldwork update
# @router.get("/get_osm_xml/{project_id}")
# async def get_osm_xml(
#     db: Annotated[Connection, Depends(db_conn)],
#     project_id: int,
#     current_user: Annotated[AuthUser, Depends(login_required)],
# ):
#     """Get the submissions in OSM XML format for a project.

#     TODO refactor to put logic in crud for easier testing.
#     """
#     # JSON FILE PATH
#     jsoninfile = f"/tmp/{project_id}_json_infile.json"

#     # # Delete if these files already exist
#     if os.path.exists(jsoninfile):
#         os.remove(jsoninfile)

#     # All Submissions JSON
#     # NOTE runs in separate thread using run_in_threadpool
#     # FIXME we probably need to change this func
#     submission = await run_in_threadpool(
#         lambda: submission_crud.get_all_submissions_json(db, project_id)
#     )

#     # Write the submission to a file
#     with open(jsoninfile, "w") as f:
#         f.write(json.dumps(submission))

#     # Convert the submission to osm xml format
#     osmoutfile = await submission_crud.convert_json_to_osm(jsoninfile)

#     # Remove the extra closing </osm> tag from the end of the file
#     with open(osmoutfile, "r") as f:
#         osmoutfile_data = f.read()

#     # Create a plain XML response
#     return Response(content=osmoutfile_data, media_type="application/xml")


@router.get("/submission_page")
async def get_submission_page(
    project_user: Annotated[ProjectUserDict, Depends(mapper)],
    days: int,
    planned_task: Optional[int] = None,
):
    """Summary submissison details for submission page.

    Returns:
        dict: A dictionary containing the submission counts for each date.
    """
    project = project_user.get("project")
    data = await submission_crud.get_submissions_by_date(project, days, planned_task)

    return data


@router.get("/submission_form_fields")
async def get_submission_form_fields(
    project_user: Annotated[ProjectUserDict, Depends(mapper)],
):
    """Retrieves the submission form for a specific project.

    Returns:
        Any: The response from the submission form API.
    """
    project = project_user.get("project")
    odk_form = central_crud.get_odk_form(project.odk_credentials)
    return odk_form.formFields(project.odkid, project.odk_form_id)


@router.get("/submission-table")
async def submission_table(
    project_user: Annotated[ProjectUserDict, Depends(mapper)],
    page: int = Query(1, ge=1),
    results_per_page: int = Query(13, le=100),
    task_id: Optional[int] = None,
    submitted_by: Optional[str] = None,
    review_state: Optional[str] = None,
    submitted_date_range: Optional[str] = Query(
        None,
        title="Submitted Date Range",
        description="Date range in format (e.g., 'YYYY-MM-DD,YYYY-MM-DD')",
    ),
):
    """This api returns the submission table of a project.

    Returns:
        dict: Paginated submissions with `results` and `pagination` keys.
    """
    project = project_user.get("project")
    filters = {
        "$count": True,
        "$wkt": True,
    }

    if submitted_date_range:
        start_date, end_date = submitted_date_range.split(",")
        filters["$filter"] = (
            "__system/submissionDate ge {}T00:00:00+00:00 "
            "and __system/submissionDate le {}T23:59:59.999+00:00"
        ).format(start_date, end_date)

    if review_state and review_state != "received":
        review_filter = f"__system/reviewState eq '{review_state}'"
        filters["$filter"] = (
            f"{filters['$filter']} and {review_filter}"
            if "$filter" in filters
            else review_filter
        )

    data = await submission_crud.get_submission_by_project(project, filters)
    total_count = data.get("@odata.count", 0)
    submissions = data.get("value", [])
    if review_state == "received":
        submissions = [
            sub for sub in submissions if sub["__system"].get("reviewState") is None
        ]
        total_count = len(submissions)

    if task_id:
        submissions = [sub for sub in submissions if sub.get("task_id") == str(task_id)]

    if submitted_by:
        submissions = [
            sub for sub in submissions if sub.get("username") == submitted_by
        ]

    start_index = (page - 1) * results_per_page
    end_index = start_index + results_per_page
    paginated_submissions = submissions[start_index:end_index]

    pagination = await project_crud.get_pagination(
        page, len(submissions), results_per_page, total_count
    )
    response = submission_schemas.PaginatedSubmissions(
        results=paginated_submissions,
        pagination=submission_schemas.PaginationInfo(**pagination.model_dump()),
    )

    return response


@router.post(
    "/update-review-state",
    response_model=submission_schemas.ReviewStateOut,
)
async def update_review_state(
    post_data: submission_schemas.ReviewStateIn,
    current_user: Annotated[ProjectUserDict, Depends(project_manager)],
):
    """Updates the review state of a project submission."""
    try:
        project = current_user.get("project")
        odk_project = central_crud.get_odk_project(project.odk_credentials)

        response = odk_project.updateReviewState(
            project.odkid,
            project.odk_form_id,
            post_data.instance_id,
            {"reviewState": post_data.review_state},
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e


@router.get("/download-submission-geojson")
async def download_submission_geojson(
    project_user: Annotated[ProjectUserDict, Depends(project_contributors)],
    submitted_date_range: Optional[str] = Query(
        None,
        title="Submitted Date Range",
        description="Date range in format (e.g., 'YYYY-MM-DD,YYYY-MM-DD')",
    ),
):
    """Download submission geojson for a specific project."""
    project = project_user.get("project")
    filters = {}

    if submitted_date_range:
        start_date, end_date = submitted_date_range.split(",")
        filters = {
            "$filter": (
                f"__system/submissionDate ge {start_date}T00:00:00+00:00 "
                f"and __system/submissionDate le {end_date}T23:59:59.999+00:00"
            )
        }
    data = await submission_crud.get_submission_by_project(project, filters)
    submission_json = data.get("value", [])

    submission_geojson = await central_crud.convert_odk_submission_json_to_geojson(
        submission_json
    )
    submission_data = BytesIO(json.dumps(submission_geojson).encode("utf-8"))
    filename = project.slug

    headers = {"Content-Disposition": f"attachment; filename={filename}.geojson"}

    return Response(submission_data.getvalue(), headers=headers)


@router.get("/conflate-submission-geojson")
async def conflate_geojson(
    db_task: Annotated[DbTask, Depends(get_task)],
    project_user: Annotated[ProjectUserDict, Depends(mapper)],
    remove_conflated: Annotated[
        bool,
        Query(
            description="Removes geometries not overlapping with OSM data",
        ),
    ] = False,
):
    """Conflates the input GeoJSON with OpenStreetMap data.

    Returns:
        str: Updated GeoJSON string with conflated features.
    """
    try:
        project = project_user.get("project")
        task_geojson = geojson.dumps(db_task.outline, indent=2)

        data = await submission_crud.get_submission_by_project(project, {})
        submission_json = data.get("value", [])
        task_submission = [
            sub for sub in submission_json if sub["task_id"] == str(db_task.id)
        ]

        if not task_submission:
            return JSONResponse(
                status_code=HTTPStatus.NOT_FOUND,
                content=f"No Submissions found within the task {db_task.id}",
            )

        submission_geojson = await central_crud.convert_odk_submission_json_to_geojson(
            task_submission
        )
        form_category = project.xform_category
        input_features = submission_geojson["features"]

        osm_features = postgis_utils.get_osm_geometries(form_category, task_geojson)
        conflated_features = postgis_utils.conflate_features(
            input_features, osm_features.get("features", []), remove_conflated
        )
        submission_geojson["features"] = conflated_features

        return submission_geojson
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to process conflation: {str(e)}",
        ) from e


@router.get("/{submission_id}/photos")
async def submission_photos(
    submission_id: str,
    project_user: Annotated[ProjectUserDict, Depends(mapper)],
) -> dict:
    """This api returns the submission detail of individual submission."""
    project = project_user.get("project")
    submission_attachments = await submission_crud.get_submission_photos(
        submission_id,
        project,
    )
    return {
        "image_urls": submission_attachments,
    }


@router.get(
    "/{project_id}/dashboard", response_model=submission_schemas.SubmissionDashboard
)
async def project_dashboard(
    project_user: Annotated[ProjectUserDict, Depends(mapper)],
    db: Annotated[Connection, Depends(db_conn)],
):
    """Get the project dashboard details."""
    project = project_user.get("project")
    details = await submission_crud.get_dashboard_detail(db, project)
    details["slug"] = project.slug
    details["organisation_name"] = project.organisation_name
    details["created_at"] = project.created_at
    details["organisation_logo"] = project.organisation_logo
    details["last_active"] = project.last_active
    return details


@router.get("/{submission_id}")
async def submission_detail(
    submission_id: str,
    project_user: Annotated[ProjectUserDict, Depends(mapper)],
) -> dict:
    """This api returns the submission detail of individual submission."""
    project = project_user.get("project")
    submission_detail = await submission_crud.get_submission_detail(
        submission_id,
        project,
    )
    return submission_detail
