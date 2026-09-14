/** E-10: aliquot/pool plan + dest entries are an atomic pair. */

export const ALIQUOT_PLAN_KEY = 'aliquot_pool_plan';
export const ALIQUOT_DEST_KEY = 'aliquots_pools';

export type AliquotPairEntry = {
  entry_type: string;
  name: string;
  description?: string;
  predefined_entry_key?: string;
  sort_order?: number;
  config?: Record<string, unknown>;
  fields?: unknown[];
};

export const ALIQUOT_PLAN_ENTRY: Omit<AliquotPairEntry, 'sort_order'> = {
  entry_type: 'experiment_data',
  name: 'Aliquot / pool plan',
  description: 'Plan amounts; execute creates dest samples',
  predefined_entry_key: ALIQUOT_PLAN_KEY,
  config: {
    method: 'aliquot_by_volume',
    default_dest_sample_type: null,
    default_dest_container_type: null,
  },
  fields: [],
};

export const ALIQUOT_DEST_ENTRY: Omit<AliquotPairEntry, 'sort_order'> = {
  entry_type: 'experiment_sample_data',
  name: 'Aliquots / pools',
  description: 'Post-execute view of resulting samples',
  predefined_entry_key: ALIQUOT_DEST_KEY,
  config: {
    sample_columns: ['client_sample_id', 'sample_type'],
    minted_sample_ids: [],
    populated_after_execute: false,
  },
  fields: [],
};

export const aliquotPairMate = (key?: string | null): string | null => {
  if (key === ALIQUOT_PLAN_KEY) return ALIQUOT_DEST_KEY;
  if (key === ALIQUOT_DEST_KEY) return ALIQUOT_PLAN_KEY;
  return null;
};

export const hasAliquotPair = (entries: Array<{ predefined_entry_key?: string }>): boolean => {
  const keys = new Set(entries.map((e) => e.predefined_entry_key));
  return keys.has(ALIQUOT_PLAN_KEY) || keys.has(ALIQUOT_DEST_KEY);
};

export const appendAliquotPair = <T extends AliquotPairEntry>(entries: T[]): T[] => {
  if (hasAliquotPair(entries)) return entries;
  const start = entries.length;
  return [
    ...entries,
    { ...(ALIQUOT_PLAN_ENTRY as T), sort_order: start },
    { ...(ALIQUOT_DEST_ENTRY as T), sort_order: start + 1 },
  ];
};

export const removeAliquotPairAt = <T extends { predefined_entry_key?: string }>(
  entries: T[],
  index: number,
): T[] => {
  const target = entries[index];
  const mate = aliquotPairMate(target?.predefined_entry_key);
  if (!mate) {
    return entries.filter((_, i) => i !== index);
  }
  return entries.filter(
    (e, i) => i !== index && e.predefined_entry_key !== mate,
  );
};
