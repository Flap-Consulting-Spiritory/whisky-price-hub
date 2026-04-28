import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPrice(price: number | null, currency: string | null): string {
  if (price === null || price === undefined) return "—";
  const cur = (currency || "EUR").toUpperCase();
  const amount = price.toFixed(2);
  switch (cur) {
    case "EUR": return `€${amount}`;
    case "USD": return `$${amount}`;
    case "GBP": return `£${amount}`;
    case "CHF": return `CHF ${amount}`;
    case "JPY": return `¥${amount}`;
    default:    return `${cur} ${amount}`;
  }
}

export function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
