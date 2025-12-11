/**
 * Model Icons and Styling Utilities
 *
 * Provides icon and styling configuration for different LLM models
 */

import { LLM_MODEL_LOGOS } from "../config/constants";

/**
 * Get model icon and styling based on model name
 * @param {string} modelName - The model name (e.g., "qwen-plus", "gpt-4o")
 * @param {string} modelProvider - The model provider (e.g., "OPENAI", "ANTHROPIC")
 * @returns {object} Icon configuration { logoPath, color, bgColor, label, provider }
 */
export function getModelIcon(modelName, modelProvider) {
  if (!modelName) {
    return {
      logoPath: null,
      color: "#666666",
      bgColor: "#f5f5f5",
      label: "Default",
      provider: "Default"
    };
  }

  const name = modelName.toLowerCase();
  const provider = (modelProvider || "").toUpperCase();

  // ========== Priority 1: Model Name Based Detection (Highest Priority) ==========
  // This ensures we infer the correct logo from model name even if provider is OPENAI

  // GLM Models (智谱AI)
  if (name.includes("glm")) {
    return {
      logoPath: LLM_MODEL_LOGOS["Zhipu AI"],
      color: "#4A90E2",
      bgColor: "#E3F2FD",
      label: "GLM-4.6",
      provider: "Zhipu AI"
    };
  }

  // Qwen Models (阿里云/通义千问)
  if (name.includes("qwen")) {
    return {
      logoPath: LLM_MODEL_LOGOS["Alibaba"],
      color: "#FF6A00",
      bgColor: "#FFF3E0",
      label: name.includes("max") ? "Qwen-Max" : name.includes("plus") ? "Qwen-Plus" : "Qwen",
      provider: "Alibaba"
    };
  }

  // DeepSeek Models
  if (name.includes("deepseek")) {
    return {
      logoPath: LLM_MODEL_LOGOS["DeepSeek"],
      color: "#1976D2",
      bgColor: "#E3F2FD",
      label: "DeepSeek-V3",
      provider: "DeepSeek"
    };
  }

  // Moonshot/Kimi Models (月之暗面)
  if (name.includes("moonshot") || name.includes("kimi")) {
    return {
      logoPath: LLM_MODEL_LOGOS["Moonshot"],
      color: "#7B68EE",
      bgColor: "#F3E5F5",
      label: "Kimi-K2",
      provider: "Moonshot"
    };
  }

  // Anthropic Claude Models (check model name first)
  if (name.includes("claude")) {
    return {
      logoPath: LLM_MODEL_LOGOS["Anthropic"],
      color: "#D97706",
      bgColor: "#FEF3C7",
      label: "Claude",
      provider: "Anthropic"
    };
  }

  // Google Gemini Models (check model name first)
  if (name.includes("gemini")) {
    return {
      logoPath: LLM_MODEL_LOGOS["Google"],
      color: "#4285F4",
      bgColor: "#E8F0FE",
      label: "Gemini",
      provider: "Google"
    };
  }

  // OpenAI GPT Models (check model name first)
  if (name.includes("gpt") || name.includes("o1") || name.includes("o2") || name.includes("o3")) {
    return {
      logoPath: LLM_MODEL_LOGOS["OpenAI"],
      color: "#10A37F",
      bgColor: "#E8F5E9",
      label: name.includes("4o") ? "GPT-4o" : name.includes("4.5") ? "GPT-4.5" : name.includes("4") ? "GPT-4" : name.includes("3.5") ? "GPT-3.5" : "OpenAI",
      provider: "OpenAI"
    };
  }

  // ========== Priority 2: Provider Based Detection (Fallback) ==========
  // Only use provider if model name doesn't match any known patterns

  // Anthropic Claude Models (provider fallback)
  if (provider === "ANTHROPIC") {
    return {
      logoPath: LLM_MODEL_LOGOS["Anthropic"],
      color: "#D97706",
      bgColor: "#FEF3C7",
      label: "Claude",
      provider: "Anthropic"
    };
  }

  // Google Gemini Models (provider fallback)
  if (provider === "GOOGLE") {
    return {
      logoPath: LLM_MODEL_LOGOS["Google"],
      color: "#4285F4",
      bgColor: "#E8F0FE",
      label: "Gemini",
      provider: "Google"
    };
  }

  // OpenAI Models (provider fallback - only if model name doesn't match)
  if (provider === "OPENAI") {
    return {
      logoPath: LLM_MODEL_LOGOS["OpenAI"],
      color: "#10A37F",
      bgColor: "#E8F5E9",
      label: "OpenAI",
      provider: "OpenAI"
    };
  }

  // Groq Models
  if (provider === "GROQ") {
    return {
      logoPath: LLM_MODEL_LOGOS["Groq"],
      color: "#DC2626",
      bgColor: "#FEE2E2",
      label: "Groq",
      provider: "Groq"
    };
  }

  // Ollama Models
  if (provider === "OLLAMA") {
    return {
      logoPath: LLM_MODEL_LOGOS["Ollama"],
      color: "#000000",
      bgColor: "#F5F5F5",
      label: "Ollama",
      provider: "Ollama"
    };
  }

  // OpenRouter Models
  if (provider === "OPENROUTER") {
    return {
      logoPath: null,
      color: "#8B5CF6",
      bgColor: "#F5F3FF",
      label: "OpenRouter",
      provider: "OpenRouter"
    };
  }

  // GigaChat Models
  if (provider === "GIGACHAT") {
    return {
      logoPath: null,
      color: "#9333EA",
      bgColor: "#FAF5FF",
      label: "GigaChat",
      provider: "GigaChat"
    };
  }

  // Default fallback
  return {
    logoPath: null,
    color: "#666666",
    bgColor: "#f5f5f5",
    label: modelName.substring(0, 15),
    provider: provider || "Unknown"
  };
}

