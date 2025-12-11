import React, { useState } from 'react';

/**
 * Header Component
 * Reusable header brand with EvoTraders logo, GitHub link, and Contact Us section
 *
 * @param {Function} onEvoTradersClick - Optional callback when EvoTraders is clicked
 * @param {string} evoTradersLinkStyle - Optional style variant: 'default' | 'close'
 */
export default function Header({
  onEvoTradersClick = null,
  evoTradersLinkStyle = 'default' // 'default' shows ↗, 'close' shows ↙
}) {
  const [activeContactCard, setActiveContactCard] = useState({ yue: false, jiaji: false });
  const [clickedContactCard, setClickedContactCard] = useState(null);

  const handleEvoTradersClick = () => {
    if (onEvoTradersClick) {
      onEvoTradersClick();
    }
  };

  return (
    <div className="header-title" style={{ flex: '0 1 auto', minWidth: 0 }}>
      <span
        className="header-link"
        onClick={handleEvoTradersClick}
        style={{ cursor: 'pointer', padding: '4px 8px', borderRadius: '3px', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
      >
        <img
          src="/trading_logo.png"
          alt="EvoTraders Logo"
          style={{ height: '24px', width: 'auto' }}
        />
        EvoTraders {evoTradersLinkStyle === 'close' ? (
          <span className="link-arrow">↙</span>
        ) : (
          <span className="link-arrow">↗</span>
        )}
      </span>

      <span style={{
        width: '2px',
        height: '16px',
        background: '#666',
        margin: '0 16px',
        display: 'inline-block',
        verticalAlign: 'middle'
      }} />

      <span style={{
        padding: '1px 5px',
        fontSize: '9px',
        fontWeight: 700,
        color: '#00C853',
        background: 'rgba(0, 200, 83, 0.1)',
        border: '1px solid #00C853',
        borderRadius: '3px',
        letterSpacing: '0.5px',
        marginRight: '0px'
      }}>
        OPEN SOURCE
      </span>

      <a
        href="https://github.com/agentscope-ai/agentscope-samples"
        target="_blank"
        rel="noopener noreferrer"
        className="header-link"
        style={{ display: 'inline-flex', flexDirection: 'row', alignItems: 'center', gap: '6px' }}
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="currentColor"
          style={{ display: 'inline-block' }}
        >
          <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
        </svg>
        <span>agentscope-samples</span>
        <span className="link-arrow">↗</span>
      </a>

      <a
        href="https://github.com/agentscope-ai/ReMe"
        target="_blank"
        rel="noopener noreferrer"
        className="header-link"
        style={{ display: 'inline-flex', flexDirection: 'row', alignItems: 'center', gap: '6px', marginLeft: '0px' }}
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="currentColor"
          style={{ display: 'inline-block' }}
        >
          <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
        </svg>
        <span>agentscope-ReMe</span>
        <span className="link-arrow">↗</span>
      </a>

      <span style={{
        width: '2px',
        height: '16px',
        background: '#666',
        margin: '0 16px',
        display: 'inline-block',
        verticalAlign: 'middle'
      }} />

      <div
        style={{
          position: 'relative',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          cursor: 'pointer'
        }}
        onClick={() => {
          const bothActive = activeContactCard.yue && activeContactCard.jiaji;
          if (!bothActive) {
            setActiveContactCard({ yue: true, jiaji: true });
            setClickedContactCard('both');
          } else {
            setActiveContactCard({ yue: false, jiaji: false });
            setClickedContactCard(null);
          }
        }}
      >
        <span className="header-link">
          Contact Us
        </span>

        {/* Two contact buttons */}
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <div
            onClick={(e) => {
              e.stopPropagation();
              if (activeContactCard.yue) {
                setActiveContactCard(prev => ({ ...prev, yue: false }));
                if (clickedContactCard === 'yue' || clickedContactCard === 'both') {
                  setClickedContactCard(null);
                }
              } else {
                setActiveContactCard(prev => ({ ...prev, yue: true }));
                setClickedContactCard('yue');
              }
            }}
            onMouseEnter={() => {
              if (!clickedContactCard || clickedContactCard === 'yue' || clickedContactCard === 'both') {
                setActiveContactCard(prev => ({ ...prev, yue: true }));
              }
            }}
            onMouseLeave={() => {
              if (clickedContactCard !== 'yue' && clickedContactCard !== 'both') {
                setActiveContactCard(prev => ({ ...prev, yue: false }));
              }
            }}
            style={{
              padding: '4px 8px',
              background: activeContactCard.yue ? '#615CED' : '#f5f5f5',
              color: activeContactCard.yue ? '#fff' : '#333',
              border: '1px solid',
              borderColor: activeContactCard.yue ? '#615CED' : '#e0e0e0',
              borderRadius: '3px',
              fontSize: '10px',
              fontWeight: 700,
              fontFamily: "'IBM Plex Mono', monospace",
              cursor: 'pointer',
              transition: 'all 0.2s',
              letterSpacing: '0.5px',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              maxWidth: activeContactCard.yue ? '80px' : '32px',
              minWidth: activeContactCard.yue ? '80px' : '32px'
            }}
          >
            {activeContactCard.yue ? (
              <a
                href="https://1mycell.github.io/"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: 'inherit', textDecoration: 'none' }}
                onClick={(e) => e.stopPropagation()}
              >
                Yue Wu ↗
              </a>
            ) : 'YW'}
          </div>

          <div
            onClick={(e) => {
              e.stopPropagation();
              if (activeContactCard.jiaji) {
                setActiveContactCard(prev => ({ ...prev, jiaji: false }));
                if (clickedContactCard === 'jiaji' || clickedContactCard === 'both') {
                  setClickedContactCard(null);
                }
              } else {
                setActiveContactCard(prev => ({ ...prev, jiaji: true }));
                setClickedContactCard('jiaji');
              }
            }}
            onMouseEnter={() => {
              if (!clickedContactCard || clickedContactCard === 'jiaji' || clickedContactCard === 'both') {
                setActiveContactCard(prev => ({ ...prev, jiaji: true }));
              }
            }}
            onMouseLeave={() => {
              if (clickedContactCard !== 'jiaji' && clickedContactCard !== 'both') {
                setActiveContactCard(prev => ({ ...prev, jiaji: false }));
              }
            }}
            style={{
              padding: '4px 8px',
              background: activeContactCard.jiaji ? '#615CED' : '#f5f5f5',
              color: activeContactCard.jiaji ? '#fff' : '#333',
              border: '1px solid',
              borderColor: activeContactCard.jiaji ? '#615CED' : '#e0e0e0',
              borderRadius: '3px',
              fontSize: '10px',
              fontWeight: 700,
              fontFamily: "'IBM Plex Mono', monospace",
              cursor: 'pointer',
              transition: 'all 0.2s',
              letterSpacing: '0.5px',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              maxWidth: activeContactCard.jiaji ? '100px' : '32px',
              minWidth: activeContactCard.jiaji ? '100px' : '32px'
            }}
          >
            {activeContactCard.jiaji ? (
              <a
                href="https://dengjiaji.github.io/self/"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: 'inherit', textDecoration: 'none' }}
                onClick={(e) => e.stopPropagation()}
              >
                Jiaji Deng ↗
              </a>
            ) : 'JD'}
          </div>
        </div>
      </div>
    </div>
  );
}

