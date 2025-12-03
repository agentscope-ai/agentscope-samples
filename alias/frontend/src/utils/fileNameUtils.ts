/**
 * Get filename from full path
 */
export const getBaseName = (filename: string): string =>
  filename.split("/").pop() || filename;

/**
 * Generate unique filename, handling duplicate files
 * @param existingFiles Existing file list
 * @param originalName Original filename
 * @returns Processed unique filename
 */
export const getUniqueFileName = (
  existingFiles: string[],
  originalName: string,
): string => {
  // Ensure existingFiles is an array and not empty
  if (!Array.isArray(existingFiles) || existingFiles.length === 0) {
    return originalName;
  }

  // Get pure filename (remove path)
  const baseNames = existingFiles.map((file) => getBaseName(file));

  // Separate filename and extension
  const lastDotIndex = originalName.lastIndexOf(".");
  const ext = lastDotIndex > -1 ? originalName.substring(lastDotIndex) : "";
  const nameWithoutExt =
    lastDotIndex > -1 ? originalName.substring(0, lastDotIndex) : originalName;

  // If filename doesn't exist, return original filename directly
  if (
    !baseNames.some((name) => name.toLowerCase() === originalName.toLowerCase())
  ) {
    return originalName;
  }

  // Create regex to match base filename and possible sequence number
  // Example: "example.txt" will match "example.txt", "example(1).txt", "example(2).txt", etc.
  const escapeRegExp = (string: string) =>
    string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const baseNameWithoutExt = escapeRegExp(nameWithoutExt);
  const baseNamePattern = new RegExp(
    `^${baseNameWithoutExt}(?:\\((\\d+)\\))?${escapeRegExp(ext)}$`,
    "i",
  );

  // Find all matching filenames and their sequence numbers
  const numbers = baseNames
    .map((name) => {
      const match = name.match(baseNamePattern);
      if (match) {
        // If no sequence number, return 0; otherwise return sequence number
        return match[1] ? parseInt(match[1], 10) : 0;
      }
      return -1;
    })
    .filter((num) => num >= 0);

  // If no sequence numbers found, start from 1
  if (numbers.length === 0) {
    return `${nameWithoutExt}(1)${ext}`;
  }

  // Find maximum sequence number and add 1
  const nextNumber = Math.max(...numbers) + 1;
  return `${nameWithoutExt}(${nextNumber})${ext}`;
};

/**
 * Save file IDs to local storage
 */
export const saveFileIds = (
  storageKey: string,
  conversationId: string,
  fileIds: string[],
): void => {
  const key = `${storageKey}_${conversationId}`;
  localStorage.setItem(key, JSON.stringify(fileIds));
};

/**
 * Get file IDs from local storage
 */
export const getStoredFileIds = (
  storageKey: string,
  conversationId: string,
): string[] => {
  const key = `${storageKey}_${conversationId}`;
  const storedIds = localStorage.getItem(key);
  return storedIds ? JSON.parse(storedIds) : [];
};

/**
 * Remove saved file IDs
 */
export const removeFileIds = (
  storageKey: string,
  conversationId: string,
): void => {
  const key = `${storageKey}_${conversationId}`;
  localStorage.removeItem(key);
};

export const formatFileSize = (size: number) => {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  if (size < 1024 * 1024 * 1024)
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  return `${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`;
};