/**
 * Get short model name for display
 * @param {string} modelName - The full model name
 * @returns {string} Short version of the model name (preserves full version numbers and suffixes)
 */
export function getShortModelName(modelName) {
  if (!modelName) {
    return "N/A";
  }

  const name = modelName.toLowerCase();

  // Helper function to capitalize first letter of each word
  const capitalizeWords = (str) => {
    return str.split(/[-_\s]/).map(word =>
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join("-");
  };

  // GLM - preserve version numbers
  if (name.includes("glm")) {
    // Extract version number if present (e.g., glm-4.6, glm-4.5)
    const versionMatch = name.match(/glm[_-]?(\d+\.\d+)/);
    if (versionMatch) {
      return `GLM-${versionMatch[1]}`;
    }
    return "GLM-4.6"; // Default
  }

  // Qwen - preserve full version and suffixes
  if (name.includes("qwen")) {
    // Match patterns like: qwen3-max-preview, qwen-max, qwen-plus, qwen-flash
    if (name.includes("qwen3-max")) {
      // Extract suffix if present (e.g., -preview)
      const fullMatch = name.match(/qwen3-max[_-]?([a-z0-9-]+)?/);
      if (fullMatch && fullMatch[1]) {
        return `Qwen3-Max-${capitalizeWords(fullMatch[1])}`;
      }
      return "Qwen3-Max";
    }
    if (name.includes("qwen-max")) {
      const fullMatch = name.match(/qwen-max[_-]?([a-z0-9-]+)?/);
      if (fullMatch && fullMatch[1]) {
        return `Qwen-Max-${capitalizeWords(fullMatch[1])}`;
      }
      return "Qwen-Max";
    }
    if (name.includes("qwen-plus")) {
      const fullMatch = name.match(/qwen-plus[_-]?([a-z0-9-]+)?/);
      if (fullMatch && fullMatch[1]) {
        return `Qwen-Plus-${capitalizeWords(fullMatch[1])}`;
      }
      return "Qwen-Plus";
    }
    if (name.includes("qwen-flash")) {
      const fullMatch = name.match(/qwen-flash[_-]?([a-z0-9-]+)?/);
      if (fullMatch && fullMatch[1]) {
        return `Qwen-Flash-${capitalizeWords(fullMatch[1])}`;
      }
      return "Qwen-Flash";
    }
    // Generic qwen with version
    const versionMatch = name.match(/qwen[_-]?(\d+[a-z0-9-]*)?/);
    if (versionMatch && versionMatch[1]) {
      return `Qwen-${capitalizeWords(versionMatch[1])}`;
    }
    return "Qwen";
  }

  // DeepSeek - preserve full version numbers and suffixes
  if (name.includes("deepseek")) {
    // Match patterns like: deepseek-v3.1, deepseek-v3.2-exp, deepseek-v3
    // First try to match with version and suffix
    const fullMatch = name.match(/deepseek[_-]?v?(\d+\.\d+[a-z0-9]*)[_-]?([a-z0-9-]+)?/);
    if (fullMatch) {
      const version = fullMatch[1];
      const suffix = fullMatch[2];
      if (suffix) {
        return `DeepSeek-V${version}-${capitalizeWords(suffix)}`;
      }
      return `DeepSeek-V${version}`;
    }
    // Try to match just version
    const versionMatch = name.match(/deepseek[_-]?v?(\d+\.\d+)/);
    if (versionMatch) {
      return `DeepSeek-V${versionMatch[1]}`;
    }
    // Fallback to generic DeepSeek
    return "DeepSeek";
  }

  // Moonshot/Kimi - preserve full model names
  if (name.includes("moonshot") || name.includes("kimi")) {
    // Match patterns like: moonshot-kimi-k2-instruct, kimi-k2-instruct
    // First check if it contains k2
    if (name.includes("k2")) {
      // Try to extract suffix after k2 (e.g., -instruct)
      const k2Match = name.match(/k2[_-]?([a-z0-9-]+)?/);
      if (k2Match && k2Match[1]) {
        return `Moonshot-Kimi-K2-${capitalizeWords(k2Match[1])}`;
      }
      return "Moonshot-Kimi-K2";
    }
    if (name.includes("kimi")) {
      return "Kimi";
    }
    return "Moonshot";
  }

  // OpenAI - preserve full version numbers
  if (name.includes("gpt") || name.includes("o1") || name.includes("o2") || name.includes("o3")) {
    // Match patterns like: gpt-4o, gpt-4.5, gpt-4, gpt-3.5-turbo
    if (name.includes("gpt-4o")) {
      const suffixMatch = name.match(/gpt-4o[_-]?([a-z0-9-]+)?/);
      if (suffixMatch && suffixMatch[1]) {
        return `GPT-4o-${capitalizeWords(suffixMatch[1])}`;
      }
      return "GPT-4o";
    }
    if (name.includes("gpt-4.5")) {
      const suffixMatch = name.match(/gpt-4\.5[_-]?([a-z0-9-]+)?/);
      if (suffixMatch && suffixMatch[1]) {
        return `GPT-4.5-${capitalizeWords(suffixMatch[1])}`;
      }
      return "GPT-4.5";
    }
    if (name.includes("gpt-4")) {
      const suffixMatch = name.match(/gpt-4[_-]?([a-z0-9-]+)?/);
      if (suffixMatch && suffixMatch[1]) {
        return `GPT-4-${capitalizeWords(suffixMatch[1])}`;
      }
      return "GPT-4";
    }
    if (name.includes("gpt-3.5")) {
      const suffixMatch = name.match(/gpt-3\.5[_-]?([a-z0-9-]+)?/);
      if (suffixMatch && suffixMatch[1]) {
        return `GPT-3.5-${capitalizeWords(suffixMatch[1])}`;
      }
      return "GPT-3.5";
    }
    // O-series models
    if (name.includes("o3")) {
      return "O3";
    }
    if (name.includes("o2")) {
      return "O2";
    }
    if (name.includes("o1")) {
      return "O1";
    }
    return "OpenAI";
  }

  // Claude - preserve full model names
  if (name.includes("claude")) {
    if (name.includes("claude-opus")) {
      const versionMatch = name.match(/claude-opus[_-]?(\d+[a-z0-9-]*)?/);
      if (versionMatch && versionMatch[1]) {
        return `Claude-Opus-${capitalizeWords(versionMatch[1])}`;
      }
      return "Claude-Opus";
    }
    if (name.includes("claude-sonnet")) {
      const versionMatch = name.match(/claude-sonnet[_-]?(\d+[a-z0-9-]*)?/);
      if (versionMatch && versionMatch[1]) {
        return `Claude-Sonnet-${capitalizeWords(versionMatch[1])}`;
      }
      return "Claude-Sonnet";
    }
    if (name.includes("claude-haiku")) {
      const versionMatch = name.match(/claude-haiku[_-]?(\d+[a-z0-9-]*)?/);
      if (versionMatch && versionMatch[1]) {
        return `Claude-Haiku-${capitalizeWords(versionMatch[1])}`;
      }
      return "Claude-Haiku";
    }
    return "Claude";
  }

  // Google Gemini
  if (name.includes("gemini")) {
    const versionMatch = name.match(/gemini[_-]?([a-z0-9.-]+)?/);
    if (versionMatch && versionMatch[1]) {
      return `Gemini-${capitalizeWords(versionMatch[1])}`;
    }
    return "Gemini";
  }

  // If no specific pattern matched, return formatted original name
  // Truncate only if extremely long (over 30 chars)
  if (modelName.length > 30) {
    return capitalizeWords(modelName.substring(0, 27)) + "...";
  }

  // Return formatted original name
  return capitalizeWords(modelName);
}

