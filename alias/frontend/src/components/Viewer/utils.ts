export const getFileType = (extension: string) => {
  switch (extension.toLowerCase().replace(".", "")) {
    case "html":
    case "htm":
      return "html";
    case "md":
    case "markdown":
      return "markdown";
    case "txt":
      return "text";
    case "json":
      return "json";
    case "csv":
      return "csv";
    case "xml":
      return "xml";
    case "yaml":
    case "yml":
      return "yaml";
    case "log":
      return "log";
    case "pdf":
      return "pdf";
    case "png":
    case "jpg":
    case "jpeg":
    case "gif":
    case "webp":
      return "image";
    case "diff":
    case "patch":
      return "diff";
    case "chart":
      return "chart";
    default:
      return "text";
  }
};
export const languageMap: { [key: string]: string } = {
  js: "javascript",
  jsx: "jsx",
  ts: "typescript",
  tsx: "typescript",
  py: "python",
  python: "python",
  rb: "ruby",
  java: "java",
  cpp: "cpp",
  c: "c",
  cs: "csharp",
  go: "go",
  rs: "rust",
  php: "php",
  html: "html",
  css: "css",
  scss: "scss",
  sql: "sql",
  yaml: "yaml",
  yml: "yaml",
  json: "json",
  xml: "xml",
  md: "markdown",
  sh: "bash",
  bash: "bash",
  diff: "diff",
};
