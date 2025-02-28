import React, { useEffect, useState } from 'react';
import { Modal } from '@/components/common/Modal';
import { SubmissionActions } from '@/store/slices/SubmissionSlice';
import { reviewListType } from '@/models/submission/submissionModel';
import { DeleteGeometry, PostGeometry, UpdateReviewStateService } from '@/api/SubmissionService';
import TextArea from '../common/TextArea';
import Button from '../common/Button';
import { GetGeometryLog, PostProjectComments, UpdateEntityState } from '@/api/Project';
import { entity_state } from '@/types/enums';
import { useAppDispatch, useAppSelector } from '@/types/reduxTypes';
import { task_event } from '@/types/enums';
import { featureType } from '@/store/types/ISubmissions';

// Note these id values must be camelCase to match what ODK Central requires
const reviewList: reviewListType[] = [
  {
    id: 'approved',
    title: 'Approved',
    className: 'fmtm-bg-[#E7F3E8] fmtm-text-[#40B449] fmtm-border-[#40B449]',
    hoverClass: 'hover:fmtm-text-[#40B449] hover:fmtm-border-[#40B449]',
  },
  {
    id: 'hasIssues',
    title: 'Has Issue',
    className: 'fmtm-bg-[#E9DFCF] fmtm-text-[#D99F00] fmtm-border-[#D99F00]',
    hoverClass: 'hover:fmtm-text-[#D99F00] hover:fmtm-border-[#D99F00]',
  },
];

