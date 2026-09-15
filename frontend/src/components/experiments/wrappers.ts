/**
 * Predefined entry wrappers. Cardinality, pairing, and mint are catalog
 * properties — not if-aliquot branches. Aliquot/pool is the first mint proof
 * (cardinality 1). n-instances: ideas/aliquot-pool-multiple-pairs.md
 */

export type WrapperId = 'aliquot_pool' | 'experiment_header' | 'samples';

export type WrapperSpec = {
  id: WrapperId;
  keys: readonly string[];
  cardinality: 1;
  atomicPair: boolean;
  mint: boolean;
  sourceFrom?: 'start_cohort';
  addLabel: string;
};

export const WRAPPER_CATALOG: Record<WrapperId, WrapperSpec> = {
  aliquot_pool: {
    id: 'aliquot_pool',
    keys: ['aliquot_pool_plan', 'aliquots_pools'],
    cardinality: 1,
    atomicPair: true,
    mint: true,
    sourceFrom: 'start_cohort',
    addLabel: 'Aliquot/pool',
  },
  experiment_header: {
    id: 'experiment_header',
    keys: ['experiment_header'],
    cardinality: 1,
    atomicPair: false,
    mint: false,
    addLabel: 'Header',
  },
  samples: {
    id: 'samples',
    keys: ['samples'],
    cardinality: 1,
    atomicPair: false,
    mint: false,
    addLabel: 'Samples',
  },
};

const KEY_TO_WRAPPER: Record<string, WrapperId> = Object.fromEntries(
  Object.values(WRAPPER_CATALOG).flatMap((spec) =>
    spec.keys.map((key) => [key, spec.id]),
  ),
) as Record<string, WrapperId>;

export const wrapperIdForKey = (key?: string | null): WrapperId | null => {
  if (!key) return null;
  return KEY_TO_WRAPPER[key] ?? null;
};

export const wrapperMateKey = (key?: string | null): string | null => {
  const id = wrapperIdForKey(key);
  if (!id) return null;
  const spec = WRAPPER_CATALOG[id];
  if (!spec.atomicPair || spec.keys.length !== 2 || !key) return null;
  if (!spec.keys.includes(key)) return null;
  return spec.keys[0] === key ? spec.keys[1] : spec.keys[0];
};

export const wrapperInstancePresent = (
  wrapperId: WrapperId,
  entries: Array<{ predefined_entry_key?: string | null }>,
): boolean => {
  const keys = new Set(entries.map((e) => e.predefined_entry_key));
  return WRAPPER_CATALOG[wrapperId].keys.some((k) => keys.has(k));
};

export const wrapperAtCapacity = (
  wrapperId: WrapperId,
  entries: Array<{ predefined_entry_key?: string | null }>,
): boolean => {
  const spec = WRAPPER_CATALOG[wrapperId];
  const counts: Record<string, number> = {};
  for (const e of entries) {
    const k = e.predefined_entry_key;
    if (!k) continue;
    counts[k] = (counts[k] || 0) + 1;
  }
  return spec.keys.some((k) => (counts[k] || 0) >= spec.cardinality);
};
