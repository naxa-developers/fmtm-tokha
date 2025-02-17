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
"""Functions for task submissions."""

import json
from collections import Counter
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional

from fastapi import HTTPException, Response
from loguru import logger as log
from psycopg import Connection

# from osm_fieldwork.json2osm import json2osm
from app.central.central_crud import (
    get_odk_form,
)
from app.central.central_deps import get_async_odk_form
from app.db.enums import HTTPStatus
from app.db.models import DbProject
from app.db.postgis_utils import timestamp
from app.projects import project_crud

# async def convert_json_to_osm(file_path):
#     """Wrapper for osm-fieldwork json2osm."""
#     osm_xml_path = json2osm(file_path)
#     return osm_xml_path


# # FIXME 07/06/2024 since osm-fieldwork update
# def convert_to_osm(project_id: int, task_id: Optional[int]):
#     """Convert submissions to OSM XML format."""
#     project_sync = async_to_sync(project_deps.get_project_by_id)
#     project = project_sync(db, project_id)

#     get_submission_sync = async_to_sync(get_submission_by_project)
#     data = get_submission_sync(project_id, {})

#     submissions = data.get("value", [])

#     # Create a new ZIP file for the extracted files
#     final_zip_file_path = f"/tmp/{project.slug}_osm.zip"

#     # Remove the ZIP file if it already exists
#     if os.path.exists(final_zip_file_path):
#         os.remove(final_zip_file_path)

#     # filter submission by task_id
#     if task_id:
#         submissions = [
#             sub
#             for sub in submissions
#             if sub.get("task_id") == str(task_id)
#         ]

#     if not submissions:
#         raise HTTPException(
#              status_code=HTTPStatus.NOT_FOUND,
#              detail="Submission not found")

#     # JSON FILE PATH
#     jsoninfile = "/tmp/json_infile.json"

#     # Write the submission to a file
#     with open(jsoninfile, "w") as f:
#         f.write(json.dumps(submissions))

#     # Convert the submission to osm xml format
#     convert_json_to_osm_sync = async_to_sync(convert_json_to_osm)

#     if osm_file_path := convert_json_to_osm_sync(jsoninfile):
#         with open(osm_file_path, "r") as osm_file:
#             osm_data = osm_file.read()
#             last_osm_index = osm_data.rfind("</osm>")
#             processed_xml_string = (
#                 osm_data[:last_osm_index] + osm_data[last_osm_index + len("</osm>") :]
#             )

#         with open(osm_file_path, "w") as osm_file:
#             osm_file.write(processed_xml_string)

#         final_zip_file_path = f"/tmp/{project.slug}_osm.zip"
#         if os.path.exists(final_zip_file_path):
#             os.remove(final_zip_file_path)

#         with zipfile.ZipFile(final_zip_file_path, mode="a") as final_zip_file:
#             final_zip_file.write(osm_file_path)

#     return final_zip_file_path


async def gather_all_submission_csvs(project: DbProject, filters: dict):
    """Gather all of the submission CSVs for a project.

    Generate a single zip with all submissions.
    """
    log.info(f"Downloading all CSV submissions for project {project.id}")
    xform = get_odk_form(project.odk_credentials)
    file = xform.getSubmissionMedia(project.odkid, project.odk_form_id, filters)
    return file.content


async def download_submission_in_json(project: DbProject, filters: dict):
    """Download submission data from ODK Central."""
    if data := await get_submission_by_project(project, filters):
        json_data = data
    else:
        json_data = None

    json_bytes = BytesIO(json.dumps(json_data).encode("utf-8"))
    headers = {
        "Content-Disposition": f"attachment; filename={project.slug}_submissions.json"
    }
    return Response(content=json_bytes.getvalue(), headers=headers)


async def get_submission_count_of_a_project(project: DbProject):
    """Return the total number of submissions made for a project."""
    # Get ODK Form with odk credentials from the project.
    xform = get_odk_form(project.odk_credentials)
    data = xform.listSubmissions(project.odkid, project.odk_form_id, {})
    return len(data["value"])


async def get_submissions_by_date(
    project: DbProject,
    days: int,
    planned_task: Optional[int] = None,
):
    """Get submissions by date.

    Fetches the submissions for a given project within a specified number of days.

    Args:
        project (DbProject): The database project object.
        days (int): The number of days to consider for fetching submissions.
        planned_task (int): Associated task id.

    Returns:
        dict: A dictionary containing the submission counts for each date.

    Examples:
        # Fetch submissions for project with ID 1 within the last 7 days
        submissions = await get_submissions_by_date(1, 7)
    """
    data = await get_submission_by_project(project, {})

    end_dates = [
        datetime.fromisoformat(entry["end"].split("+")[0])
        for entry in data["value"]
        if entry.get("end")
    ]

    dates = [
        date.strftime("%m/%d")
        for date in end_dates
        if timestamp() - date <= timedelta(days=days)
    ]

    submission_counts = Counter(sorted(dates))

    response = [
        {"date": key, "count": value} for key, value in submission_counts.items()
    ]
    if planned_task:
        count_dict = {}
        cummulative_count = 0
        for date, count in submission_counts.items():
            cummulative_count += count
            count_dict[date] = cummulative_count
        response = [
            {"date": key, "count": count_dict[key], "planned": planned_task}
            for key, value in submission_counts.items()
        ]

    return response


async def get_submission_by_project(
    project: DbProject,
    filters: dict,
):
    """Get submission by project.

    Retrieves a paginated list of submissions for a given project.

    Args:
        project (DbProject): The database project object.
        filters (dict): The filters to apply directly to submissions
            in odk central.

    Returns:
        Tuple[int, List]: A tuple containing the total number of submissions and
        the paginated list of submissions.

    Raises:
        ValueError: If the submission file cannot be found.

    """
    xform = get_odk_form(project.odk_credentials)
    return xform.listSubmissions(project.odkid, project.odk_form_id, filters)


async def get_submission_detail(
    submission_id: str,
    project: DbProject,
):
    """Get the details of a submission.

    Args:
        submission_id: The instance uuid of the submission.
        project: The project object representing the project.

    Returns:
        The details of the submission as a JSON object.
    """
    odk_form = get_odk_form(project.odk_credentials)

    project_submissions = odk_form.getSubmissions(
        project.odkid, project.odk_form_id, submission_id
    )
    if not project_submissions:
        log.warning("Failed to download submissions due to unknown error")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Failed to download submissions",
        )

    submission = json.loads(project_submissions)
    return submission.get("value", [])[0]


async def get_submission_photos(
    submission_id: str,
    project: DbProject,
):
    """Get the details of a submission.

    Args:
        submission_id: The instance uuid of the submission.
        project: The project object representing the project.

    Returns:
        The details of the submission as a JSON object.
    """
    async with get_async_odk_form(project.odk_credentials) as async_odk_form:
        submission_photos = await async_odk_form.getSubmissionAttachmentUrls(
            project.odkid, project.odk_form_id, submission_id
        )

    return submission_photos


async def get_dashboard_detail(db: Connection, project: DbProject):
    """Get project details for project dashboard."""
    xform = get_odk_form(project.odk_credentials)
    submission_meta_data = xform.getFullDetails(project.odkid, project.odk_form_id)

    contributors_dict = await project_crud.get_project_users_plus_contributions(
        db,
        project.id,
    )
    return {
        "total_submission": submission_meta_data.get("submissions", 0),
        "last_active": submission_meta_data.get("lastSubmission"),
        "total_tasks": len(project.tasks),
        "total_contributors": len(contributors_dict),
    }
