import React, { useState, useRef, useImperativeHandle, forwardRef } from 'react';
import { formatTime } from '../utils/formatters';
import { MESSAGE_COLORS, getAgentColors, AGENTS, ASSETS } from '../config/constants';
import { getModelIcon } from '../utils/modelIcons';
import MarkdownModal from './MarkdownModal';

const isAnalyst = (agentId, agentName) => {
  if (agentId && agentId.includes('analyst')) return true;
  if (agentName && agentName.toLowerCase().includes('analyst')) return true;
  return false;
};

const isManager = (agentId, agentName) => {
  if (agentId && agentId.includes('manager')) return true;
  if (agentName && agentName.toLowerCase().includes('manager')) return true;
  return false;
};

const stripMarkdown = (text) => {
  return text
    .replace(/<think>[\s\S]*?<\/think>/gi, '')
    .replace(/#{1,6}\s+/g, '')
    .replace(/\*\*\*(.+?)\*\*\*/g, '$1')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/__(.+?)__/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/_(.+?)_/g, '$1')
    .replace(/`(.+?)`/g, '$1')
    .replace(/\[(.+?)\]\(.+?\)/g, '$1')
    .replace(/!\[.*?\]\(.+?\)/g, '')
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/^\s*\d+\.\s+/gm, '')
    .replace(/^\s*>\s+/gm, '')
    .replace(/\|/g, ' ')
    .replace(/^[-=]+$/gm, '');
};

