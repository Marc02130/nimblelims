/** Aliquot/pool wrapper (WRAPPER_CATALOG.aliquot_pool): atomic pair, cardinality 1. */

import {
  WRAPPER_CATALOG,
  wrapperAtCapacity,
  wrapperMateKey,
} from './wrappers';

export const ALIQUOT_PLAN_KEY = WRAPPER_CATALOG.aliquot_pool.keys[0];
export const ALIQUOT_DEST_KEY = WRAPPER_CATALOG.aliquot_pool.keys[1];

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

export const aliquotPairMate = (key?: string | null): string | null =>
  wrapperMateKey(key);

export const hasAliquotPair = (
  entries: Array<{ predefined_entry_key?: string | null }>,
): boolean => wrapperAtCapacity('aliquot_pool', entries);

export const appendAliquotPair = <T extends AliquotPairEntry>(entries: T[]): T[] => {
  if (wrapperAtCapacity('aliquot_pool', entries)) return entries;
  const start = entries.length;
  return [
    ...entries,
    { ...(ALIQUOT_PLAN_ENTRY as T), sort_order: start },
    { ...(ALIQUOT_DEST_ENTRY as T), sort_order: start + 1 },
  ];
};

export const removeAliquotPairAt = <T extends { predefined_entry_key?: string | null }>(
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
