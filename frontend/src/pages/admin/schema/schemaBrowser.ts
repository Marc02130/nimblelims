/**
 * Pure helpers for the Schema table browser. No React, no API.
 *
 * Product locks encoded here:
 * - Every registered table is **Lab** unless it is a system reference table (**System**).
 * - System columns (id, timestamps, created-by, relationship foreign keys, `list_id`)
 *   are not editable and not removable. Reflected built-ins are described, not edited.
 * - A field is a column on a table; there is no Custom Fields area.
 */

export type TableKind = 'core' | 'ui' | 'system';
export type TableCategory = 'lab' | 'system';
export type Cardinality = 'one_to_many' | 'one_to_one';

export interface SchemaTableRow {
  id: string;
  display_name: string;
  physical_name: string;
  kind: TableKind | string;
  category?: TableCategory | string;
  status: string;
  column_count: number;
  relation_count?: number;
  can_add_columns?: boolean;
  can_remove?: boolean;
}

export interface SchemaColumnRow {
  id: string;
  table_id: string;
  display_name: string;
  physical_name: string;
  data_type: string;
  pg_type?: string | null;
  nullable: boolean;
  list_id?: string | null;
  sop_hint?: string | null;
  status: string;
  is_platform: boolean;
  is_identity: boolean;
  is_fk?: boolean;
  fk_table?: string | null;
  is_unique?: boolean;
  origin?: 'ui' | 'reflected' | string;
  is_system?: boolean;
  system_reason?: string | null;
  editable?: boolean;
}

export interface SchemaRelationRow {
  id: string;
  display_name: string;
  from_table_id: string;
  from_table_name?: string | null;
  from_physical_name?: string | null;
  to_table_id: string;
  to_table_name?: string | null;
  to_physical_name?: string | null;
  fk_column_id: string;
  fk_column_name?: string | null;
  fk_physical_name?: string | null;
  cardinality: Cardinality | string;
  status: string;
}

export interface TableKeyRow {
  column_id: string;
  column_name: string;
  physical_name: string;
  fk_table?: string | null;
  fk_table_id?: string | null;
  fk_table_name?: string | null;
  is_unique?: boolean;
}

export interface TableLinks {
  table_id: string;
  keys: TableKeyRow[];
  children: SchemaRelationRow[];
  parents: SchemaRelationRow[];
}

export const CARDINALITY_LABEL: Record<string, string> = {
  one_to_many: 'One to many',
  one_to_one: 'One to one',
};

export const SYSTEM_REASON_COPY: Record<string, string> = {
  system_table: 'System reference table — read-only here.',
  platform: 'Platform field (id, timestamps, created-by, active).',
  identity: 'Identity/lineage field.',
  relationship_key: 'Relationship key — a real foreign key.',
};

/** Badge for a table: Lab vs System. UI-created tables are Lab. */
export function tableCategory(row: Pick<SchemaTableRow, 'kind' | 'category'>): TableCategory {
  if (row.category === 'system' || row.category === 'lab') return row.category;
  return row.kind === 'system' ? 'system' : 'lab';
}

export function tableCategoryLabel(row: Pick<SchemaTableRow, 'kind' | 'category'>): string {
  return tableCategory(row) === 'system' ? 'System' : 'Lab';
}

/** Where the table came from, as a scientist would read it. */
export function tableSourceLabel(row: Pick<SchemaTableRow, 'kind'>): string {
  if (row.kind === 'ui') return 'Created here';
  if (row.kind === 'system') return 'Reference';
  return 'Built in';
}

/**
 * A column is locked when the API says so, or (older payloads) when it is a
 * platform / identity / relationship-key column. `list_entries` keys are list
 * bindings and stay lab columns.
 */
export function isSystemColumn(col: SchemaColumnRow): boolean {
  if (typeof col.is_system === 'boolean') return col.is_system;
  if (col.is_platform || col.is_identity) return true;
  if (col.is_fk && col.fk_table && col.fk_table !== 'list_entries') return true;
  return false;
}

/** Only UI-added lab columns get Deprecate / Drop. Reflected built-ins never do. */
export function isColumnEditable(col: SchemaColumnRow): boolean {
  if (typeof col.editable === 'boolean') return col.editable;
  if (isSystemColumn(col)) return false;
  return (col.origin ?? 'ui') === 'ui';
}

export function columnScopeLabel(col: SchemaColumnRow): 'System' | 'Lab' {
  return isSystemColumn(col) ? 'System' : 'Lab';
}

export function columnLockReason(col: SchemaColumnRow): string | null {
  if (isSystemColumn(col)) {
    return SYSTEM_REASON_COPY[col.system_reason ?? ''] ?? 'System field — not editable.';
  }
  if (!isColumnEditable(col)) {
    return 'Built-in field owned by migrations. Described here, not edited.';
  }
  return null;
}

/** Lab sentence for the Relations preview. */
export function relationSentence(
  cardinality: string,
  parentName: string,
  childName: string,
  keyName: string,
): string {
  if (cardinality === 'one_to_one') {
    return `Each ${childName} points at one ${parentName} through ${keyName}, and only one ${childName} may point at that record. Stored as a real unique key on ${childName}.`;
  }
  return `Each ${childName} points at one ${parentName} through ${keyName}. ${parentName} lists its ${childName}. Stored as a real key on ${childName}.`;
}

/** Candidate key columns on a child for a chosen parent: real FKs that point at it. */
export function keyColumnsFor(
  columns: SchemaColumnRow[],
  parentPhysicalName: string | undefined,
): SchemaColumnRow[] {
  if (!parentPhysicalName) return [];
  return columns.filter((c) => c.is_fk && c.fk_table === parentPhysicalName);
}

/** Sort: Lab tables first (sample-centric spine), System reference tables after — matches the API order. */
export function sortTables<T extends Pick<SchemaTableRow, 'kind' | 'category' | 'display_name'>>(
  rows: T[],
): T[] {
  return [...rows].sort((a, b) => {
    const ca = tableCategory(a) === 'system' ? 1 : 0;
    const cb = tableCategory(b) === 'system' ? 1 : 0;
    if (ca !== cb) return ca - cb;
    return a.display_name.localeCompare(b.display_name);
  });
}
