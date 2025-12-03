/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_TITLE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
  readonly hot: {
    accept(): void;
    dispose(cb: (data: any) => void): void;
    data: any;
  };
}
