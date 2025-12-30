/**
 * Environment variables configuration
 * Unified management of all environment variables, providing type safety and default values
 */

/**
 * Get environment variable value, return default value if it doesn't exist
 */
function getEnv(key: string, defaultValue: string = ""): string {
  return import.meta.env[key] || defaultValue;
}

/**
 * Get number type environment variable
 */
function getEnvNumber(key: string, defaultValue: number): number {
  const value = import.meta.env[key];
  if (value === undefined || value === "") {
    return defaultValue;
  }
  const num = Number(value);
  return isNaN(num) ? defaultValue : num;
}

/**
 * Environment configuration object
 */
export const env = {
  // Application basic configuration
  appTitle: getEnv("VITE_APP_TITLE", "Alias Frontend"),

  // API configuration
  // Must be set in production environment, has default value in development
  apiUrl: (() => {
    const value = import.meta.env.VITE_API_URL;
    if (import.meta.env.PROD) {
      // Production environment: must be set, cannot be empty
      if (!value || value.trim() === "") {
        console.error(
          "Error: VITE_API_URL environment variable must be set in production environment",
        );
        return "";
      }
      return value;
    }
    // Development environment: has default value
    return value || "http://localhost:8000";
  })(),
  userProfilingApiUrl: (() => {
    const value = import.meta.env.VITE_USER_PROFILING_API_URL;
    if (import.meta.env.PROD) {
      // Production environment: must be set, cannot be empty
      if (!value || value.trim() === "") {
        console.error(
          "Error: VITE_USER_PROFILING_API_URL environment variable must be set in production environment",
        );
        return "";
      }
      return value;
    }
    // Development environment: has default value
    return value || "http://localhost:6380";
  })(),

  // Request retry configuration
  maxRetries: getEnvNumber("VITE_MAX_RETRIES", 3),
  retryDelay: getEnvNumber("VITE_RETRY_DELAY", 1000),

  // Token configuration
  apiAccessToken: getEnv("VITE_API_ACCESS_TOKEN") || getEnv("VITE_API_TOKEN"),
  apiRefreshToken: getEnv("VITE_API_REFRESH_TOKEN"),

  // Environment identification
  mode: import.meta.env.MODE,
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
  isSSR: import.meta.env.SSR,
} as const;

/**
 * Development environment configuration
 */
export const devConfig = {
  apiUrl: "http://localhost:8000",
  userProfilingApiUrl: "http://localhost:6380",
  maxRetries: 3,
  retryDelay: 1000,
} as const;

/**
 * Production environment configuration
 * Production environment must be set via environment variables, no default values provided to ensure clear configuration
 */
export const prodConfig = {
  apiUrl: getEnv("VITE_API_URL", ""),
  userProfilingApiUrl: getEnv("VITE_USER_PROFILING_API_URL", ""),
  maxRetries: getEnvNumber("VITE_MAX_RETRIES", 3),
  retryDelay: getEnvNumber("VITE_RETRY_DELAY", 1000),
} as const;

/**
 * Get configuration based on environment
 * Production environment must set VITE_API_URL and VITE_USER_PROFILING_API_URL
 */
export function getConfig() {
  if (env.isProd) {
    // Production environment check required configuration
    if (!env.apiUrl || env.apiUrl.trim() === "") {
      console.warn(
        "Warning: VITE_API_URL is not set for production environment, please check .env.production file or environment variables",
      );
    }
    if (!env.userProfilingApiUrl || env.userProfilingApiUrl.trim() === "") {
      console.warn(
        "Warning: VITE_USER_PROFILING_API_URL is not set for production environment, please check .env.production file or environment variables",
      );
    }
    return {
      ...prodConfig,
      // Use values from env (already validated), if empty use prodConfig (may also be empty)
      apiUrl: env.apiUrl || prodConfig.apiUrl,
      userProfilingApiUrl: env.userProfilingApiUrl || prodConfig.userProfilingApiUrl,
    };
  }
  return {
    ...devConfig,
    // Development environment: prioritize values from env, otherwise use defaults
    apiUrl: env.apiUrl || devConfig.apiUrl,
    userProfilingApiUrl: env.userProfilingApiUrl || devConfig.userProfilingApiUrl,
  };
}

/**
 * Validate production environment configuration
 * Call at application startup to ensure complete production environment configuration
 */
export function validateProdConfig(): void {
  if (env.isProd) {
    const missing: string[] = [];
    if (!env.apiUrl) {
      missing.push("VITE_API_URL");
    }
    if (!env.userProfilingApiUrl) {
      missing.push("VITE_USER_PROFILING_API_URL");
    }
    if (missing.length > 0) {
      console.error(
        `Missing production environment configuration: ${missing.join(", ")}. Please set these environment variables.`,
      );
    }
  }
}

export default env;