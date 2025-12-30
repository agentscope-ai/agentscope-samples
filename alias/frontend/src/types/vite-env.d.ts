/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_TITLE?: string;
  readonly VITE_API_URL?: string;
  readonly VITE_USER_PROFILING_API_URL?: string;
  readonly VITE_MAX_RETRIES?: string;
  readonly VITE_RETRY_DELAY?: string;
  readonly VITE_API_ACCESS_TOKEN?: string;
  readonly VITE_API_TOKEN?: string;
  readonly VITE_API_REFRESH_TOKEN?: string;
  readonly MODE: string;
  readonly DEV: boolean;
  readonly PROD: boolean;
  readonly SSR: boolean;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
  readonly hot: {
    accept(): void;
    dispose(cb: (data: any) => void): void;
    data: any;
  };
}
