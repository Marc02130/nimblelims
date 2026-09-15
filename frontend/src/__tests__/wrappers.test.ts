import {
  WRAPPER_CATALOG,
  wrapperAtCapacity,
  wrapperIdForKey,
  wrapperInstancePresent,
  wrapperMateKey,
} from '../components/experiments/wrappers';

describe('WRAPPER_CATALOG', () => {
  it('pairs aliquot/pool keys and sets cardinality 1', () => {
    const spec = WRAPPER_CATALOG.aliquot_pool;
    expect(spec.keys).toEqual(['aliquot_pool_plan', 'aliquots_pools']);
    expect(spec.cardinality).toBe(1);
    expect(spec.atomicPair).toBe(true);
    expect(spec.mint).toBe(true);
    expect(spec.sourceFrom).toBe('start_cohort');
  });

  it('maps keys to wrappers and mates', () => {
    expect(wrapperIdForKey('aliquot_pool_plan')).toBe('aliquot_pool');
    expect(wrapperMateKey('aliquot_pool_plan')).toBe('aliquots_pools');
    expect(wrapperMateKey('aliquots_pools')).toBe('aliquot_pool_plan');
    expect(wrapperMateKey('experiment_header')).toBeNull();
  });

  it('treats one pair as at capacity', () => {
    const pair = [
      { predefined_entry_key: 'aliquot_pool_plan' },
      { predefined_entry_key: 'aliquots_pools' },
    ];
    expect(wrapperInstancePresent('aliquot_pool', pair)).toBe(true);
    expect(wrapperAtCapacity('aliquot_pool', pair)).toBe(true);
    expect(wrapperAtCapacity('aliquot_pool', [])).toBe(false);
    expect(
      wrapperAtCapacity('experiment_header', [
        { predefined_entry_key: 'experiment_header' },
      ]),
    ).toBe(true);
  });
});
