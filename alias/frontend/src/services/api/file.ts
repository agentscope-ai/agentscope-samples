import {
  DeleteFileResponse,
  FileResponse,
  ShareFileRequest,
  UploadFileResponse,
} from "@/types/api";
import axios, { AxiosRequestConfig } from "axios";
import { request } from "./request";

// Create a dedicated axios instance for file operations
const fileInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 60000,
});

// Add request interceptor to set token
fileInstance.interceptors.request.use((config) => {
  const token =
    localStorage.getItem("access_token") ||
    import.meta.env.VITE_API_ACCESS_TOKEN;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const fileApi = {
  // Get file information
  getFileInfo: (fileId: string) => {
    return request.get<FileResponse>(`/api/v1/files/${fileId}`);
  },

  // Upload file
  uploadFile: (
    file: File,
    onUploadProgress?: (progressEvent: any) => void,
    abortController?: AbortController,
  ) => {
    const formData = new FormData();
    formData.append("file", file);

    return request.post<UploadFileResponse>("/api/v1/files/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress,
      signal: abortController?.signal,
    });
  },

  // Delete file
  deleteFile: (fileId: string) => {
    return request.delete<DeleteFileResponse>(`/api/v1/files/${fileId}`);
  },

  // Download file
  downloadFile: (fileId: string) => {
    const config: AxiosRequestConfig = {
      responseType: "blob",
      transformResponse: [(data) => data], // Prevent axios from parsing response
    };
    return fileInstance.get(`/api/v1/files/${fileId}/download`, config);
  },

  // Set file share status
  shareFile: (fileId: string, share: boolean) => {
    return request.post<FileResponse>(`/api/v1/files/${fileId}/share`, {
      share,
    } as ShareFileRequest);
  },

  // Preview file
  previewFile: (fileId: string) => {
    const config: AxiosRequestConfig = {
      responseType: "blob",
      transformResponse: [(data) => data],
    };
    return fileInstance.get(`/api/v1/files/${fileId}/preview`, config);
  },

  // Public preview file
  publicPreviewFile: (fileId: string) => {
    const config: AxiosRequestConfig = {
      responseType: "blob",
      transformResponse: [(data) => data],
    };
    return fileInstance.get(`/api/v1/files/${fileId}/public`, config);
  },

  // Utility function to download file with name
  downloadFileWithName: async (
    fileId: string,
    defaultFileName: string = "downloaded_file",
  ) => {
    try {
      const response = await fileApi.downloadFile(fileId);

      // Get filename from Content-Disposition
      const contentDisposition = response.headers["content-disposition"];
      let fileName = defaultFileName;

      if (contentDisposition) {
        const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(
          contentDisposition,
        );
        if (matches != null && matches[1]) {
          fileName = matches[1].replace(/['"]/g, "");
        }
      }

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", fileName);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Failed to download file:", error);
      throw error;
    }
  },

  // Utility function to preview file in new tab
  previewFileInNewTab: async (fileId: string, isPublic: boolean = false) => {
    try {
      const response = await (isPublic
        ? fileApi.publicPreviewFile(fileId)
        : fileApi.previewFile(fileId));

      // Create preview link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      window.open(url, "_blank");
      // Delay URL revocation
      setTimeout(() => window.URL.revokeObjectURL(url), 1000);
    } catch (error) {
      console.error("Failed to preview file:", error);
      throw error;
    }
  },
};
