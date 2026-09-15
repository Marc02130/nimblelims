import {
  ALIQUOT_DEST_KEY,
  ALIQUOT_PLAN_KEY,
  appendAliquotPair,
  hasAliquotPair,
  removeAliquotPairAt,
} from '../components/experiments/aliquotPair';

describe('aliquotPair', () => {
  it('appends plan and dest together', () => {
    const next = appendAliquotPair([{ name: 'Header', entry_type: 'experiment_data' }]);
    expect(next).toHaveLength(3);
    expect(next.map((e) => e.predefined_entry_key)).toEqual([
      undefined,
      ALIQUOT_PLAN_KEY,
      ALIQUOT_DEST_KEY,
    ]);
  });

  it('does not add a second pair', () => {
    const once = appendAliquotPair([]);
    expect(appendAliquotPair(once)).toHaveLength(2);
    expect(hasAliquotPair(once)).toBe(true);
  });

  it('removes both when either half is deleted', () => {
    const pair = appendAliquotPair([]);
    expect(removeAliquotPairAt(pair, 0)).toHaveLength(0);
    expect(removeAliquotPairAt(pair, 1)).toHaveLength(0);
  });

  it('allows a new pair after the previous pair is gone', () => {
    const gone = removeAliquotPairAt(appendAliquotPair([]), 0);
    expect(hasAliquotPair(gone)).toBe(false);
    expect(appendAliquotPair(gone)).toHaveLength(2);
  });
});
