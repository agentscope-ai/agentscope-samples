import React from 'react';
import { ASSETS } from '../config/constants';
import { getModelIcon, getShortModelName } from '../utils/modelIcons';

/**
 * Get rank medal/trophy
 */
function getRankMedal(rank) {
  if (rank === 1) return { emoji: '🏆', color: '#FFD700', label: 'Gold' };
  if (rank === 2) return { emoji: '🥈', color: '#C0C0C0', label: 'Silver' };
  if (rank === 3) return { emoji: '🥉', color: '#CD7F32', label: 'Bronze' };
  return { emoji: `#${rank}`, color: '#333333', label: `#${rank}` };
}

/**
 * Agent Performance Card Component
 * Horizontal dropdown panel displayed below the agent indicator bar
 */
export default function AgentCard({ agent, onClose, isClosing }) {
  if (!agent) return null;

  const bullTotal = agent.bull?.n || 0;
  const bullWins = agent.bull?.win || 0;
  const bullUnknown = agent.bull?.unknown || 0;
  const bearTotal = agent.bear?.n || 0;
  const bearWins = agent.bear?.win || 0;
  const bearUnknown = agent.bear?.unknown || 0;
  const totalSignals = bullTotal + bearTotal;
  const evaluatedBull = Math.max(bullTotal - bullUnknown, 0);
  const evaluatedBear = Math.max(bearTotal - bearUnknown, 0);
  const evaluatedTotal = evaluatedBull + evaluatedBear;
  const bullWinRate = evaluatedBull > 0 ? (bullWins / evaluatedBull) : null;
  const bearWinRate = evaluatedBear > 0 ? (bearWins / evaluatedBear) : null;
  const overallWinRate = agent.winRate != null
    ? agent.winRate
    : (evaluatedTotal > 0 ? ((bullWins + bearWins) / evaluatedTotal) : null);
  const overallColor = overallWinRate != null
    ? (overallWinRate >= 0.5 ? '#00C853' : '#FF1744')
    : '#555555';

  const rankMedal = agent.rank ? getRankMedal(agent.rank) : null;
  const isPortfolioManager = agent.id === 'portfolio_manager';
  const isRiskManager = agent.id === 'risk_manager';
  const displayName = isPortfolioManager ? 'Team' : agent.name;

  // Get model icon configuration
  const modelInfo = getModelIcon(agent.modelName, agent.modelProvider);
  const shortModelName = getShortModelName(agent.modelName);

  return (
    <div style={{
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      background: '#ffffff',
      borderBottom: '2px solid #000000',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
      zIndex: 1000,
      animation: isClosing ? 'slideUp 0.2s ease-out forwards' : 'slideDown 0.25s ease-out'
    }}>
      {/* Horizontal scrollable content */}
      <div style={{
        overflowX: 'auto',
        overflowY: 'hidden',
        padding: '12px',

        /* Hide scrollbar for all browsers */
        scrollbarWidth: 'none', /* Firefox */
        msOverflowStyle: 'none', /* IE and Edge */
      }}>
        <style>
          {`
            div::-webkit-scrollbar {
              display: none; /* Chrome, Safari, Opera */
            }
          `}
        </style>

        <div style={{
          display: 'flex',
          gap: '12px',
          minWidth: 'max-content'
        }}>
          {/* Agent Info with Rank */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '8px 12px',
            background: '#fafafa',
            border: '2px solid #000000',
            minWidth: 200
          }}>
            {isPortfolioManager ? (
              <img
                src={ASSETS.teamLogo}
                alt="Team"
                style={{
                  height: 50,
                  width: 50,
                  objectFit: 'contain'
                }}
              />
            ) : agent.avatar ? (
              <img
                src={agent.avatar}
                alt={agent.name}
                style={{
                  height: 50,
                  width: 50,
                  objectFit: 'contain'
                }}
              />
            ) : null}
            <div>
              <div style={{
                fontSize: 16,
                fontWeight: 700,
                color: '#000000',
                marginBottom: 2
              }}>
                {displayName}
              </div>
              {rankMedal && !isPortfolioManager && (
                <div style={{ fontSize: 18 }}>
                  {rankMedal.emoji} Rank #{agent.rank}
                </div>
              )}
            </div>
          </div>

          {/* Risk Manager Note */}
          {isRiskManager && (
            <div style={{
              padding: '8px 12px',
              background: '#FFF9E6',
              border: '2px solid #FFA726',
              minWidth: 220,
              maxWidth: 280,
              display: 'flex',
              alignItems: 'center'
            }}>
              <div style={{
                fontSize: 12,
                color: '#E65100',
                fontStyle: 'italic',
                lineHeight: 1.5,
                whiteSpace: 'normal',
                wordWrap: 'break-word'
              }}>
                ⓘ Risk Manager focuses on risk management and does not participate in prediction accuracy ranking.
              </div>
            </div>
          )}

          {/* Portfolio Manager Note */}
          {isPortfolioManager && (
            <div style={{
              padding: '8px 12px',
              background: '#E8F5E9',
              border: '2px solid #66BB6A',
              minWidth: 220,
              maxWidth: 280,
              display: 'flex',
              alignItems: 'center'
            }}>
              <div style={{
                fontSize: 12,
                color: '#2E7D32',
                fontStyle: 'italic',
                lineHeight: 1.5,
                whiteSpace: 'normal',
                wordWrap: 'break-word'
              }}>
                ⓘ Portfolio Manager provides the team's final signal(position), synthesizing all analyst recommendations, and does not participate in ranking.
              </div>
            </div>
          )}

          {/* Model Info Card */}
          {agent.modelName && (
            <div style={{
              padding: '8px 12px',
              background: '#ffffff',
              border: `2px solid ${modelInfo.color}`,
              minWidth: 140,
              position: 'relative',
              cursor: 'help'
            }}
            title={`Model: ${agent.modelName}\nProvider: ${modelInfo.provider}`}>
              <div style={{
                fontSize: 10,
                fontWeight: 700,
                color: modelInfo.color,
                letterSpacing: 1,
                marginBottom: 4,
                textTransform: 'uppercase'
              }}>
                Model
              </div>
              <div style={{
                height: 40,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: 4
              }}>
                {modelInfo.logoPath ? (
                  <img
                    src={modelInfo.logoPath}
                    alt={modelInfo.provider}
                    style={{
                      maxHeight: '100%',
                      maxWidth: '100%',
                      objectFit: 'contain'
                    }}
                  />
                ) : (
                  <div style={{
                    fontSize: 28,
                    lineHeight: 1
                  }}>
                    🤖
                  </div>
                )}
              </div>
              <div style={{
                fontSize: 11,
                fontWeight: 600,
                color: modelInfo.color,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {shortModelName}
              </div>
              <div style={{
                fontSize: 8,
                color: '#666666',
                marginTop: 2
              }}>
                {modelInfo.provider}
              </div>
            </div>
          )}

          {/* Overall Win Rate */}
          {!isRiskManager && !isPortfolioManager && (
            <div style={{
              padding: '8px 14px',
              background: '#fafafa',
              border: '2px solid #e0e0e0',
              textAlign: 'center',
              minWidth: 160
            }}>
              <div style={{
                fontSize: 10,
                color: '#333333',
                fontWeight: 700,
                letterSpacing: 1,
                marginBottom: 4,
                textTransform: 'uppercase'
              }}>
                Win Rate
              </div>
              <div style={{
                fontSize: 36,
                fontWeight: 700,
                color: overallColor,
                fontFamily: '"Courier New", monospace',
                lineHeight: 1,
                marginBottom: 2
              }}>
                {overallWinRate != null ? `${(overallWinRate * 100).toFixed(1)}%` : 'N/A'}
              </div>
              <div style={{
                fontSize: 9,
                color: '#555555'
              }}>
                {bullWins + bearWins}Win / {evaluatedTotal}Eval
              </div>
              <div style={{
                fontSize: 8,
                color: '#888888',
                marginTop: 4,
                fontStyle: 'italic',
                lineHeight: 1.2,
                whiteSpace: 'pre-line'
              }}>
                Eval: total evaluated bull & bear signals.{'\n'}Win Rate = correct signals / total evaluated signals
              </div>
            </div>
          )}

          {/* Bull Stats */}
          {!isRiskManager && !isPortfolioManager && (
            <div style={{
              padding: '8px 12px',
              background: '#F0FFF4',
              border: '2px solid #00C853',
              minWidth: 140
            }}>
              <div style={{
                fontSize: 10,
                fontWeight: 700,
                color: '#00C853',
                letterSpacing: 1,
                marginBottom: 4,
                textTransform: 'uppercase'
              }}>
                Bull Win Rate
              </div>
              <div style={{
                fontSize: 28,
                fontWeight: 700,
                color: bullWinRate != null ? (bullWinRate >= 0.5 ? '#00C853' : '#333333') : '#555555',
                marginBottom: 2,
                lineHeight: 1
              }}>
                {bullWinRate != null ? `${(bullWinRate * 100).toFixed(1)}%` : 'N/A'}
              </div>
              <div style={{
                fontSize: 9,
                color: '#333333'
              }}>
                {bullWins}Win / {evaluatedBull}Eval
                {bullUnknown > 0 && ` / ${bullUnknown}P`}
              </div>
            </div>
          )}

          {/* Bear Stats */}
          {!isRiskManager && !isPortfolioManager && (
            <div style={{
              padding: '8px 12px',
              background: '#FFF5F5',
              border: '2px solid #FF1744',
              minWidth: 140
            }}>
              <div style={{
                fontSize: 10,
                fontWeight: 700,
                color: '#FF1744',
                letterSpacing: 1,
                marginBottom: 4,
                textTransform: 'uppercase'
              }}>
                Bear Win Rate
              </div>
              <div style={{
                fontSize: 28,
                fontWeight: 700,
                color: bearWinRate != null ? (bearWinRate >= 0.5 ? '#00C853' : '#333333') : '#555555',
                marginBottom: 2,
                lineHeight: 1
              }}>
                {bearWinRate != null ? `${(bearWinRate * 100).toFixed(1)}%` : 'N/A'}
              </div>
              <div style={{
                fontSize: 9,
                color: '#333333'
              }}>
                {bearWins}Win / {evaluatedBear}Eval
                {bearUnknown > 0 && ` / ${bearUnknown}P`}
              </div>
            </div>
          )}

          {/* Recent Signals - Horizontal scroll */}
          {agent.signals && agent.signals.length > 0 && (
            <div style={{
              display: 'flex',
              gap: 6,
              padding: '8px 12px',
              background: '#fafafa',
              border: '2px solid #e0e0e0'
            }}>
              {[...agent.signals]
                .filter(signal => signal && signal.signal)
                .sort((a, b) => {
                  // Sort by date descending (newest first)
                  const dateA = a.date || '';
                  const dateB = b.date || '';
                  return dateB.localeCompare(dateA);
                })
                .slice(0, 35)
                .map((signal, idx) => {
                const signalType = signal.signal.toLowerCase();
                const isBull = signalType.includes('bull') || signalType === 'long';
                const isBear = signalType.includes('bear') || signalType === 'short';
                const isNeutral = (!isBull && !isBear) || signalType.includes('neutral') || signalType === 'hold';
                const isCorrect = signal.is_correct === true;
                const isUnknown = signal.is_correct === 'unknown' || signal.is_correct === null;

                // Determine result symbol/text and color: unknown has priority over neutral
                let resultDisplay;
                let resultColor = '#555555';
                let resultFontSize = 18;

                if (isNeutral) {
                  resultDisplay = '-';
                  resultColor = '#555555'; // Gray for neutral
                } else if (isUnknown) {
                  resultDisplay = '?';
                  resultColor = '#FFA726'; // Orange for unknown
                  resultFontSize = 14; // Smaller font for text
                } else {
                  resultDisplay = isCorrect ? '✓' : '✗';
                  resultColor = isCorrect ? '#00C853' : '#FF1744'; // Green for correct, Red for wrong
                }

                return (
                  <div key={idx} style={{
                    fontSize: 9,
                    fontFamily: '"Courier New", monospace',
                    padding: '6px 8px',
                    background: '#ffffff',
                    border: '1px solid #e0e0e0',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 3,
                    minWidth: 70
                  }}>
                    <div style={{
                      fontWeight: 700,
                      color: isBull ? '#00C853' : isBear ? '#FF1744' : '#555555'
                    }}>
                      {signal.ticker}
                    </div>
                    <div style={{
                      fontSize: 16,
                      color: isBull ? '#00C853' : isBear ? '#FF1744' : '#555555'
                    }}>
                      {isBull ? 'bull' : isBear ? 'bear' : 'neutral'}
                    </div>
                    <div style={{
                      fontSize: 8,
                      color: '#555555'
                    }}>
                      {signal.date?.substring(5, 10) || 'N/A'}
                    </div>
                    <div style={{
                      fontSize: resultFontSize,
                      fontWeight: 700,
                      color: resultColor
                    }}>
                      {resultDisplay}
                    </div>
                  </div>
                );
              })}
              {/* Info card explaining signal display */}
              <div style={{
                fontSize: 9,
                fontFamily: '"Courier New", monospace',
                padding: '6px 8px',
                background: '#E3F2FD',
                border: '1px solid #90CAF9',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 2,
                minWidth: 70,
                textAlign: 'center'
              }}>
                <div style={{
                  fontSize: 10,
                  fontWeight: 700,
                  color: '#1976D2'
                }}>
                  ⓘ Info
                </div>
                <div style={{
                  fontSize: 8,
                  color: '#1976D2',
                  lineHeight: 1.2
                }}>
                  Showing recent 5 trading days (1 week) signals only
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <style>
        {`
          @keyframes slideDown {
            from {
              opacity: 0;
              transform: translateY(-20px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }

          @keyframes slideUp {
            from {
              opacity: 1;
              transform: translateY(0);
            }
            to {
              opacity: 0;
              transform: translateY(-20px);
            }
          }
        `}
      </style>
    </div>
  );
}

