import axios, { AxiosResponse } from 'axios';
import { SubmissionActions } from '@/store/slices/SubmissionSlice';
import { AppDispatch } from '@/store/Store';

export const SubmissionService = (url: string) => {
  return async (dispatch: AppDispatch) => {
    dispatch(SubmissionActions.SetSubmissionDetails(null));
    dispatch(SubmissionActions.SetSubmissionDetailsLoading(true));
    const getSubmissionDetails = async (url: string) => {
      try {
        const response: AxiosResponse<Record<string, any>> = await axios.get(url);
        dispatch(SubmissionActions.SetSubmissionDetails(response.data));
        dispatch(SubmissionActions.SetSubmissionDetailsLoading(false));
      } catch (error) {
        dispatch(SubmissionActions.SetSubmissionDetailsLoading(false));
      } finally {
        dispatch(SubmissionActions.SetSubmissionDetailsLoading(false));
      }
    };
    await getSubmissionDetails(url);
  };
};

export const GetSubmissionPhotosService = (url: string, params: { project_id: number }) => {
  return async (dispatch: AppDispatch) => {
    dispatch(SubmissionActions.SetSubmissionPhotosLoading(true));
    const getSubmissionPhotos = async (url: string) => {
      try {
        const response: AxiosResponse<{ image_urls: string[] }> = await axios.get(url, { params });
        dispatch(SubmissionActions.SetSubmissionPhotos(response?.data?.image_urls));
        dispatch(SubmissionActions.SetSubmissionPhotosLoading(false));
      } catch (error) {
        dispatch(SubmissionActions.SetSubmissionPhotosLoading(false));
      } finally {
        dispatch(SubmissionActions.SetSubmissionPhotosLoading(false));
      }
    };
    await getSubmissionPhotos(url);
  };
};