const AgentFeed = forwardRef(({ feed, leaderboard }, ref) => {
  const feedContentRef = useRef(null);
  const [highlightedId, setHighlightedId] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState('all');
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const getAgentModelInfo = (agentId) => {
    if (!leaderboard || !agentId) return { modelName: null, modelProvider: null };
    const agentData = leaderboard.find(lb => lb.id === agentId || lb.agentId === agentId);
    return {
      modelName: agentData?.modelName,
      modelProvider: agentData?.modelProvider
    };
  };

  // Get agent info by name
  const getAgentInfoByName = (agentName) => {
    if (!leaderboard || !agentName) return null;
    const agentData = leaderboard.find(lb => lb.name === agentName || lb.agentName === agentName);
    if (!agentData) return null;
    return {
      agentId: agentData.id || agentData.agentId,
      modelName: agentData.modelName,
      modelProvider: agentData.modelProvider
    };
  };

  // Get unique agent names from feed (only registered agents in AGENTS)
  const getUniqueAgents = () => {
    const agentNamesInFeed = new Set();

    // Collect all agent names that appear in the feed
    feed.forEach(item => {
      if (item.type === 'message' && item.data?.agent) {
        agentNamesInFeed.add(item.data.agent);
      } else if (item.type === 'conference' && item.data?.messages) {
        item.data.messages.forEach(msg => {
          if (msg.agent) {
            agentNamesInFeed.add(msg.agent);
          }
        });
      }
    });

    // Filter to only include registered agents and sort by AGENTS array order
    const registeredAgentNames = AGENTS.map(a => a.name);
    return registeredAgentNames.filter(name => agentNamesInFeed.has(name));
  };

  // Filter feed based on selected agent
  const filteredFeed = selectedAgent === 'all'
    ? feed
    : feed.filter(item => {
        if (item.type === 'message') {
          return item.data?.agent === selectedAgent;
        } else if (item.type === 'conference') {
          return item.data?.messages?.some(msg => msg.agent === selectedAgent);
        }
        return false;
      });

  useImperativeHandle(ref, () => ({
    scrollToMessage: (bubble) => {
      if (!bubble || !feedContentRef.current) return;

      // Direct feedItemId match (used by replay mode)
      if (bubble.feedItemId) {
        const element = document.getElementById(`feed-item-${bubble.feedItemId}`);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
          setHighlightedId(bubble.feedItemId);
          setTimeout(() => setHighlightedId(null), 2000);
          return;
        }
      }

      const bubbleTimestamp = bubble.ts || bubble.timestamp;

      // Check if a message matches the bubble
      const isMatch = (msg, checkTime = true) => {
        const agentMatch = msg.agentId === bubble.agentId || msg.agent === bubble.agentName;
        if (!agentMatch || !checkTime) return agentMatch;
        return Math.abs(msg.timestamp - bubbleTimestamp) < 5000;
      };

      // Check if a feed item contains the target message
      const itemContains = (item, checkTime = true) => {
        if (item.type === 'message' && item.data) return isMatch(item.data, checkTime);
        if (item.type === 'conference' && item.data?.messages) {
          return item.data.messages.some(msg => isMatch(msg, checkTime));
        }
        return false;
      };

      // Find exact match first, then fallback to agent match
      const targetItem = feed.find(item => itemContains(item, true))
                      || feed.find(item => itemContains(item, false));

      if (targetItem) {
        const element = document.getElementById(`feed-item-${targetItem.id}`);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
          setHighlightedId(targetItem.id);
          setTimeout(() => setHighlightedId(null), 2000);
        }
      }
    }
  }), [feed]);

  const uniqueAgents = getUniqueAgents();

  // Get current selection display info
  const getCurrentSelectionInfo = () => {
    if (selectedAgent === 'all') {
      return { label: 'All Agents', modelInfo: null };
    }
    const agentInfo = getAgentInfoByName(selectedAgent);
    const modelInfo = agentInfo ? getModelIcon(agentInfo.modelName, agentInfo.modelProvider) : null;
    return { label: selectedAgent, modelInfo };
  };

  const currentSelection = getCurrentSelectionInfo();

  return (
    <div className="agent-feed">
      <div className="agent-feed-header">
        <h3 className="agent-feed-title">ACTIVITY FEED</h3>
        <div className="agent-filter-wrapper">
          <label className="agent-filter-label">Filter:</label>
          <div className="custom-select-wrapper">
            <button
              className="custom-select-trigger"
              onClick={() => setDropdownOpen(!dropdownOpen)}
              onBlur={() => setTimeout(() => setDropdownOpen(false), 200)}
            >
              <div className="custom-select-value">
                {currentSelection.modelInfo?.logoPath && (
                  <img
                    src={currentSelection.modelInfo.logoPath}
                    alt={currentSelection.modelInfo.provider}
                    className="select-model-icon"
                  />
                )}
                <span>{currentSelection.label}</span>
              </div>
              <span className="custom-select-arrow">▼</span>
            </button>
            {dropdownOpen && (
              <div className="custom-select-dropdown">
                <div
                  className={`custom-select-option ${selectedAgent === 'all' ? 'selected' : ''}`}
                  onClick={() => {
                    setSelectedAgent('all');
                    setDropdownOpen(false);
                  }}
                >
                  <span>All Agents</span>
                </div>
                {uniqueAgents.map(agent => {
                  const agentInfo = getAgentInfoByName(agent);
                  const modelInfo = agentInfo ? getModelIcon(agentInfo.modelName, agentInfo.modelProvider) : null;
                  return (
                    <div
                      key={agent}
                      className={`custom-select-option ${selectedAgent === agent ? 'selected' : ''}`}
                      onClick={() => {
                        setSelectedAgent(agent);
                        setDropdownOpen(false);
                      }}
                    >
                      {modelInfo?.logoPath && (
                        <img
                          src={modelInfo.logoPath}
                          alt={modelInfo.provider}
                          className="select-model-icon"
                        />
                      )}
                      <span>{agent}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="feed-content" ref={feedContentRef}>
        {filteredFeed.length === 0 && (
          <div className="empty-state">
            {selectedAgent === 'all'
              ? 'Waiting for system updates...'
              : `No messages from ${selectedAgent}`}
          </div>
        )}

        {filteredFeed.map(item => {
          const isHighlighted = item.id === highlightedId;
          if (item.type === 'conference') {
            return <ConferenceItem key={item.id} conference={item.data} itemId={item.id} isHighlighted={isHighlighted} getAgentModelInfo={getAgentModelInfo} />;
          } else if (item.type === 'memory') {
            return <MemoryItem key={item.id} memory={item.data} itemId={item.id} isHighlighted={isHighlighted} />;
          } else if (item.data?.agent === 'System') {
            return <SystemDivider key={item.id} message={item.data} itemId={item.id} />;
          } else {
            return <MessageItem key={item.id} message={item.data} itemId={item.id} isHighlighted={isHighlighted} getAgentModelInfo={getAgentModelInfo} />;
          }
        })}
      </div>
    </div>
  );
});

AgentFeed.displayName = 'AgentFeed';

export default AgentFeed;

function SystemDivider({ message, itemId }) {
  const content = String(message.content || '');

  return (
    <div
      id={`feed-item-${itemId}`}
      style={{
        display: 'flex',
        alignItems: 'center',
        padding: '12px 16px',
        gap: '12px',
      }}
    >
      <div style={{ flex: 1, height: '1px', backgroundColor: '#d0d0d0' }} />
      <span style={{
        fontSize: '11px',
        color: '#888',
        whiteSpace: 'normal',
        fontWeight: 500,
        letterSpacing: '0.3px',
      }}>
        {content}
      </span>
      <div style={{ flex: 1, height: '1px', backgroundColor: '#d0d0d0' }} />
    </div>
  );
}

function ConferenceItem({ conference, itemId, isHighlighted, getAgentModelInfo }) {
  const colors = MESSAGE_COLORS.conference;

  return (
    <div
      id={`feed-item-${itemId}`}
      className="feed-item"
      style={{
        backgroundColor: colors.bg,
        outline: isHighlighted ? '2px solid #615CED' : 'none',
        transition: 'outline 0.3s ease'
      }}
    >
      <div className="feed-item-header">
        <span className="feed-item-title" style={{ color: colors.text }}>
          CONFERENCE
        </span>
        {conference.isLive && <span className="feed-live-badge">● LIVE</span>}
        <span className="feed-item-time">{formatTime(conference.startTime)}</span>
      </div>

      <div className="feed-item-subtitle" style={{ color: colors.text }}>
        {conference.title}
      </div>

      <div className="conference-messages">
        {conference.messages.map((msg, idx) => (
          <ConferenceMessage key={idx} message={msg} getAgentModelInfo={getAgentModelInfo} />
        ))}
      </div>
    </div>
  );
}

function ConferenceMessage({ message, getAgentModelInfo }) {
  const [expanded, setExpanded] = useState(false);

  const agentColors = message.agent === 'System' ? MESSAGE_COLORS.system :
                      message.agent === 'Memory' ? MESSAGE_COLORS.memory :
                      getAgentColors(message.agentId, message.agent);

  const agentModelData = message.agentId && getAgentModelInfo ?
    getAgentModelInfo(message.agentId) :
    { modelName: null, modelProvider: null };
  const modelInfo = getModelIcon(agentModelData.modelName, agentModelData.modelProvider);

  let content = message.content || '';
  if (typeof content === 'object') {
    content = JSON.stringify(content, null, 2);
  } else {
    content = String(content);
  }

  const needsTruncation = content.length > 200;
  const MAX_EXPANDED_LENGTH = 10000;

  let displayContent = content;
  if (!expanded && needsTruncation) {
    displayContent = content.substring(0, 200) + '...';
  } else if (expanded && content.length > MAX_EXPANDED_LENGTH) {
    displayContent = content.substring(0, MAX_EXPANDED_LENGTH) + '...';
  }

  return (
    <div className="conf-message-item">
      <div className="conf-agent-name" style={{ color: agentColors.text, display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
        {modelInfo.logoPath && (
          <img
            src={modelInfo.logoPath}
            alt={modelInfo.provider}
            style={{
              width: '20px',
              height: '20px',
              borderRadius: '50%',
              objectFit: 'contain'
            }}
          />
        )}
        {message.agent}
      </div>
      <div className="conf-message-content-wrapper">
        <span className="conf-message-content">{stripMarkdown(displayContent)}</span>
        {needsTruncation && (
          <button
            className="conf-expand-btn"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? '« Less' : 'More »'}
          </button>
        )}
      </div>
    </div>
  );
}

function MemoryItem({ memory, itemId, isHighlighted }) {
  const [expanded, setExpanded] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);
  const colors = MESSAGE_COLORS.memory;

  let content = memory.content || '';
  if (typeof content === 'object') {
    content = JSON.stringify(content, null, 2);
  } else {
    content = String(content);
  }

  const needsTruncation = content.length > 200;
  const MAX_EXPANDED_LENGTH = 10000;

  let displayContent = content;
  if (!expanded && needsTruncation) {
    displayContent = content.substring(0, 200) + '...';
  } else if (expanded && content.length > MAX_EXPANDED_LENGTH) {
    displayContent = content.substring(0, MAX_EXPANDED_LENGTH) + '...';
  }

  const agentLabel = memory.agent && memory.agent !== 'Memory'
    ? `MEMORY · ${memory.agent}`
    : 'MEMORY';

  return (
    <div
      id={`feed-item-${itemId}`}
      className="feed-item"
      style={{
        background: 'linear-gradient(180deg, #F0F9FF 0%, #F6F4FF 100%)',
        border: '1px solid rgba(0, 194, 255, 0.15)',
        outline: isHighlighted ? '2px solid #615CED' : 'none',
        transition: 'outline 0.3s ease',
        position: 'relative'
      }}
    >
      <div className="feed-item-header">
        <span className="feed-item-title" style={{ color: colors.text, display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div
            style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
          >
            <a
              href="https://github.com/agentscope-ai/ReMe"
              target="_blank"
              rel="noopener noreferrer"
              style={{ display: 'flex', alignItems: 'center', textDecoration: 'none' }}
            >
              <img
                src={ASSETS.remeLogo}
                alt="ReMe"
                style={{
                  cursor: 'pointer',
                  height: '12px',
                  width: 'auto',
                  objectFit: 'contain',
                  userSelect: 'none',
                  transition: 'all 0.2s ease',
                  opacity: showTooltip ? 1 : 0.9,
                  filter: showTooltip ? 'brightness(1.1)' : 'none'
                }}
              />
              <span style={{
                fontSize: '11px',
                marginLeft: '4px',
                opacity: showTooltip ? 0.6 : 0,
                transform: showTooltip ? 'translate(0, 0)' : 'translate(-4px, 2px)',
                transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                color: colors.text,
                lineHeight: 1,
                pointerEvents: 'none'
              }}>
                ↗
              </span>
            </a>
          </div>
          <span style={{
            background: 'linear-gradient(90deg, #00C2FF 0%, #5C4CE0 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            color: 'transparent',
            fontWeight: 700
          }}>
            {agentLabel}
          </span>
        </span>
        <span className="feed-item-time">{formatTime(memory.timestamp)}</span>
      </div>

      <div style={{
        position: 'absolute',
        top: '34px',
        left: '12px',
        right: '12px',
        background: 'rgba(255, 255, 255, 0.9)',
        backdropFilter: 'blur(4px)',
        color: '#334155',
        padding: '10px 14px',
        borderRadius: '8px',
        fontSize: '12px',
        lineHeight: '1.5',
        zIndex: 100,
        boxShadow: '0 4px 12px rgba(0, 194, 255, 0.1)',
        opacity: showTooltip ? 1 : 0,
        visibility: showTooltip ? 'visible' : 'hidden',
        transition: 'all 0.2s ease',
        pointerEvents: 'none',
        border: '1px solid rgba(0, 194, 255, 0.15)'
      }}>
        <div style={{
          fontWeight: '700',
          marginBottom: '3px',
          background: 'linear-gradient(90deg, #00C2FF 0%, #5C4CE0 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
          color: 'transparent',
          display: 'inline-block'
        }}>
          Memory powered by AgentScope-ReMe
        </div>
        <div style={{ color: '#475569', opacity: 0.9 }}>
          Not only retrieves historical memories but also generates suggestions and hints for the current task based on latest context.
        </div>
      </div>

      <div className="feed-item-content">{stripMarkdown(displayContent)}</div>

      {needsTruncation && (
        <button
          className="feed-expand-btn"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? '« Less' : 'More »'}
        </button>
      )}
    </div>
  );
}

function MessageItem({ message, itemId, isHighlighted, getAgentModelInfo }) {
  const [expanded, setExpanded] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [isHovering, setIsHovering] = useState(false);

  const colors = message.agent === 'Memory' ? MESSAGE_COLORS.memory :
                 getAgentColors(message.agentId, message.agent);
  const title = message.agent === 'Memory' ? 'MEMORY' : message.agent || 'AGENT';

  const agentModelData = message.agentId && getAgentModelInfo ?
    getAgentModelInfo(message.agentId) :
    { modelName: null, modelProvider: null };
  const modelInfo = getModelIcon(agentModelData.modelName, agentModelData.modelProvider);

  const isAnalystAgent = isAnalyst(message.agentId, message.agent);
  const isManagerAgent = isManager(message.agentId, message.agent);
  const useModalView = isAnalystAgent || isManagerAgent;

  let content = message.content || '';
  if (typeof content === 'object') {
    content = JSON.stringify(content, null, 2);
  } else {
    content = String(content);
  }

  let displayContent = content;
  let showExpandButton = false;

  if (useModalView) {
    displayContent = content.length > 150 ? content.substring(0, 150) + '...' : content;
  } else {
    const needsTruncation = content.length > 200;
    const MAX_EXPANDED_LENGTH = 8000;

    if (!expanded && needsTruncation) {
      displayContent = content.substring(0, 200) + '...';
      showExpandButton = true;
    } else if (expanded && content.length > MAX_EXPANDED_LENGTH) {
      displayContent = content.substring(0, MAX_EXPANDED_LENGTH) + '...';
      showExpandButton = needsTruncation;
    } else {
      showExpandButton = needsTruncation;
    }
  }

  return (
    <>
      <div
        id={`feed-item-${itemId}`}
        className="feed-item"
        style={{
          backgroundColor: colors.bg,
          outline: isHighlighted ? '2px solid #615CED' : 'none',
          transition: 'outline 0.3s ease'
        }}
      >
        <div className="feed-item-header">
        <span className="feed-item-title" style={{ color: colors.text, display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
            {modelInfo.logoPath && message.agent !== 'Memory' && (
              <img
                src={modelInfo.logoPath}
                alt={modelInfo.provider}
                style={{
                  width: '20px',
                  height: '20px',
                  borderRadius: '50%',
                  objectFit: 'contain'
                }}
              />
            )}
            {title}
          </span>
          <span className="feed-item-time">{formatTime(message.timestamp)}</span>
        </div>

        <div className="feed-item-content">{stripMarkdown(displayContent)}</div>

        {useModalView && (
          <button
            onClick={() => setShowModal(true)}
            onMouseEnter={() => setIsHovering(true)}
            onMouseLeave={() => setIsHovering(false)}
            style={{
              marginTop: '8px',
              fontSize: '12px',
              color: isHovering ? '#000' : '#666',
              fontWeight: '700',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '4px 0',
              textAlign: 'left',
              width: '100%',
              outline: 'none'
            }}
          >
            📄 {isManagerAgent ? 'View decision log »' : 'View full report »'}
          </button>
        )}

        {showExpandButton && (
          <button
            className="feed-expand-btn"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? '« Less' : 'More »'}
          </button>
        )}
      </div>
      {useModalView && (
        <MarkdownModal
          isOpen={showModal}
          onClose={() => setShowModal(false)}
          content={content}
          agentName={message.agent}
          reportType={isManagerAgent ? 'decision' : 'analysis'}
        />
      )}
    </>
  );
}
