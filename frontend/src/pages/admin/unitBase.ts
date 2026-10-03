export function isBaseUnit(unit: {
  multiplier?: number | string | null;
  is_base?: boolean;
}): boolean {
  if (unit.is_base) return true;
  if (unit.multiplier === null || unit.multiplier === undefined || unit.multiplier === '') return false;
  const value = Number(unit.multiplier);
  return Number.isFinite(value) && value === 1;
}
