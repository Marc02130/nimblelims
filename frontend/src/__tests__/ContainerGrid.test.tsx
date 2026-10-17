import { containerFromBatchMember } from '../components/batches/ContainerGrid';

describe('containerFromBatchMember', () => {
  test('reads id, row, and column from the nested container', () => {
    const row = containerFromBatchMember({
      batch_id: 'batch-1',
      container_id: 'container-1',
      position: 'A1',
      container: {
        id: 'container-1',
        name: 'Tube A',
        row: 2,
        column: 3,
        type_id: 'type-1',
      },
    });

    expect(row.id).toBe('container-1');
    expect(row.row).toBe(2);
    expect(row.column).toBe(3);
    expect(row.name).toBe('Tube A');
    expect(row.type_id).toBe('type-1');
  });

  test('reads a flat batch row that already carries id, row, and column', () => {
    const row = containerFromBatchMember({
      id: 'container-2',
      container_id: 'container-2',
      name: 'Tube B',
      row: 1,
      column: 4,
      type_id: 'type-2',
    });

    expect(row.id).toBe('container-2');
    expect(row.row).toBe(1);
    expect(row.column).toBe(4);
  });

  test('keeps a zero coordinate so validation can reject it', () => {
    const row = containerFromBatchMember({
      container_id: 'container-3',
      row: 0,
      column: 0,
    });

    expect(row.id).toBe('container-3');
    expect(row.row).toBe(0);
    expect(row.column).toBe(0);
  });
});
