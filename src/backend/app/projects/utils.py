import uuid
from typing import Optional

from fastapi import (
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.logger import logger as logger
from sqlalchemy.orm import Session

from ..db import database
from . import project_crud

async def generate_files(
    background_tasks: BackgroundTasks,
    project_id: int,
    extract_polygon: bool = Form(False),
    upload: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
):
    """Generate required media files tasks in the project based on the provided params.

    Accepts a project ID, category, custom form flag, and an uploaded file as inputs.
    The generated files are associated with the project ID and stored in the database.
    This api generates qr_code, forms. This api also creates an app user for each task and provides the required roles.
    Some of the other functionality of this api includes converting a xls file provided by the user to the xform,
    generates osm data extracts and uploads it to the form.


    Parameters:

    project_id (int): The ID of the project for which files are being generated. This is a required field.
    polygon (bool): A boolean flag indicating whether the polygon is extracted or not.

    upload (UploadFile): An uploaded file that is used as input for generating the files.
        This is not a required field. A file should be provided if user wants to upload a custom xls form.

    Returns:
    Message (str): A success message containing the project ID.

    """
    contents = None
    xform_title = None

    project = project_crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=428, detail=f"Project with id {project_id} does not exist"
        )

    project.data_extract_type = 'polygon' if extract_polygon else 'centroid'
    db.commit()

    if upload:
        file_ext = 'xls'
        contents = upload

    # generate a unique task ID using uuid
    background_task_id = uuid.uuid4()

    # insert task and task ID into database
    await project_crud.insert_background_task_into_database(
        db, task_id=background_task_id
    )

    background_tasks.add_task(
        project_crud.generate_appuser_files,
        db,
        project_id,
        extract_polygon,
        contents,
        None,
        xform_title,
        file_ext if upload else 'xls',
        background_task_id,
    )

    return {"Message": f"{project_id}", "task_id": f"{background_task_id}"}