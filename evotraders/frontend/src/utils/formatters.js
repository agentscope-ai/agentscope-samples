/**
 * Formatting utility functions
 */

/**
 * Format time from timestamp
 */
export function formatTime(ts) {
  try {
    const d = new Date(ts);
    return d.toLocaleString([], {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit"
    });
  } catch {
    return "";
  }
}

/**
 * Format date and time from timestamp
 */
export function formatDateTime(ts) {
  try {
    const d = new Date(ts);
    const date = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    const time = d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
    return `${date} ${time}`;
  } catch {
    return "";
  }
}

/**
 * Format number with commas (no decimals)
 */
export function formatNumber(num) {
  if (!isFinite(num)) {
    return "-";
  }
  return Math.abs(num).toLocaleString(undefined, { maximumFractionDigits: 0 });
}

/**
 * Format full number with commas for Y-axis
 */
export function formatFullNumber(num) {
  if (!isFinite(num)) {
    return "-";
  }
  return num.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

/**
 * Format ticker price with appropriate decimal places
 */
export function formatTickerPrice(price) {
  if (!isFinite(price)) {
    return "-";
  }
  if (price >= 1000) {
    return price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  } else if (price >= 1) {
    return price.toFixed(2);
  } else {
    return price.toFixed(4);
  }
}

/**
 * Calculate duration between two timestamps
 */
export function calculateDuration(start, end) {
  const diff = end - start;
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) {
    return `${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins}m`;
}

