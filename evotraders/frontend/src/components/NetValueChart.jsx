import React, { useMemo, useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { formatNumber, formatFullNumber } from '../utils/formatters';

/**
 * Helper function to get the start time of the most recent trading session
 * Trading session: 22:30 - next day 05:00
 * @param {Date|null} virtualTime - Virtual time from server (for mock mode), or null to use real time
 */
function getRecentTradingSessionStart(virtualTime = null) {
  // Use virtual time if provided (for mock mode), otherwise use real time
  let now;
  if (virtualTime) {
    // Ensure virtualTime is a valid Date object
    if (virtualTime instanceof Date && !isNaN(virtualTime.getTime())) {
      now = virtualTime;
    } else if (typeof virtualTime === 'string') {
      now = new Date(virtualTime);
      if (isNaN(now.getTime())) {
        console.warn('Invalid virtualTime string, using current time:', virtualTime);
        now = new Date();
      }
    } else {
      console.warn('Invalid virtualTime type, using current time:', typeof virtualTime);
      now = new Date();
    }
  } else {
    now = new Date();
  }

  const currentHour = now.getHours();
  const currentMinute = now.getMinutes();

  // Check if currently in trading session
  const isInTradingSession = (currentHour === 22 && currentMinute >= 30) ||
                              currentHour >= 23 ||
                              (currentHour >= 0 && currentHour < 5) ||
                              (currentHour === 5 && currentMinute === 0);

  let sessionStartTime;
  if (isInTradingSession) {
    // Currently in trading session, find today's 22:30
    sessionStartTime = new Date(now);
    sessionStartTime.setHours(22, 30, 0, 0);
    // If current time is before 22:30, it means yesterday's 22:30
    if (now < sessionStartTime) {
      sessionStartTime.setDate(sessionStartTime.getDate() - 1);
    }
  } else {
    // Not in trading session, find previous session start (yesterday 22:30)
    sessionStartTime = new Date(now);
    sessionStartTime.setDate(sessionStartTime.getDate() - 1);
    sessionStartTime.setHours(22, 30, 0, 0);
  }

  return sessionStartTime;
}

/**
 * Helper function to filter strategy data for live view
 * NOTE: Live mode returns are now pre-processed by the backend, restricted to the
 * latest trading session and already starting at 0% at session start. This helper
 * is kept for potential future use but is no longer used in live mode.
 */
function filterStrategyDataForLive(strategyData, equity, sessionStartTime) {
  if (!strategyData || strategyData.length === 0 || !equity || equity.length === 0) return [];

  try {
    if (!sessionStartTime || isNaN(sessionStartTime.getTime())) {
      console.warn('Invalid sessionStartTime in filterStrategyDataForLive');
      return [];
    }

    const sessionStartTimestamp = sessionStartTime.getTime();

    // Find the last index before session
    let lastDataBeforeSession = null;
    for (let i = equity.length - 1; i >= 0; i--) {
      if (equity[i] && typeof equity[i].t === 'number' && equity[i].t < sessionStartTimestamp) {
        if (strategyData[i] && strategyData[i].v !== undefined && strategyData[i].v !== null) {
          lastDataBeforeSession = strategyData[i];
        }
        break;
      }
    }

    // Find data points in the session
    const sessionData = [];
    for (let i = 0; i < equity.length; i++) {
      if (equity[i] && typeof equity[i].t === 'number' &&
          equity[i].t >= sessionStartTimestamp &&
          strategyData[i] &&
          strategyData[i].v !== undefined && strategyData[i].v !== null) {
        sessionData.push(strategyData[i]);
      }
    }

    // If we have a value before session and session data, add the start point
    // Create a start point with timestamp just before session start
    if (lastDataBeforeSession && sessionData.length > 0) {
      const startPoint = {
        t: sessionStartTimestamp - 1,
        v: lastDataBeforeSession.v
      };
      return [startPoint, ...sessionData];
    }

    return sessionData;
  } catch (error) {
    console.error('Error in filterStrategyDataForLive:', error);
    return [];
  }
}

/**
 * Net Value Chart Component
 * Displays portfolio value over time with multiple strategy comparisons
 */
export default function NetValueChart({ equity, baseline, baseline_vw, momentum, strategies, equity_return, baseline_return, baseline_vw_return, momentum_return, chartTab = 'all', virtualTime = null }) {
  const [activePoint, setActivePoint] = useState(null);
  const [stableYRange, setStableYRange] = useState(null);
  const [legendTooltip, setLegendTooltip] = useState(null);

  // Legend descriptions
  const legendDescriptions = {
    'EvoTraders': 'EvoTraders is our agents investment strategy',
    'Buy & Hold (EW)': 'Equal Weight: Can be viewed as an equal-weighted index of all invested stocks',
    'Buy & Hold (VW)': 'Value Weighted: Can be viewed as a market-cap weighted index of all invested stocks',
    'Momentum': 'Momentum Strategy: Buy stocks that have performed well in the past',
  };


  // For live mode, use cumulative returns calculated by backend
  // For all mode, use portfolio values directly
  const dataSource = useMemo(() => {
    if (chartTab === 'live') {
      return {
        equity: equity_return || equity,
        baseline: baseline_return || baseline,
        baseline_vw: baseline_vw_return || baseline_vw,
        momentum: momentum_return || momentum
      };
    }
    return {
      equity: equity,
      baseline: baseline,
      baseline_vw: baseline_vw,
      momentum: momentum
    };
  }, [chartTab, equity, baseline, baseline_vw, momentum, equity_return, baseline_return, baseline_vw_return, momentum_return]);
  // Filter equity data based on chartTab
  const filteredEquity = useMemo(() => {
    if (chartTab === 'all') {
      const sourceEquity = dataSource.equity;
      if (!sourceEquity || sourceEquity.length === 0) return [];

      // ALL chart: Show only the last point per day
      // Logic: Keep the last equity value before 22:30 each day (the last equity value before US next trading day opens)
      // Data after 22:30 belongs to the next trading day's session and is not shown in this chart
      // Time handling: timestamp(ms) -> UTC -> Asia/Shanghai timezone, then group and filter based on Asia/Shanghai time
      const dailyData = {};

      sourceEquity.forEach((d) => {
        // Timestamp is in milliseconds, first create UTC time, then convert to Asia/Shanghai timezone
        // Equivalent to: pd.to_datetime(timestamp, unit='ms', utc=True).dt.tz_convert('Asia/Shanghai')
        const utcDate = new Date(d.t); // timestamp(ms) -> UTC time

        // Use Intl API to get date/time components in Asia/Shanghai timezone
        const formatter = new Intl.DateTimeFormat('en-US', {
          timeZone: 'Asia/Shanghai',
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          hour12: false
        });

        const parts = formatter.formatToParts(utcDate);
        const year = parts.find(p => p.type === 'year').value;
        const month = parts.find(p => p.type === 'month').value;
        const day = parts.find(p => p.type === 'day').value;
        const hour = parseInt(parts.find(p => p.type === 'hour').value);
        const minute = parseInt(parts.find(p => p.type === 'minute').value);

        // Check if before 22:30 (Asia/Shanghai timezone)
        const isBefore2230 = hour < 22 || (hour === 22 && minute < 30);

        // Only process data before 22:30
        if (isBefore2230) {
          // Use Asia/Shanghai timezone date as key
          const dateKey = `${year}-${month}-${day}`;

          // Update if this day has no data yet, or if current data is later in time
          if (!dailyData[dateKey] || new Date(d.t) > new Date(dailyData[dateKey].t)) {
            dailyData[dateKey] = d;
          }
        }
      });

      // Convert to array and sort by time
      return Object.values(dailyData).sort((a, b) => a.t - b.t);
    } else if (chartTab === 'live') {
      // LIVE chart: Show all updates from the most recent trading session (22:30-05:00)
      // Live mode: Backend has already returned return curves for "current trading session + 0% starting point", frontend can use directly
      const sourceEquity = dataSource.equity;
      if (!sourceEquity || sourceEquity.length === 0) return [];
      return sourceEquity;
    }
    return dataSource.equity || [];
  }, [dataSource.equity, chartTab, virtualTime]);
  // Helper function to get daily indices for 'all' view
  const getDailyIndices = useMemo(() => {
    if (!equity || equity.length === 0) return new Set();
    const dailyIndices = new Set();
    const dailyData = {};

    const formatter = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });

    equity.forEach((d, idx) => {
      const utcDate = new Date(d.t);
      const parts = formatter.formatToParts(utcDate);
      const hour = parseInt(parts.find(p => p.type === 'hour').value);
      const minute = parseInt(parts.find(p => p.type === 'minute').value);

      // Check if before 22:30 (Asia/Shanghai timezone)
      const isBefore2230 = hour < 22 || (hour === 22 && minute < 30);

      // Only process data before 22:30
      if (isBefore2230) {
        const year = parts.find(p => p.type === 'year').value;
        const month = parts.find(p => p.type === 'month').value;
        const day = parts.find(p => p.type === 'day').value;
        const dateKey = `${year}-${month}-${day}`;

        if (!dailyData[dateKey] || new Date(d.t) > new Date(dailyData[dateKey].t)) {
          dailyData[dateKey] = { data: d, index: idx };
        }
      }
    });

    Object.values(dailyData).forEach(({ index }) => dailyIndices.add(index));
    return dailyIndices;
  }, [equity]);

  // Filter baseline, baseline_vw, momentum, strategies to match filteredEquity indices
  const filteredBaseline = useMemo(() => {
    const sourceBaseline = dataSource.baseline;
    if (!sourceBaseline || sourceBaseline.length === 0 || !equity || equity.length === 0) return [];
    if (chartTab === 'all') {
      return sourceBaseline.filter((_, idx) => getDailyIndices.has(idx));
    } else if (chartTab === 'live') {
      // Live mode: Use backend pre-processed baseline return curves directly
      return sourceBaseline;
    }
    return sourceBaseline;
  }, [dataSource.baseline, equity, chartTab, getDailyIndices, virtualTime]);
  const filteredBaselineVw = useMemo(() => {
    const sourceBaselineVw = dataSource.baseline_vw;
    if (!sourceBaselineVw || sourceBaselineVw.length === 0 || !equity || equity.length === 0) return [];
    if (chartTab === 'all') {
      return sourceBaselineVw.filter((_, idx) => getDailyIndices.has(idx));
    } else if (chartTab === 'live') {
      // Live mode: Use backend pre-processed baseline return curves directly
      return sourceBaselineVw;
    }
    return sourceBaselineVw;
  }, [dataSource.baseline_vw, equity, chartTab, getDailyIndices, virtualTime]);
  const filteredMomentum = useMemo(() => {
    const sourceMomentum = dataSource.momentum;
    if (!sourceMomentum || sourceMomentum.length === 0 || !equity || equity.length === 0) return [];
    if (chartTab === 'all') {
      return sourceMomentum.filter((_, idx) => getDailyIndices.has(idx));
    } else if (chartTab === 'live') {
      // Live mode: Use backend pre-processed momentum return curves directly
      return sourceMomentum;
    }
    return sourceMomentum;
  }, [dataSource.momentum, equity, chartTab, getDailyIndices, virtualTime]);
  const filteredStrategies = useMemo(() => {
    if (!strategies || strategies.length === 0 || !equity || equity.length === 0) return [];
    if (chartTab === 'all') {
      return strategies.filter((_, idx) => getDailyIndices.has(idx));
    } else if (chartTab === 'live') {
      const sessionStartTime = getRecentTradingSessionStart(virtualTime);
      return filterStrategyDataForLive(strategies, equity, sessionStartTime);
    }
    return strategies;
  }, [strategies, equity, chartTab, getDailyIndices, virtualTime]);

  const chartData = useMemo(() => {
    if (!filteredEquity || filteredEquity.length === 0) return [];

    try {
      // LIVE mode: Align all curves by timestamp with forward filling to ensure consistent point counts and aligned starting points
      if (chartTab === 'live') {
        // Build timestamp -> value mapping
        const toMap = (arr) => {
          const m = new Map();
          if (Array.isArray(arr)) {
            arr.forEach((p) => {
              if (p && typeof p.t === 'number' && typeof p.v === 'number') {
                m.set(p.t, p.v);
              }
            });
          }
          return m;
        };

        const portfolioMap = toMap(filteredEquity);
        const baselineMap = toMap(filteredBaseline);
        const baselineVwMap = toMap(filteredBaselineVw);
        const momentumMap = toMap(filteredMomentum);
        const strategyMap = toMap(filteredStrategies);

        // Collect all timestamps, sort by time
        const timestampSet = new Set();
        [filteredEquity, filteredBaseline, filteredBaselineVw, filteredMomentum, filteredStrategies].forEach(arr => {
          if (Array.isArray(arr)) {
            arr.forEach(p => {
              if (p && typeof p.t === 'number') timestampSet.add(p.t);
            });
          }
        });

        const timestamps = Array.from(timestampSet).sort((a, b) => a - b);
        if (timestamps.length === 0) return [];

        // Current values for forward filling, initialized to 0% to ensure starting point alignment
        let currentPortfolio = 0;
        let currentBaseline = 0;
        let currentBaselineVw = 0;
        let currentMomentum = 0;
        let currentStrategy = 0;

        return timestamps.map((t, idx) => {
          if (portfolioMap.has(t)) currentPortfolio = portfolioMap.get(t);
          if (baselineMap.has(t)) currentBaseline = baselineMap.get(t);
          if (baselineVwMap.has(t)) currentBaselineVw = baselineVwMap.get(t);
          if (momentumMap.has(t)) currentMomentum = momentumMap.get(t);
          if (strategyMap.has(t)) currentStrategy = strategyMap.get(t);

          const date = new Date(t);
          if (isNaN(date.getTime())) {
            console.warn('Invalid timestamp in live chart data:', t);
            return null;
          }

          return {
            index: idx,
            time:
              date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
              }) +
              ' ' +
              date.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                hour12: false,
              }),
            timestamp: t,
            portfolio: currentPortfolio,
            baseline: currentBaseline,
            baseline_vw: currentBaselineVw,
            momentum: currentMomentum,
            strategy: currentStrategy,
          };
        }).filter(item => item !== null);
      }

      // ALL mode: Keep the original index-based alignment logic
      return filteredEquity.map((d, idx) => {
        if (!d || typeof d.t !== 'number' || typeof d.v !== 'number') {
          console.warn('Invalid equity data point:', d);
          return null;
        }

        const date = new Date(d.t);
        if (isNaN(date.getTime())) {
          console.warn('Invalid timestamp:', d.t);
          return null;
        }

        const baselineVal = filteredBaseline?.[idx]
          ? (typeof filteredBaseline[idx] === 'object' ? filteredBaseline[idx].v : filteredBaseline[idx])
          : null;
        const baselineVwVal = filteredBaselineVw?.[idx]
          ? (typeof filteredBaselineVw[idx] === 'object' ? filteredBaselineVw[idx].v : filteredBaselineVw[idx])
          : null;
        const momentumVal = filteredMomentum?.[idx]
          ? (typeof filteredMomentum[idx] === 'object' ? filteredMomentum[idx].v : filteredMomentum[idx])
          : null;
        const strategyVal = filteredStrategies?.[idx]
          ? (typeof filteredStrategies[idx] === 'object' ? filteredStrategies[idx].v : filteredStrategies[idx])
          : null;

        return {
          index: idx,
          time:
            date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) +
            ' ' +
            date.toLocaleTimeString('en-US', {
              hour: '2-digit',
              minute: '2-digit',
              hour12: false,
            }),
          timestamp: d.t,
          portfolio: d.v,
          baseline: baselineVal || null,
          baseline_vw: baselineVwVal || null,
          momentum: momentumVal || null,
          strategy: strategyVal || null,
        };
      }).filter(item => item !== null); // Remove null entries
    } catch (error) {
      console.error('Error processing chart data:', error);
      return [];
    }
  }, [filteredEquity, filteredBaseline, filteredBaselineVw, filteredMomentum, filteredStrategies, chartTab]);

  const { yMin, yMax, xTickIndices } = useMemo(() => {
    if (chartData.length === 0) return { yMin: 0, yMax: 1, xTickIndices: [] };

    // Calculate min and max from all series
    const allValues = chartData.flatMap(d =>
      [d.portfolio, d.baseline, d.baseline_vw, d.momentum, d.strategy].filter(v => v !== null && isFinite(v))
    );

    if (allValues.length === 0) {
      return { yMin: 0, yMax: 1000000, xTickIndices: [] };
    }

    const dataMin = Math.min(...allValues);
    const dataMax = Math.max(...allValues);
    const range = dataMax - dataMin || 1;

    // For live mode (percentage data), use smaller padding and finer rounding
    // For all mode (dollar amounts), use larger padding and coarser rounding
    const isLiveMode = chartTab === 'live';

    const paddingFactor = isLiveMode ? range * 0.15 : range * 0.03;

    let yMinCalc = dataMin - paddingFactor;
    let yMaxCalc = dataMax + paddingFactor;

    // Smart rounding based on magnitude and mode
    const magnitude = Math.max(Math.abs(yMinCalc), Math.abs(yMaxCalc));
    let roundTo;

    if (isLiveMode) {
      // For percentage data, use much finer rounding
      if (magnitude >= 100) {
        roundTo = 10;
      } else if (magnitude >= 10) {
        roundTo = 1;
      } else if (magnitude >= 1) {
        roundTo = 0.1;
      } else {
        roundTo = 0.01;
      }
    } else {
      // For dollar amounts, use coarser rounding
      if (magnitude >= 1e6) {
        roundTo = 10000;
      } else if (magnitude >= 1e5) {
        roundTo = 5000;
      } else if (magnitude >= 1e4) {
        roundTo = 1000;
      } else {
        roundTo = 100;
      }
    }

    yMinCalc = Math.floor(yMinCalc / roundTo) * roundTo;
    yMaxCalc = Math.ceil(yMaxCalc / roundTo) * roundTo;

    // Stable range to prevent frequent updates
    if (stableYRange) {
      const { min: stableMin, max: stableMax } = stableYRange;
      const stableRange = stableMax - stableMin;
      const threshold = stableRange * 0.05;

      const needsUpdate =
        dataMin < (stableMin + threshold) ||
        dataMax > (stableMax - threshold);

      if (!needsUpdate) {
        yMinCalc = stableMin;
        yMaxCalc = stableMax;
      }
    }

    // Calculate x-axis tick indices
    const safeLength = Math.min(chartData.length, 10000);
    const targetTicks = Math.min(8, Math.max(5, Math.floor(safeLength / 10)));
    const step = Math.max(1, Math.floor(safeLength / (targetTicks - 1)));

    const indices = [];
    for (let i = 0; i < safeLength && indices.length < 100; i += step) {
      indices.push(i);
    }

    if (safeLength > 0 && indices[indices.length - 1] !== safeLength - 1) {
      indices.push(safeLength - 1);
    }

    return { yMin: yMinCalc, yMax: yMaxCalc, xTickIndices: indices };
  }, [chartData, stableYRange]);

  // Update stableYRange in useEffect to avoid infinite re-renders
  // Use functional update to avoid dependency on stableYRange
  useEffect(() => {
    if (yMin !== undefined && yMax !== undefined && yMin !== null && yMax !== null && isFinite(yMin) && isFinite(yMax)) {
      setStableYRange(prevRange => {
        if (!prevRange) {
          // Initialize stable range
          return { min: yMin, max: yMax };
        } else {
          // Check if update is needed (5% threshold)
          const stableRange = prevRange.max - prevRange.min;
          const threshold = stableRange * 0.05;
          const needsUpdate =
            yMin < (prevRange.min + threshold) ||
            yMax > (prevRange.max - threshold);

          if (needsUpdate) {
            return { min: yMin, max: yMax };
          }
          // No update needed, return previous range
          return prevRange;
        }
      });
    }
  }, [yMin, yMax]);

  if (!equity || equity.length === 0) {
    return (
      <div style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#cccccc',
        fontFamily: '"Courier New", monospace',
        fontSize: '12px'
      }}>
        NO DATA AVAILABLE
      </div>
    );
  }

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const isLiveMode = chartTab === 'live';
      return (
        <div style={{
          background: '#000000',
          border: '1px solid #333333',
          padding: '10px 14px',
          fontFamily: '"Courier New", monospace',
          fontSize: '10px',
          color: '#ffffff'
        }}>
          <div style={{ fontWeight: 700, marginBottom: '6px', fontSize: '11px' }}>
            {payload[0].payload.time}
          </div>
          {payload.map((entry, index) => (
            <div key={index} style={{ color: entry.color, marginTop: '2px' }}>
              <span style={{ fontWeight: 700 }}>{entry.name}:</span> {isLiveMode ? `${entry.value.toFixed(2)}%` : `$${formatNumber(entry.value)}`}            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  const CustomDot = ({ dataKey, ...props }) => {
    const { cx, cy, payload, index } = props;
    const isActive = activePoint === index;
    const isLastPoint = index === chartData.length - 1;

    // Only show dot for the last point
    if (!isLastPoint) {
      return null;
    }
    const colors = {
      portfolio: '#00C853',
      baseline: '#FF6B00',
      baseline_vw: '#9C27B0',
      momentum: '#2196F3',
      strategy: '#795548'
    };

    return (
      <circle
        cx={cx}
        cy={cy}
        r={isActive ? 6 : 8}
        fill={colors[dataKey]}
        stroke="#ffffff"
        strokeWidth={2}
        style={{ cursor: 'pointer' }}
        onMouseEnter={() => setActivePoint(index)}
        onMouseLeave={() => setActivePoint(null)}
        onClick={() => console.log('Clicked point:', { dataKey, ...payload })}
      />
    );
  };

  const CustomXAxisTick = ({ x, y, payload }) => {
    const shouldShow = xTickIndices.includes(payload.index);
    if (!shouldShow) return null;

    return (
      <g transform={`translate(${x},${y})`}>
        <text
          x={0}
          y={0}
          dy={16}
          textAnchor="middle"
          fill="#666666"
          fontSize="10px"
          fontFamily='"Courier New", monospace'
          fontWeight="700"
        >
          {payload.value}
        </text>
      </g>
    );
  };

  const CustomLegend = ({ payload }) => {
    if (!payload || payload.length === 0) return null;

    return (
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '16px',
        padding: '10px 0',
        position: 'relative',
        fontFamily: '"Courier New", monospace',
        fontSize: '11px',
        fontWeight: 700,
        justifyContent: 'center'
      }}>
        {payload.map((entry, index) => {
          const description = legendDescriptions[entry.value] || '';
          const isActive = legendTooltip === entry.value;

          return (
            <div
              key={index}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: 'pointer',
                position: 'relative',
                padding: '4px 8px',
                borderRadius: '4px',
                backgroundColor: isActive ? '#f0f0f0' : 'transparent',
                transition: 'background-color 0.2s',
                userSelect: 'none'
              }}
              onMouseEnter={() => setLegendTooltip(entry.value)}
              onMouseLeave={() => setLegendTooltip(null)}
              onClick={(e) => {
                e.stopPropagation();
                setLegendTooltip(isActive ? null : entry.value);
              }}
            >
              <div
                style={{
                  width: '14px',
                  height: '3px',
                  backgroundColor: entry.color,
                  border: 'none'
                }}
              />
              <span
                style={{
                  fontFamily: '"Courier New", monospace',
                  fontSize: '11px',
                  fontWeight: 700,
                  color: '#000000'
                }}
              >
                {entry.value}
              </span>
              {isActive && description && (
                <div
                  style={{
                    position: 'absolute',
                    bottom: '100%',
                    left: 0,
                    marginBottom: '8px',
                    padding: '8px 12px',
                    background: '#000000',
                    color: '#ffffff',
                    fontSize: '10px',
                    fontFamily: '"Courier New", monospace',
                    whiteSpace: 'normal',
                    maxWidth: '300px',
                    zIndex: 1000,
                    borderRadius: '4px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                    pointerEvents: 'none',
                    lineHeight: 1.4
                  }}
                >
                  {description}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart
        data={chartData}
        margin={{ top: 20, right: 30, bottom: 50, left: 60 }}
      >
        <XAxis
          dataKey="time"
          stroke="#666666"
          tick={<CustomXAxisTick />}
          interval={0}
        />
        <YAxis
          domain={[yMin, yMax]}
          stroke="#000000"
          style={{ fontFamily: '"Courier New", monospace', fontSize: '11px', fontWeight: 700 }}
          tick={{ fill: '#000000' }}
          tickFormatter={(value) => chartTab === 'live' ? `${value.toFixed(2)}%` : formatFullNumber(value)}
          width={75}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          content={<CustomLegend />}
        />

        {/* Portfolio line */}
        <Line
          type="linear"
          dataKey="portfolio"
          name="EvoTraders"
          stroke="#00C853"
          strokeWidth={2.5}
          dot={(props) => <CustomDot {...props} dataKey="portfolio" />}
          activeDot={{ r: 6, stroke: '#ffffff', strokeWidth: 2 }}
          isAnimationActive={false}
        />

        {/* Baseline Equal Weight */}
        {baseline && baseline.length > 0 && (
          <Line
            type="linear"
            dataKey="baseline"
            name="Buy & Hold (EW)"
            stroke="#FF6B00"
            strokeWidth={2}
            strokeDasharray="5 5"
            dot={(props) => <CustomDot {...props} dataKey="baseline" />}
            activeDot={{ r: 6, stroke: '#ffffff', strokeWidth: 2 }}
            isAnimationActive={false}
          />
        )}

        {/* Baseline Value Weighted */}
        {baseline_vw && baseline_vw.length > 0 && (
          <Line
            type="linear"
            dataKey="baseline_vw"
            name="Buy & Hold (VW)"
            stroke="#9C27B0"
            strokeWidth={2}
            strokeDasharray="8 4"
            dot={(props) => <CustomDot {...props} dataKey="baseline_vw" />}
            activeDot={{ r: 6, stroke: '#ffffff', strokeWidth: 2 }}
            isAnimationActive={false}
          />
        )}

        {/* Momentum Strategy */}
        {momentum && momentum.length > 0 && (
          <Line
            type="linear"
            dataKey="momentum"
            name="Momentum"
            stroke="#2196F3"
            strokeWidth={2}
            strokeDasharray="3 3"
            dot={(props) => <CustomDot {...props} dataKey="momentum" />}
            activeDot={{ r: 6, stroke: '#ffffff', strokeWidth: 2 }}
            isAnimationActive={false}
          />
        )}

        {/* Other Strategies */}
        {strategies && strategies.length > 0 && (
          <Line
            type="linear"
            dataKey="strategy"
            name="Strategy"
            stroke="#795548"
            strokeWidth={2}
            dot={(props) => <CustomDot {...props} dataKey="strategy" />}
            activeDot={{ r: 6, stroke: '#ffffff', strokeWidth: 2 }}
            isAnimationActive={false}
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}

