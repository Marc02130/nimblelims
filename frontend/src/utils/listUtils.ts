/**
 * Utility functions for list management
 */

/**
 * Normalize a display name to a slug format for API access
 * Converts "Sample Status" to "sample_status"
 */
export const normalizeListName = (displayName: string): string => {
  return displayName
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
};

/**
 * Convert a slug back to a display name
 * Converts "sample_status" to "Sample Status"
 */
export const slugToDisplayName = (slug: string): string => {
  return slug
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

