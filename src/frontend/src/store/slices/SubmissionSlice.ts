import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { SubmissionStateTypes } from '@/store/types/ISubmissions';
import { updateReviewStateType, validatedMappedType } from '@/models/submission/submissionModel';

const initialState: SubmissionStateTypes = {
  submissionDetailsLoading: true,
  submissionDetails: null,
  submissionContributors: [],
  submissionContributorsLoading: true,
  submissionFormFields: [],
  submissionTableData: {
    results: [],
    pagination: {
      has_next: false,
      has_prev: false,
      total: null,
      page: null,
      prev_num: null,
      next_num: null,
      per_page: null,
      pages: null,
    },
  },
  submissionFormFieldsLoading: false,
  submissionTableDataLoading: false,
  submissionTableRefreshing: false,
  updateReviewStatusModal: {
    toggleModalStatus: false,
    instanceId: null,
    taskId: null,
    projectId: null,
    reviewState: '',
    taskUid: null,
    entity_id: null,
    label: null,
  },
  updateReviewStateLoading: false,
  mappedVsValidatedTask: [],
  mappedVsValidatedTaskLoading: false,
  submissionPhotos: [],
  submissionPhotosLoading: false,
  DownloadSubmissionGeojsonLoading: false,
};

const SubmissionSlice = createSlice({
  name: 'submission',
  initialState: initialState,
  reducers: {
    SetSubmissionDetailsLoading(state, action: PayloadAction<boolean>) {
      state.submissionDetailsLoading = action.payload;
    },
    SetSubmissionDetails(state, action: PayloadAction<Record<string, any> | null>) {
      state.submissionDetails = action.payload;
    },
    SetSubmissionContributors(state, action: PayloadAction<SubmissionStateTypes['submissionContributors']>) {
      state.submissionContributors = action.payload;
    },
    SetSubmissionContributorsLoading(state, action: PayloadAction<boolean>) {
      state.submissionContributorsLoading = action.payload;
    },
    SetSubmissionFormFields(state, action: PayloadAction<SubmissionStateTypes['submissionFormFields']>) {
      state.submissionFormFields = action.payload;
    },
    SetSubmissionTable(state, action: PayloadAction<SubmissionStateTypes['submissionTableData']>) {
      state.submissionTableData = action.payload;
    },
    SetSubmissionFormFieldsLoading(state, action: PayloadAction<boolean>) {
      state.submissionFormFieldsLoading = action.payload;
    },
    SetSubmissionTableLoading(state, action: PayloadAction<boolean>) {
      state.submissionTableDataLoading = action.payload;
    },
    SetSubmissionTableRefreshing(state, action: PayloadAction<boolean>) {
      state.submissionTableRefreshing = action.payload;
    },
    SetUpdateReviewStatusModal(state, action: PayloadAction<SubmissionStateTypes['updateReviewStatusModal']>) {
      state.updateReviewStatusModal = action.payload;
    },
    UpdateReviewStateLoading(state, action: PayloadAction<boolean>) {
      state.updateReviewStateLoading = action.payload;
    },
    UpdateSubmissionTableDataReview(state, action: PayloadAction<updateReviewStateType>) {
      const updatedSubmission = action.payload;

      // submission-instance table update
      if (state.submissionTableData.results.length > 0) {
        const updatedSubmissionDataList = state.submissionTableData.results.map((submissionData: any) => {
          if (updatedSubmission.instanceId === submissionData.meta.instanceID) {
            return {
              ...submissionData,
              __system: { ...submissionData.__system, reviewState: updatedSubmission.reviewState },
            };
          }
          return submissionData;
        });
        state.submissionTableData.results = updatedSubmissionDataList;
      }

      // submission-instance key value pair update
      if (state.submissionDetails) {
        state.submissionDetails = {
          ...state.submissionDetails,
          __system: { ...state.submissionDetails.__system, reviewState: updatedSubmission.reviewState },
        };
      }
    },
    SetMappedVsValidatedTask(state, action: PayloadAction<validatedMappedType[]>) {
      const MappedVsValidatedTask = action.payload;
      state.mappedVsValidatedTask = MappedVsValidatedTask?.map((task) => ({
        ...task,
        label: task?.date?.split('/').slice(0, 2).join('/'),
      }));
    },
    SetMappedVsValidatedTaskLoading(state, action: PayloadAction<boolean>) {
      state.mappedVsValidatedTaskLoading = action.payload;
    },
    SetSubmissionPhotos(state, action: PayloadAction<string[]>) {
      state.submissionPhotos = action.payload;
    },
    SetSubmissionPhotosLoading(state, action: PayloadAction<boolean>) {
      state.submissionPhotosLoading = action.payload;
    },
    DownloadSubmissionGeojsonLoading(state, action: PayloadAction<boolean>) {
      state.DownloadSubmissionGeojsonLoading = action.payload;
    },
  },
});

export const SubmissionActions = SubmissionSlice.actions;
export default SubmissionSlice;
