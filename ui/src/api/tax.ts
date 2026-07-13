/** Tax categories, mirroring tuttle.model.TaxCategory (UNTDID 5305 codes). */

export type TaxCategory = "S" | "Z" | "O";

export const TAX_CATEGORY_LABELS: Record<TaxCategory, string> = {
  S: "Standard rated",
  Z: "Zero rated",
  O: "Outside scope of tax",
};

/** Coerce whatever the backend sent into a known category, defaulting to standard. */
export function taxCategory(value: unknown): TaxCategory {
  return value === "Z" || value === "O" ? value : "S";
}

/**
 * How a supply is taxed, for display: "Standard 19%", "Zero rated (Z)",
 * "Outside scope of tax (O)". Only a standard-rated supply has a meaningful rate.
 */
export function taxTreatment(category: TaxCategory, vatRate: number): string {
  if (category !== "S") return `${TAX_CATEGORY_LABELS[category]} (${category})`;
  const fraction = vatRate > 1 ? vatRate / 100 : vatRate;
  return `Standard ${(fraction * 100).toFixed(0)}%`;
}
