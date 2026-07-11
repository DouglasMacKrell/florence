const DEFAULT_CONTACT_PHONE = "+18779166745";

export function contactPhoneE164(): string {
  const configured = import.meta.env.VITE_CONTACT_PHONE?.trim();
  return configured || DEFAULT_CONTACT_PHONE;
}

export function formatContactPhone(e164: string): string {
  const digits = e164.replace(/\D/g, "");
  if (digits.length === 11 && digits.startsWith("1")) {
    return `+1 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
  }
  if (digits.length === 10) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  }
  return e164;
}

export function contactPhoneDisplay(): string {
  return formatContactPhone(contactPhoneE164());
}

export function contactPhoneTelUri(): string {
  const digits = contactPhoneE164().replace(/\D/g, "");
  return digits.startsWith("1") ? `tel:+${digits}` : `tel:+1${digits}`;
}
