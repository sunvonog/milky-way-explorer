export type ArrowRow = Record<string, unknown>

export function requiredString(row: ArrowRow, field: string): string {
  const value = row[field]

  if (typeof value !== 'string') {
    throw new TypeError(`${field} must be a string`)
  }

  return value
}

export function requiredNumber(row: ArrowRow, field: string): number {
  const value = row[field]

  if (typeof value !== 'number') {
    throw new TypeError(`${field} must be a number`)
  }

  return value
}

export function requiredBoolean(row: ArrowRow, field: string): boolean {
  const value = row[field]

  if (typeof value !== 'boolean') {
    throw new TypeError(`${field} must be a boolean`)
  }

  return value
}

export function nullableString(row: ArrowRow, field: string): string | null {
  const value = row[field]

  if (value === null) {
    return null
  }

  if (typeof value !== 'string') {
    throw new TypeError(`${field} must be a string or null`)
  }

  return value
}

export function nullableNumber(row: ArrowRow, field: string): number | null {
  const value = row[field]

  if (value === null) {
    return null
  }

  if (typeof value !== 'number') {
    throw new TypeError(`${field} must be a number or null`)
  }

  return value
}
