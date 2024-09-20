import {
  submissionContributorsTypes,
  submissionFormFieldsTypes,
  submissionTableDataTypes,
} from '@/models/submission/submissionModel';

export type SubmissionStateTypes = {
  submissionDetailsLoading: boolean;
  submissionDetails: Record<string, any> | null;
  submissionContributors: submissionContributorsTypes[];
  submissionContributorsLoading: boolean;
  submissionFormFields: submissionFormFieldsTypes[];
  submissionTableData: submissionTableDataTypes;
  submissionFormFieldsLoading: boolean;
  submissionTableDataLoading: boolean;
  submissionTableRefreshing: boolean;
  updateReviewStatusModal: updateReviewStatusModal;
  updateReviewStateLoading: boolean;
};

type updateReviewStatusModal = {
  toggleModalStatus: boolean;
  instanceId: string | null;
  taskId: string | null;
  projectId: number | null;
  reviewState: string;
  taskUId: string | null;
};

export type filterType = {
  task_id: string | null;
  submitted_by: string | null;
  review_state: string | null;
  submitted_date: string | null;
};
