import React, { useEffect, useState } from 'react';

export interface CountryPrefix {
  code: string;
  flag: string;
  prefix: string;
  label: string;
}

export const COUNTRY_PREFIXES: CountryPrefix[] = [
  { code: 'IL', flag: '🇮🇱', prefix: '+972', label: 'Israel' },
  { code: 'US', flag: '🇺🇸', prefix: '+1', label: 'United States' },
  { code: 'GB', flag: '🇬🇧', prefix: '+44', label: 'United Kingdom' },
  { code: 'DE', flag: '🇩🇪', prefix: '+49', label: 'Germany' },
  { code: 'FR', flag: '🇫🇷', prefix: '+33', label: 'France' },
  { code: 'CA', flag: '🇨🇦', prefix: '+1', label: 'Canada' },
  { code: 'AU', flag: '🇦🇺', prefix: '+61', label: 'Australia' },
  { code: 'IN', flag: '🇮🇳', prefix: '+91', label: 'India' },
];

export interface PhoneInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
  id?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
}

export const PhoneInput: React.FC<PhoneInputProps> = ({
  value,
  onChange,
  placeholder = '50-123-4567',
  label,
  id,
  required = false,
  disabled = false,
  className = '',
}) => {
  const [selectedPrefix, setSelectedPrefix] = useState<string>('+972');
  const [localNumber, setLocalNumber] = useState<string>('');

  // Synchronize internal local number & prefix when external value changes
  useEffect(() => {
    if (!value) {
      setLocalNumber('');
      return;
    }

    const trimmed = value.trim();
    const matched = COUNTRY_PREFIXES.find((c) => trimmed.startsWith(c.prefix));
    if (matched) {
      setSelectedPrefix(matched.prefix);
      setLocalNumber(trimmed.slice(matched.prefix.length).trim());
    } else if (trimmed.startsWith('0')) {
      // Local Israeli number starting with 0
      setSelectedPrefix('+972');
      setLocalNumber(trimmed.slice(1));
    } else {
      setLocalNumber(trimmed);
    }
  }, [value]);

  const handlePrefixChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newPrefix = e.target.value;
    setSelectedPrefix(newPrefix);
    const combined = localNumber.trim() ? `${newPrefix}${localNumber.trim()}` : '';
    onChange(combined);
  };

  const handleLocalChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const rawVal = e.target.value;
    setLocalNumber(rawVal);

    let clean = rawVal.trim();
    if (clean.startsWith('0')) {
      clean = clean.slice(1);
    }
    const combined = clean ? `${selectedPrefix}${clean}` : '';
    onChange(combined);
  };

  return (
    <div className={`space-y-1 ${className}`}>
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-guardian-muted">
          {label}
        </label>
      )}
      <div className="flex rounded-lg overflow-hidden border border-gray-700 focus-within:border-guardian-accent bg-gray-900">
        <select
          value={selectedPrefix}
          onChange={handlePrefixChange}
          disabled={disabled}
          className="bg-gray-800 text-white px-3 py-2 text-sm border-r border-gray-700 focus:outline-none cursor-pointer"
          aria-label="Select Country Code"
        >
          {COUNTRY_PREFIXES.map((country) => (
            <option key={country.code} value={country.prefix}>
              {country.flag} {country.prefix} ({country.label})
            </option>
          ))}
        </select>
        <input
          id={id}
          type="tel"
          value={localNumber}
          onChange={handleLocalChange}
          placeholder={placeholder}
          required={required}
          disabled={disabled}
          className="w-full bg-gray-900 px-4 py-2 text-white focus:outline-none text-sm placeholder-gray-500"
        />
      </div>
    </div>
  );
};