const UpdateReviewStatusModal = () => {
  const dispatch = useAppDispatch();
  const [noteComments, setNoteComments] = useState('');
  const [reviewStatus, setReviewStatus] = useState('');
  const updateReviewStatusModal = useAppSelector((state) => state.submission.updateReviewStatusModal);
  const updateReviewStateLoading = useAppSelector((state) => state.submission.updateReviewStateLoading);
  const badGeomLogList = useAppSelector((state) => state?.project?.badGeomLogList);

  useEffect(() => {
    setReviewStatus(updateReviewStatusModal.reviewState);
  }, [updateReviewStatusModal.reviewState]);

  useEffect(() => {
    if (!updateReviewStatusModal.projectId) return;
    dispatch(
      GetGeometryLog(`${import.meta.env.VITE_API_URL}/projects/${updateReviewStatusModal.projectId}/geometry/records`),
    );
  }, [updateReviewStatusModal.projectId]);

  const handleStatusUpdate = async () => {
    if (
      !updateReviewStatusModal.instanceId ||
      !updateReviewStatusModal.projectId ||
      !updateReviewStatusModal.taskId ||
      !updateReviewStatusModal.entity_id ||
      !updateReviewStatusModal.taskUid
    ) {
      return;
    }

    if (updateReviewStatusModal.reviewState !== reviewStatus) {
      await dispatch(
        UpdateReviewStateService(
          `${import.meta.env.VITE_API_URL}/submission/update-review-state?project_id=${updateReviewStatusModal.projectId}`,
          {
            instance_id: updateReviewStatusModal.instanceId,
            review_state: reviewStatus,
          },
        ),
      );

      // post bad geometry if submission is marked as hasIssues
      if (reviewStatus === 'hasIssues') {
        const badFeature = {
          ...(updateReviewStatusModal.feature as featureType),
          properties: {
            entity_id: updateReviewStatusModal.entity_id,
            task_id: updateReviewStatusModal.taskUid,
            instance_id: updateReviewStatusModal.instanceId,
          },
        };

        dispatch(
          PostGeometry(
            `${import.meta.env.VITE_API_URL}/projects/${updateReviewStatusModal.projectId}/geometry/records`,
            {
              status: 'BAD',
              geojson: badFeature,
              project_id: updateReviewStatusModal.projectId,
              task_id: +updateReviewStatusModal.taskUid,
            },
          ),
        );
      }

      // delete bad geometry if the entity previously has rejected submission and current submission is marked as approved
      if (reviewStatus === 'approved') {
        const badGeomId = badGeomLogList.find(
          (geom) => geom.geojson.properties.entity_id === updateReviewStatusModal.entity_id,
        )?.id;
        dispatch(
          DeleteGeometry(
            `${import.meta.env.VITE_API_URL}/projects/${updateReviewStatusModal.projectId}/geometry/records/${badGeomId}`,
          ),
        );
      }

      dispatch(
        UpdateEntityState(
          `${import.meta.env.VITE_API_URL}/projects/${updateReviewStatusModal.projectId}/entity/status`,
          {
            entity_id: updateReviewStatusModal.entity_id,
            status: reviewStatus === 'approved' ? entity_state['SURVEY_SUBMITTED'] : entity_state['MARKED_BAD'],
            label: updateReviewStatusModal.label,
          },
        ),
      );
    }

    if (noteComments.trim().length > 0) {
      dispatch(
        PostProjectComments(
          `${import.meta.env.VITE_API_URL}/tasks/${updateReviewStatusModal?.taskUid}/event?project_id=${updateReviewStatusModal?.projectId}`,
          {
            task_id: +updateReviewStatusModal?.taskUid,
            comment: `#submissionId:${updateReviewStatusModal?.instanceId} #featureId:${updateReviewStatusModal?.entity_id} ${noteComments}`,
            event: task_event.COMMENT,
          },
        ),
      );
      setNoteComments('');
    }
    dispatch(
      SubmissionActions.SetUpdateReviewStatusModal({
        toggleModalStatus: false,
        projectId: null,
        instanceId: null,
        taskId: null,
        reviewState: '',
        taskUid: null,
        entity_id: null,
        label: null,
        feature: null,
      }),
    );
    dispatch(SubmissionActions.UpdateReviewStateLoading(false));
  };

  return (
    <Modal
      title={
        <div className="fmtm-w-full fmtm-flex fmtm-justify-start">
          <h2 className="!fmtm-text-lg fmtm-font-archivo fmtm-tracking-wide">Update Review Status</h2>
        </div>
      }
      className="!fmtm-w-[23rem] !fmtm-outline-none fmtm-rounded-xl"
      description={
        <div className="fmtm-mt-9">
          <div className="fmtm-mb-4">
            <div className="fmtm-flex fmtm-gap-2">
              {reviewList.map((reviewBtn) => (
                <button
                  key={reviewBtn.id}
                  className={`${
                    reviewBtn.id === reviewStatus
                      ? reviewBtn.className
                      : `fmtm-border-[#D7D7D7] fmtm-bg-[#F5F5F5] fmtm-text-[#484848] ${reviewBtn.hoverClass} fmtm-duration-150`
                  } fmtm-pt-2 fmtm-pb-1 fmtm-px-7 fmtm-outline-none fmtm-w-fit fmtm-border-[1px] fmtm-rounded-[40px] fmtm-font-archivo fmtm-text-sm`}
                  onClick={() => setReviewStatus(reviewBtn.id)}
                >
                  {reviewBtn.title}
                </button>
              ))}
            </div>
          </div>
          <TextArea
            rows={4}
            onChange={(e) => setNoteComments(e.target.value)}
            value={noteComments}
            label="Note & Comments"
          />
          <div className="fmtm-grid fmtm-grid-cols-2 fmtm-gap-4 fmtm-mt-8">
            <Button
              btnText="Cancel"
              btnType="other"
              className="fmtm-w-full fmtm-justify-center !fmtm-rounded fmtm-font-bold fmtm-text-sm !fmtm-py-2"
              onClick={() => {
                dispatch(
                  SubmissionActions.SetUpdateReviewStatusModal({
                    toggleModalStatus: false,
                    projectId: null,
                    instanceId: null,
                    taskId: null,
                    reviewState: '',
                    taskUid: null,
                    entity_id: null,
                    label: null,
                    feature: null,
                  }),
                );
              }}
            />
            <Button
              loadingText="Updating"
              isLoading={updateReviewStateLoading}
              disabled={!reviewStatus}
              btnText="Update"
              btnType="primary"
              className="fmtm-w-full fmtm-justify-center !fmtm-rounded fmtm-font-bold fmtm-text-sm !fmtm-py-2"
              onClick={handleStatusUpdate}
            />
          </div>
        </div>
      }
      open={updateReviewStatusModal.toggleModalStatus}
      onOpenChange={(value) => {
        dispatch(
          SubmissionActions.SetUpdateReviewStatusModal({
            toggleModalStatus: value,
            projectId: null,
            instanceId: null,
            taskId: null,
            reviewState: '',
            taskUid: null,
            entity_id: null,
            label: null,
            feature: null,
          }),
        );
      }}
    />
  );
};

export default UpdateReviewStatusModal;
