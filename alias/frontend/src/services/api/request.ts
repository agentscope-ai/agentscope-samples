import axios, { AxiosInstance, AxiosRequestConfig } from "axios";
import { ApiResponse } from "../types/conversation";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const USER_PROFILING_URL =
  import.meta.env.VITE_USER_PROFILING_API_URL || "http://localhost:6380";
const MAX_RETRIES = Number(import.meta.env.VITE_MAX_RETRIES) || 3;
const RETRY_DELAY = Number(import.meta.env.VITE_RETRY_DELAY) || 1000;

let onDoneCallback:
  | ((conversationId: string, taskId: string, messageId: string) => void)
  | null = null;
export const setOnDoneCallback = (
  callback: (conversationId: string, taskId: string, messageId: string) => void,
) => {
  onDoneCallback = callback;
};

const FIXED_ACCESS_TOKEN =
  import.meta.env.VITE_API_ACCESS_TOKEN || import.meta.env.VITE_API_TOKEN;
const FIXED_REFRESH_TOKEN = import.meta.env.VITE_API_REFRESH_TOKEN;

class Request {
  private instance: AxiosInstance;

  constructor() {
    this.instance = axios.create({
      baseURL: BASE_URL,
      timeout: 60000,
      headers: {
        "Content-Type": "application/json",
      },
    });

    this.setupInterceptors();
  }
  private getUserProfilingUrl(url: string): string {
    const USER_PROFILING_PATH = "/alias_memory_service/user_profiling";
    if (url.includes(USER_PROFILING_PATH)) {
      return url.startsWith("/")
        ? `${USER_PROFILING_URL}${url}`
        : `${USER_PROFILING_URL}/${url}`;
    }
    return url;
  }

  private getAccessToken(): string {
    return localStorage.getItem("access_token") || FIXED_ACCESS_TOKEN || "";
  }

  private async refreshToken() {
    try {
      const refreshToken =
        localStorage.getItem("refresh_token") || FIXED_REFRESH_TOKEN;
      const response = await axios.post(
        `${BASE_URL}/api/v1/refresh-token`,
        {
          refresh_token: refreshToken,
        },
        {
          headers: {
            "Content-Type": "application/json",
          },
        },
      );

      const { payload } = response.data;
      localStorage.setItem("access_token", payload.access_token);
      localStorage.setItem("refresh_token", payload.refresh_token);
      return payload.access_token;
    } catch (error) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      throw error;
    }
  }

  private setupInterceptors() {
    this.instance.interceptors.request.use(
      (config) => {
        const token = this.getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      },
    );

    this.instance.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            await this.refreshToken();
            return this.instance(originalRequest);
          } catch (refreshError) {
            throw refreshError;
          }
        }
        return Promise.reject(error);
      },
    );
  }

  private async retryRequest<T>(
    requestFn: () => Promise<T>,
    retries: number = MAX_RETRIES,
  ): Promise<T> {
    try {
      return await requestFn();
    } catch (error: any) {
      if (retries > 0 && error.code === "ECONNABORTED") {
        await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY));
        return this.retryRequest(requestFn, retries - 1);
      }
      throw error;
    }
  }
  async get<T>(
    url: string,
    config?: AxiosRequestConfig,
  ): Promise<ApiResponse<T>> {
    return this.retryRequest(async () => {
      const response = await this.instance.get<ApiResponse<T>>(url, config);
      return response.data;
    });
  }

  async post<T>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig,
  ): Promise<ApiResponse<T>> {
    return this.retryRequest(async () => {
      const baseUrl = this.getUserProfilingUrl(url);
      const response = await this.instance.post<ApiResponse<T>>(
        baseUrl,
        data,
        config,
      );
      return response.data;
    }, 0); // no retry
  }

  async put<T>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig,
  ): Promise<ApiResponse<T>> {
    return this.retryRequest(async () => {
      const response = await this.instance.put<ApiResponse<T>>(
        url,
        data,
        config,
      );
      return response.data;
    }, 0); // no retry
  }

  async delete<T>(
    url: string,
    config?: AxiosRequestConfig,
  ): Promise<ApiResponse<T>> {
    return this.retryRequest(async () => {
      const response = await this.instance.delete<ApiResponse<T>>(url, config);
      return response.data;
    });
  }

  async stream(
    url: string,
    onMessage: (data: any) => void,
    onError?: (error: any) => void,
    body?: any,
    abortController?: AbortController,
  ): Promise<void> {
    const tryStream = async (retries: number = 0) => {
      try {
        const response = await fetch(`${BASE_URL}${url}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${this.getAccessToken()}`,
          },
          body: body ? JSON.stringify(body) : undefined,
          signal: abortController?.signal,
        });

        if (response.status === 401) {
          await this.refreshToken();
          return this.stream(url, onMessage, onError, body, abortController);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No reader available");

        let buffer = "";

        let task_id = "";
        let conversation_id = "";
        let message_id = "";

        while (true) {
          if (abortController?.signal.aborted) {
            reader.cancel();
            return;
          }

          const { done, value } = await reader.read();
          if (done) break;

          const text = new TextDecoder().decode(value);
          buffer += text;

          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(5).trim();
              if (data === "[DONE]") {
                if (conversation_id && onDoneCallback) {
                  onDoneCallback(conversation_id, task_id, message_id);
                }
                return;
              }
              try {
                const parsed = JSON.parse(data);
                task_id = parsed?.task_id || "";
                conversation_id = parsed?.conversation_id || "";
                message_id = parsed?.message_id || "";
                if (parsed?.code && parsed?.message) {
                  onError?.(parsed);
                  return;
                }
                onMessage(parsed);
              } catch (e: any) {
                console.error("JSON.parse error:", {
                  originalData: data,
                  error: e,
                });

                const errorLog = {
                  timestamp: new Date().toISOString(),
                  data: data,
                  error: e?.message,
                };
                localStorage.setItem(
                  "parse-error-" + Date.now(),
                  JSON.stringify(errorLog),
                );

                onError?.(e);
              }
            }
          }
        }
        if (buffer.length > 0 && buffer.startsWith("data: ")) {
          const data = buffer.slice(5);
          if (data !== "[DONE]") {
            try {
              const parsed = JSON.parse(data);
              if (parsed?.code && parsed?.message) {
                onError?.(parsed);
              } else {
                onMessage(parsed);
              }
            } catch (e) {
              console.error("Final buffer JSON.parse error:", {
                originalData: data,
                error: e,
              });
              onError?.(e);
            }
          }
        }
      } catch (error: any) {
        if (error.name === "AbortError" || abortController?.signal.aborted) {
          return;
        }
        if (retries > 0) {
          await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY));
          return tryStream(retries - 1);
        }
        onError?.(error);
        throw error;
      }
    };

    return tryStream();
  }
}

export const request = new Request();
