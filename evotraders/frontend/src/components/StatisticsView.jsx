import React, { useState, useEffect } from 'react';
import StockLogo from './StockLogo';
import { formatNumber, formatDateTime } from '../utils/formatters';

/**
 * Statistics View Component
 * Displays portfolio overview, holdings, and trade history in a side-by-side layout
 * Left: Performance Overview (35%) | Right: Holdings + Trades (65%)
 * No scrolling - content fits within viewport with pagination
 */
export default function StatisticsView({ trades, holdings, stats, baseline_vw, equity, leaderboard }) {
  const [holdingsPage, setHoldingsPage] = useState(1);
  const [tradesPage, setTradesPage] = useState(1);
  const holdingsPerPage = 5;
  const tradesPerPage = 8;

  // Calculate pagination for holdings
  const totalHoldingsPages = Math.ceil(holdings.length / holdingsPerPage);
  const holdingsStartIndex = (holdingsPage - 1) * holdingsPerPage;
  const holdingsEndIndex = holdingsStartIndex + holdingsPerPage;
  const currentHoldings = holdings.slice(holdingsStartIndex, holdingsEndIndex);

  // Calculate pagination for trades
  const totalTradesPages = Math.ceil(trades.length / tradesPerPage);
  const tradesStartIndex = (tradesPage - 1) * tradesPerPage;
  const tradesEndIndex = tradesStartIndex + tradesPerPage;
  const currentTrades = trades.slice(tradesStartIndex, tradesEndIndex);

  // Calculate excess return (Evatraders return - benchmark value-weighted return)
  const calculateExcessReturn = () => {
    if (!stats || !baseline_vw || baseline_vw.length === 0) {
      return null;
    }

    // Get Evatraders return from stats
    const evatradersReturn = stats.totalReturn || 0; // Already in percentage

    // Calculate benchmark return from baseline_vw
    // baseline_vw format: [{t: timestamp, v: value}, ...] or [value, ...]
    let benchmarkInitialValue, benchmarkCurrentValue;

    if (baseline_vw.length > 0) {
      const firstPoint = baseline_vw[0];
      const lastPoint = baseline_vw[baseline_vw.length - 1];

      benchmarkInitialValue = typeof firstPoint === 'object' ? firstPoint.v : firstPoint;
      benchmarkCurrentValue = typeof lastPoint === 'object' ? lastPoint.v : lastPoint;

      if (benchmarkInitialValue && benchmarkInitialValue > 0 && benchmarkCurrentValue) {
        const benchmarkReturn = ((benchmarkCurrentValue - benchmarkInitialValue) / benchmarkInitialValue) * 100;
        const excessReturn = evatradersReturn - benchmarkReturn;
        return {
          excessReturn: excessReturn,
          benchmarkReturn: benchmarkReturn,
          evatradersReturn: evatradersReturn
        };
      }
    }

    return null;
  };

  const excessReturnData = calculateExcessReturn();

  // Calculate Portfolio Manager's win rate (similar logic to AgentCard)
  const calculatePortfolioManagerWinRate = () => {
    if (!leaderboard || !Array.isArray(leaderboard)) {
      return null;
    }

    // Find portfolio_manager in leaderboard
    const pmData = leaderboard.find(agent => agent.agentId === 'portfolio_manager');

    if (!pmData) {
      return null;
    }

    // Extract bull and bear data
    const bullTotal = pmData.bull?.n || 0;
    const bullWins = pmData.bull?.win || 0;
    const bullUnknown = pmData.bull?.unknown || 0;
    const bearTotal = pmData.bear?.n || 0;
    const bearWins = pmData.bear?.win || 0;
    const bearUnknown = pmData.bear?.unknown || 0;

    // Calculate evaluated counts (exclude unknown)
    const evaluatedBull = Math.max(bullTotal - bullUnknown, 0);
    const evaluatedBear = Math.max(bearTotal - bearUnknown, 0);
    const evaluatedTotal = evaluatedBull + evaluatedBear;

    // Calculate win rate
    const totalWins = bullWins + bearWins;
    const winRate = evaluatedTotal > 0 ? (totalWins / evaluatedTotal) : null;

    return {
      winRate,
      totalWins,
      evaluatedTotal,
      bullWins,
      bearWins,
      evaluatedBull,
      evaluatedBear
    };
  };

  const pmWinRateData = calculatePortfolioManagerWinRate();

  // Reset to page 1 when data changes
  useEffect(() => {
    setHoldingsPage(1);
  }, [holdings.length]);

  useEffect(() => {
    setTradesPage(1);
  }, [trades.length]);

  return (
    <div style={{
      display: 'flex',
      height: '100%',
      overflow: 'hidden',
      background: '#f5f5f5'
    }}>
      {/* Left Panel: Performance Overview (35%) */}
      <div style={{
        width: '35%',
        display: 'flex',
        flexDirection: 'column',
        background: '#ffffff',
        borderRight: '2px solid #e0e0e0',
        overflow: 'hidden'
      }}>
        {stats ? (
          <div style={{
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            height: '100%'
          }}>
            {/* Header */}
            <div style={{
              marginBottom: 24,
              paddingBottom: 16,
              borderBottom: '3px solid #000000'
            }}>
              <h2 style={{
                fontSize: 16,
                fontWeight: 700,
                letterSpacing: 2,
                margin: 0,
                color: '#000000',
                textTransform: 'uppercase'
              }}>
                Performance
              </h2>
            </div>

            {/* Main Stats - Hierarchical Layout */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 20 }}>
              {/* Primary Metric - Total Asset Value */}
              <div style={{
                padding: '20px 0',
                borderBottom: '1px solid #e0e0e0'
              }}>
                <div style={{
                  fontSize: 10,
                  color: '#666666',
                  fontWeight: 700,
                  letterSpacing: 1.5,
                  marginBottom: 12,
                  textTransform: 'uppercase'
                }}>
                  Total Asset Value
                </div>
                <div style={{
                  fontSize: 36,
                  fontWeight: 700,
                  color: '#000000',
                  fontFamily: '"Courier New", monospace',
                  lineHeight: 1
                }}>
                  ${formatNumber(stats.totalAssetValue || 0)}
                </div>
              </div>

              {/* Secondary Metrics - Grid: Excess Return, Win Rate, Absolute Return */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: excessReturnData ? '1fr 1fr 1fr' : '1fr 1fr',
                gap: 16,
                paddingBottom: 20,
                borderBottom: '1px solid #e0e0e0'
              }}>
                {/* 1. Excess Return */}
                {excessReturnData ? (
                  <div>
                    <div style={{
                      fontSize: 9,
                      color: '#999999',
                      fontWeight: 700,
                      letterSpacing: 1,
                      marginBottom: 8,
                      textTransform: 'uppercase'
                    }}>
                      Excess Return
                    </div>
                    <div style={{
                      fontSize: 28,
                      fontWeight: 700,
                      color: excessReturnData.excessReturn >= 0 ? '#00C853' : '#FF1744',
                      fontFamily: '"Courier New", monospace'
                    }}>
                      {excessReturnData.excessReturn >= 0 ? '+' : ''}{excessReturnData.excessReturn.toFixed(2)}%
                    </div>
                    <div style={{
                      fontSize: 7,
                      color: '#999999',
                      marginTop: 4,
                      fontFamily: '"Courier New", monospace'
                    }}>
                      vs. VW: {excessReturnData.benchmarkReturn >= 0 ? '+' : ''}{excessReturnData.benchmarkReturn.toFixed(2)}%
                    </div>
                  </div>
                ) : null}

                {/* 2. Win Rate */}
                <div>
                  <div style={{
                    fontSize: 9,
                    color: '#999999',
                    fontWeight: 700,
                    letterSpacing: 1,
                    marginBottom: 8,
                    textTransform: 'uppercase'
                  }}>
                    Win Rate
                  </div>
                  <div style={{
                    fontSize: 28,
                    fontWeight: 700,
                    color: pmWinRateData?.winRate != null ? '#00C853' : '#000000',
                    fontFamily: '"Courier New", monospace'
                  }}>
                    {pmWinRateData?.winRate != null
                      ? `${(pmWinRateData.winRate * 100).toFixed(1)}%`
                      : 'N/A'}
                  </div>
                  {pmWinRateData && (
                    <div style={{
                      fontSize: 7,
                      color: '#999999',
                      marginTop: 4,
                      fontFamily: '"Courier New", monospace'
                    }}>
                      {pmWinRateData.totalWins}Win / {pmWinRateData.evaluatedTotal}Eval
                    </div>
                  )}
                </div>

                {/* 3. Absolute Return */}
                <div>
                  <div style={{
                    fontSize: 9,
                    color: '#999999',
                    fontWeight: 700,
                    letterSpacing: 1,
                    marginBottom: 8,
                    textTransform: 'uppercase'
                  }}>
                    Absolute Return
                  </div>
                  <div style={{
                    fontSize: 28,
                    fontWeight: 700,
                    color: (stats.totalReturn || 0) >= 0 ? '#00C853' : '#FF1744',
                    fontFamily: '"Courier New", monospace'
                  }}>
                    {(stats.totalReturn || 0) >= 0 ? '+' : ''}{(stats.totalReturn || 0).toFixed(2)}%
                  </div>
                </div>
              </div>

              {/* Tertiary Metrics - Compact List */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'baseline',
                  padding: '8px 0',
                  borderBottom: '1px solid #f0f0f0'
                }}>
                  <div style={{
                    fontSize: 10,
                    color: '#666666',
                    fontWeight: 600,
                    letterSpacing: 0.5,
                    textTransform: 'uppercase'
                  }}>
                    Cash Position
                  </div>
                  <div style={{
                    fontSize: 16,
                    fontWeight: 700,
                    color: '#000000',
                    fontFamily: '"Courier New", monospace'
                  }}>
                    ${formatNumber(stats.cashPosition || 0)}
                  </div>
                </div>

                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'baseline',
                  padding: '8px 0',
                  borderBottom: '1px solid #f0f0f0'
                }}>
                  <div style={{
                    fontSize: 10,
                    color: '#666666',
                    fontWeight: 600,
                    letterSpacing: 0.5,
                    textTransform: 'uppercase'
                  }}>
                    Total Trades
                  </div>
                  <div style={{
                    fontSize: 16,
                    fontWeight: 700,
                    color: '#000000',
                    fontFamily: '"Courier New", monospace'
                  }}>
                    {stats.totalTrades || 0}
                  </div>
                </div>
              </div>

              {/* Ticker Weights - Compact */}
              {stats.tickerWeights && Object.keys(stats.tickerWeights).length > 0 && (
                <div style={{
                  marginTop: 'auto',
                  paddingTop: 20,
                  borderTop: '1px solid #e0e0e0'
                }}>
                  <div style={{
                    fontSize: 10,
                    fontWeight: 700,
                    marginBottom: 12,
                    letterSpacing: 1,
                    textTransform: 'uppercase',
                    color: '#666666'
                  }}>
                    Portfolio Weights
                  </div>
                  <div className="statistics-table-container" style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(2, 1fr)',
                    gap: 8,
                    maxHeight: 120
                  }}>
                    {Object.entries(stats.tickerWeights).map(([ticker, weight]) => {
                      const weightValue = Number(weight);
                      const isNegative = weightValue < 0;
                      const displayWeight = (weightValue * 100).toFixed(1);

                      return (
                        <div key={ticker} style={{
                          padding: '6px 10px',
                          background: '#fafafa',
                          border: '1px solid #e0e0e0',
                          fontSize: 10,
                          fontWeight: 700,
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          fontFamily: '"Courier New", monospace'
                        }}>
                          <span style={{ color: '#000000' }}>{ticker}</span>
                          <span style={{ color: isNegative ? '#FF1744' : '#00C853' }}>
                            {displayWeight}%
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: '#999999',
            fontSize: 12,
            letterSpacing: 0.5
          }}>
            No statistics available
          </div>
        )}
      </div>

      {/* Right Panel: Holdings + Trades (65%) */}
      <div style={{
        width: '65%',
        display: 'flex',
        flexDirection: 'column',
        background: '#ffffff',
        overflow: 'hidden'
      }}>
        {/* Portfolio Holdings - Top Half */}
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          background: '#ffffff',
          margin: '16px 16px 8px 16px',
          border: '1px solid #e0e0e0',
          overflow: 'hidden'
        }}>
          <div style={{
            padding: '16px 20px',
            borderBottom: '2px solid #000000',
            flexShrink: 0
          }}>
            <h2 style={{
              fontSize: 13,
              fontWeight: 700,
              letterSpacing: 1.5,
              margin: 0,
              color: '#000000',
              textTransform: 'uppercase'
            }}>
              Portfolio Holdings
            </h2>
          </div>

          <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            {holdings.length === 0 ? (
              <div style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#999999',
                fontSize: 11,
                letterSpacing: 0.5
              }}>
                No positions currently held
              </div>
            ) : (
              <>
                <div className="statistics-table-container" style={{ flex: 1 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Ticker</th>
                        <th>Quantity</th>
                        <th>Price</th>
                        <th>Value</th>
                        <th>Weight</th>
                      </tr>
                    </thead>
                    <tbody>
                      {currentHoldings.map(h => {
                        // For short positions, quantity should be negative and weight should also be negative
                        const isShort = h.ticker !== 'CASH' && Number(h.quantity) < 0;
                        const displayWeight = isShort ? -Math.abs(Number(h.weight)) : Number(h.weight);

                        return (
                          <tr key={h.ticker}>
                            <td>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                {h.ticker !== 'CASH' && <StockLogo ticker={h.ticker} size={18} />}
                                <span style={{ fontWeight: 700, color: '#000000' }}>{h.ticker}</span>
                              </div>
                            </td>
                            <td>{h.ticker === 'CASH' ? '-' : h.quantity}</td>
                            <td>{h.ticker === 'CASH' ? '-' : `$${Number(h.currentPrice).toFixed(2)}`}</td>
                            <td style={{ fontWeight: 700 }}>${formatNumber(h.marketValue)}</td>
                            <td style={{ color: isShort ? '#FF1744' : '#000000' }}>
                              {(displayWeight * 100).toFixed(2)}%
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {totalHoldingsPages > 1 && (
                  <div style={{
                    padding: '12px 20px',
                    borderTop: '1px solid #e0e0e0',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexShrink: 0,
                    background: '#fafafa'
                  }}>
                    <button
                      className="pagination-btn"
                      onClick={() => setHoldingsPage(p => Math.max(1, p - 1))}
                      disabled={holdingsPage === 1}
                    >
                      ◀ Prev
                    </button>

                    <div className="pagination-info">
                      {holdingsPage} / {totalHoldingsPages}
                    </div>

                    <button
                      className="pagination-btn"
                      onClick={() => setHoldingsPage(p => Math.min(totalHoldingsPages, p + 1))}
                      disabled={holdingsPage === totalHoldingsPages}
                    >
                      Next ▶
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Transaction History - Bottom Half */}
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          background: '#ffffff',
          margin: '8px 16px 16px 16px',
          border: '1px solid #e0e0e0',
          overflow: 'hidden'
        }}>
          <div style={{
            padding: '16px 20px',
            borderBottom: '2px solid #000000',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexShrink: 0
          }}>
            <h2 style={{
              fontSize: 13,
              fontWeight: 700,
              letterSpacing: 1.5,
              margin: 0,
              color: '#000000',
              textTransform: 'uppercase'
            }}>
              Transaction History
            </h2>
            {trades.length > 0 && (
              <div style={{
                fontSize: 10,
                color: '#666666',
                fontFamily: '"Courier New", monospace'
              }}>
                {trades.length} total
              </div>
            )}
          </div>

          <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            {trades.length === 0 ? (
              <div style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#999999',
                fontSize: 11,
                letterSpacing: 0.5
              }}>
                No trades recorded
              </div>
            ) : (
              <>
                <div className="statistics-table-container" style={{ flex: 1 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Stock</th>
                        <th>Side</th>
                        <th>Qty</th>
                        <th>Price</th>
                      </tr>
                    </thead>
                    <tbody>
                      {currentTrades.map((t, idx) => (
                        <tr key={t.id || `${t.ticker}-${t.timestamp}-${idx}`}>
                          <td style={{ fontSize: 10, color: '#666666', fontFamily: '"Courier New", monospace' }}>
                            {formatDateTime(t.timestamp)}
                          </td>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <StockLogo ticker={t.ticker} size={16} />
                              <span style={{ fontWeight: 700, color: '#000000' }}>{t.ticker}</span>
                            </div>
                          </td>
                          <td>
                            <span style={{
                              display: 'inline-block',
                              padding: '2px 6px',
                              fontSize: 9,
                              fontWeight: 700,
                              border: `1px solid ${t.side === 'LONG' ? '#00C853' : t.side === 'SHORT' ? '#FF1744' : '#666666'}`,
                              color: t.side === 'LONG' ? '#00C853' : t.side === 'SHORT' ? '#FF1744' : '#666666'
                            }}>
                              {t.side}
                            </span>
                          </td>
                          <td>{t.qty}</td>
                          <td>${Number(t.price).toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {totalTradesPages > 1 && (
                  <div style={{
                    padding: '12px 20px',
                    borderTop: '1px solid #e0e0e0',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexShrink: 0,
                    background: '#fafafa'
                  }}>
                    <button
                      className="pagination-btn"
                      onClick={() => setTradesPage(p => Math.max(1, p - 1))}
                      disabled={tradesPage === 1}
                    >
                      ◀ Prev
                    </button>

                    <div className="pagination-info">
                      {tradesPage} / {totalTradesPages}
                    </div>

                    <button
                      className="pagination-btn"
                      onClick={() => setTradesPage(p => Math.min(totalTradesPages, p + 1))}
                      disabled={tradesPage === totalTradesPages}
                    >
                      Next ▶
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
