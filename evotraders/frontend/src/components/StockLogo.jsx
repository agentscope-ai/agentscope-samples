import React from 'react';
import { STOCK_LOGOS } from '../config/constants';

/**
 * Stock Logo Component
 * Displays company logo for a given ticker symbol
 */
export default function StockLogo({ ticker, size = 20 }) {
  const logoUrl = STOCK_LOGOS[ticker];
  if (!logoUrl) return null;

  return (
    <img
      src={logoUrl}
      alt={ticker}
      style={{
        width: size,
        height: size,
        borderRadius: '4px',
        objectFit: 'contain',
        marginRight: '8px',
        verticalAlign: 'middle'
      }}
      onError={(e) => { e.target.style.display = 'none'; }}
    />
  );
}

