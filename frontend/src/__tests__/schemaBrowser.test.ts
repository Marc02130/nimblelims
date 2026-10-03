import {
  columnLockReason,
  isColumnEditable,
  isSystemColumn,
  keyColumnsFor,
  relationSentence,
  sortTables,
  tableCategory,
  tableCategoryLabel,
  tableSourceLabel,
  SchemaColumnRow,
} from '../pages/admin/schema/schemaBrowser';

const col = (over: Partial<SchemaColumnRow>): SchemaColumnRow => ({
  id: 'c',
  table_id: 't',
  display_name: 'Field',
  physical_name: 'field',
  data_type: 'text',
  nullable: true,
  status: 'active',
  is_platform: false,
  is_identity: false,
  ...over,
});

describe('schemaBrowser table badges', () => {
  it('badges every registered table Lab unless it is a system reference table', () => {
    expect(tableCategory({ kind: 'core' })).toBe('lab');
    expect(tableCategory({ kind: 'ui' })).toBe('lab');
    expect(tableCategory({ kind: 'system' })).toBe('system');
    expect(tableCategoryLabel({ kind: 'system', category: 'system' })).toBe('System');
    expect(tableCategoryLabel({ kind: 'core', category: 'lab' })).toBe('Lab');
  });

  it('prefers the API category when present', () => {
    expect(tableCategory({ kind: 'core', category: 'system' })).toBe('system');
  });

  it('names the source in lab words', () => {
    expect(tableSourceLabel({ kind: 'ui' })).toBe('Created here');
    expect(tableSourceLabel({ kind: 'system' })).toBe('Reference');
    expect(tableSourceLabel({ kind: 'core' })).toBe('Built in');
  });

  it('lists lab tables first, then system reference tables, each alphabetically', () => {
    const sorted = sortTables([
      { kind: 'system', display_name: 'Units' },
      { kind: 'core', display_name: 'Tests' },
      { kind: 'system', display_name: 'Lists' },
      { kind: 'ui', display_name: 'Lot Notes' },
      { kind: 'core', display_name: 'Samples' },
    ]);
    expect(sorted.map((t) => t.display_name)).toEqual(['Lot Notes', 'Samples', 'Tests', 'Lists', 'Units']);
  });
});

describe('schemaBrowser system columns', () => {
  it('locks id, timestamps, created-by, relationship keys and list_id', () => {
    expect(isSystemColumn(col({ physical_name: 'id', is_platform: true }))).toBe(true);
    expect(isSystemColumn(col({ physical_name: 'created_at', is_platform: true }))).toBe(true);
    expect(isSystemColumn(col({ physical_name: 'created_by', is_platform: true, is_fk: true, fk_table: 'users' }))).toBe(true);
    expect(isSystemColumn(col({ physical_name: 'project_id', is_fk: true, fk_table: 'projects' }))).toBe(true);
    expect(isSystemColumn(col({ physical_name: 'list_id', is_fk: true, fk_table: 'lists' }))).toBe(true);
    expect(isSystemColumn(col({ physical_name: 'name', is_identity: true }))).toBe(true);
  });

  it('keeps list bindings and plain lab columns editable', () => {
    const listBound = col({ physical_name: 'colour', data_type: 'list', is_fk: true, fk_table: 'list_entries', origin: 'ui' });
    expect(isSystemColumn(listBound)).toBe(false);
    expect(isColumnEditable(listBound)).toBe(true);
    expect(isColumnEditable(col({ physical_name: 'lab_note', origin: 'ui' }))).toBe(true);
  });

  it('trusts the API flags when present', () => {
    expect(isSystemColumn(col({ is_system: true, system_reason: 'relationship_key' }))).toBe(true);
    expect(isColumnEditable(col({ is_system: false, editable: false, origin: 'reflected' }))).toBe(false);
  });

  it('never offers Deprecate / Drop on system or reflected built-in columns', () => {
    expect(isColumnEditable(col({ physical_name: 'id', is_platform: true }))).toBe(false);
    expect(isColumnEditable(col({ physical_name: 'sample_id', is_fk: true, fk_table: 'samples' }))).toBe(false);
    expect(isColumnEditable(col({ physical_name: 'description', origin: 'reflected' }))).toBe(false);
  });

  it('explains the lock', () => {
    expect(columnLockReason(col({ is_system: true, system_reason: 'platform' }))).toMatch(/Platform field/);
    expect(columnLockReason(col({ is_system: true, system_reason: 'relationship_key' }))).toMatch(/real foreign key/);
    expect(columnLockReason(col({ is_system: false, editable: false, origin: 'reflected' }))).toMatch(/migrations/);
    expect(columnLockReason(col({ is_system: false, editable: true, origin: 'ui' }))).toBeNull();
  });
});

describe('schemaBrowser relations', () => {
  it('offers only real foreign keys that point at the chosen parent', () => {
    const cols = [
      col({ id: 'a', physical_name: 'project_id', is_fk: true, fk_table: 'projects' }),
      col({ id: 'b', physical_name: 'parent_sample_id', is_fk: true, fk_table: 'samples' }),
      col({ id: 'c', physical_name: 'sample_type', is_fk: true, fk_table: 'list_entries' }),
      col({ id: 'd', physical_name: 'description' }),
    ];
    expect(keyColumnsFor(cols, 'projects').map((c) => c.id)).toEqual(['a']);
    expect(keyColumnsFor(cols, 'samples').map((c) => c.id)).toEqual(['b']);
    expect(keyColumnsFor(cols, undefined)).toEqual([]);
  });

  it('previews the link in lab words with no junction table', () => {
    const many = relationSentence('one_to_many', 'Project', 'Samples', 'Project');
    expect(many).toMatch(/Each Samples points at one Project/);
    expect(many).toMatch(/real key on Samples/);
    const one = relationSentence('one_to_one', 'Samples', 'Sample passport', 'Sample');
    expect(one).toMatch(/only one Sample passport may point/);
    expect(one).toMatch(/unique key/);
    expect(many).not.toMatch(/junction/i);
  });
});
