// Common response interface
export interface ApiResponse<T> {
  code: number;
  data: T;
  message: string;
}

// AI conversation related interface
export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  type: "text" | "code" | "image" | "mindmap";
}

// AI solution related interface
export interface Solution {
  id: string;
  title: string;
  description: string;
  steps: Array<{
    id: string;
    title: string;
    content: string;
    status: "pending" | "in-process" | "completed";
  }>;
}

// User settings interface
export interface UserSettings {
  theme: "light" | "dark" | "system";
  language: "zh" | "en";
  fontSize: number;
}
