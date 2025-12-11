import { useState, useCallback, useRef } from "react";
import { AGENTS } from "../config/constants";

const MAX_FEED_ITEMS = 200;

/**
 * Generate a unique ID for feed items
 */
const generateId = (prefix = "item") => `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

/**
 * Convert raw event to a message object (for use within conferences or standalone)
 */
const eventToMessage = (evt) => {
  if (!evt || !evt.type) {
    return null;
  }

  const agent = AGENTS.find(a => a.id === evt.agentId);
  const timestamp = evt.timestamp || evt.ts || Date.now();

  switch (evt.type) {
  case "agent_message":
  case "conference_message":
    return {
      id: generateId("msg"),
      timestamp,
      agentId: evt.agentId,
      agent: agent?.name || evt.agentName || evt.agentId || "Agent",
      role: agent?.role || evt.role || "Agent",
      content: evt.content
    };

  case "memory":
    return {
      id: generateId("memory"),
      timestamp,
      agentId: evt.agentId,
      agent: agent?.name || evt.agentId || "Memory",
      role: "Memory",
      content: evt.content || evt.text || ""
    };

  case "system":
  case "day_start":
  case "day_complete":
  case "day_error":
    return {
      id: generateId("sys"),
      timestamp,
      agent: "System",
      role: "System",
      content: evt.content || `${evt.type}: ${evt.date || ""}`
    };

  default:
    return null;
  }
};

/**
 * Convert raw event to a standalone feed item (non-conference)
 */
const eventToFeedItem = (evt) => {
  if (!evt || !evt.type) {
    return null;
  }

  const message = eventToMessage(evt);
  if (!message) {
    return null;
  }

  if (evt.type === "memory") {
    return {
      type: "memory",
      id: message.id,
      data: {
        timestamp: message.timestamp,
        agentId: message.agentId,
        agent: message.agent,
        content: message.content
      }
    };
  }

  return {
    type: "message",
    id: message.id,
    data: message
  };
};

/**
 * Custom hook for processing feed events with conference aggregation
 */
export function useFeedProcessor() {
  const [feed, setFeed] = useState([]);

  // Active conference ref for real-time event handling
  const activeConferenceRef = useRef(null);

  /**
   * Process historical events from server
   * Events come in reverse chronological order (newest first)
   * So conference_end appears BEFORE conference_start in the array
   */
  const processHistoricalFeed = useCallback((events) => {
    if (!Array.isArray(events)) {
      console.warn("processHistoricalFeed: expected array, got", typeof events);
      return;
    }

    console.log("📋 Processing historical events:", events.length);

    const feedItems = [];
    let currentConference = null;

    // Process in chronological order (reverse the array)
    const chronological = [...events].reverse();

    for (const evt of chronological) {
      if (!evt || !evt.type) {
        continue;
      }

      try {
        if (evt.type === "conference_start") {
          // Start a new conference
          currentConference = {
            id: evt.conferenceId || generateId("conf"),
            title: evt.title || "Team Conference",
            startTime: evt.timestamp || evt.ts || Date.now(),
            endTime: null,
            isLive: false,
            participants: evt.participants || [],
            messages: []
          };
        } else if (evt.type === "conference_end") {
          // End current conference
          if (currentConference) {
            currentConference.endTime = evt.timestamp || evt.ts || Date.now();
            currentConference.isLive = false;
            feedItems.push({
              type: "conference",
              id: currentConference.id,
              data: currentConference
            });
            currentConference = null;
          }
        } else if (evt.type === "conference_message") {
          // Add to current conference if exists
          const message = eventToMessage(evt);
          if (message && currentConference) {
            currentConference.messages.push(message);
          } else if (message) {
            // Fallback: show as standalone message if no active conference
            feedItems.push({
              type: "message",
              id: message.id,
              data: message
            });
          }
        } else {
          // Non-conference events
          const feedItem = eventToFeedItem(evt);
          if (feedItem) {
            if (currentConference) {
              // Add to conference messages
              currentConference.messages.push(feedItem.data);
            } else {
              feedItems.push(feedItem);
            }
          }
        }
      } catch (error) {
        console.error("Error processing historical event:", evt.type, error);
      }
    }

    // If there's an unclosed conference, it's still live
    if (currentConference) {
      currentConference.isLive = true;
      feedItems.push({
        type: "conference",
        id: currentConference.id,
        data: currentConference
      });
      // Store as active for real-time updates
      activeConferenceRef.current = currentConference;
      console.log(`🔴 Restored active conference: ${currentConference.id} with ${currentConference.messages.length} messages`);
    }

    // Reverse back to newest-first order
    setFeed(feedItems.reverse());
    console.log(`✅ Processed ${feedItems.length} feed items from ${events.length} events`);
  }, []);

  /**
   * Process a single real-time event
   * Handles conference aggregation for live events
   */
  const processFeedEvent = useCallback((evt) => {
    if (!evt || !evt.type) {
      return null;
    }

    // Handle conference start
    if (evt.type === "conference_start") {
      const conference = {
        id: evt.conferenceId || generateId("conf"),
        title: evt.title || "Team Conference",
        startTime: evt.timestamp || evt.ts || Date.now(),
        endTime: null,
        isLive: true,
        participants: evt.participants || [],
        messages: []
      };
      activeConferenceRef.current = conference;
      setFeed(prev => [{ type: "conference", id: conference.id, data: conference }, ...prev].slice(0, MAX_FEED_ITEMS));
      return conference;
    }

    // Handle conference end
    if (evt.type === "conference_end") {
      const activeConf = activeConferenceRef.current;
      activeConferenceRef.current = null;

      if (activeConf) {
        const ended = {
          ...activeConf,
          endTime: evt.timestamp || evt.ts || Date.now(),
          isLive: false
        };
        setFeed(prev => prev.map(item =>
          item.type === "conference" && item.id === activeConf.id
            ? { ...item, data: ended }
            : item
        ));
        return ended;
      }
      return null;
    }

    // Handle conference message
    if (evt.type === "conference_message") {
      const message = eventToMessage(evt);
      if (!message) {
        return null;
      }

      const activeConf = activeConferenceRef.current;
      if (activeConf) {
        // Add to active conference
        const updated = {
          ...activeConf,
          messages: [...activeConf.messages, message]
        };
        activeConferenceRef.current = updated;
        setFeed(prev => prev.map(item =>
          item.type === "conference" && item.id === activeConf.id
            ? { ...item, data: updated }
            : item
        ));
        return message;
      } else {
        // No active conference, show as standalone
        const feedItem = { type: "message", id: message.id, data: message };
        setFeed(prev => [feedItem, ...prev].slice(0, MAX_FEED_ITEMS));
        return feedItem;
      }
    }

    // Handle other feed events (agent_message, memory, system, etc.)
    const feedEventTypes = ["agent_message", "memory", "system", "day_start", "day_complete", "day_error"];
    if (!feedEventTypes.includes(evt.type)) {
      return null;
    }

    const feedItem = eventToFeedItem(evt);
    if (!feedItem) {
      return null;
    }

    const activeConf = activeConferenceRef.current;
    if (activeConf) {
      // Add to active conference
      const updated = {
        ...activeConf,
        messages: [...activeConf.messages, feedItem.data]
      };
      activeConferenceRef.current = updated;
      setFeed(prev => prev.map(item =>
        item.type === "conference" && item.id === activeConf.id
          ? { ...item, data: updated }
          : item
      ));
      return feedItem.data;
    } else {
      // No active conference, add as standalone
      setFeed(prev => [feedItem, ...prev].slice(0, MAX_FEED_ITEMS));
      return feedItem;
    }
  }, []);

  /**
   * Add a system message to the feed
   */
  const addSystemMessage = useCallback((content) => {
    const message = {
      id: generateId("sys"),
      timestamp: Date.now(),
      agent: "System",
      role: "System",
      content
    };

    const activeConf = activeConferenceRef.current;
    if (activeConf) {
      const updated = {
        ...activeConf,
        messages: [...activeConf.messages, message]
      };
      activeConferenceRef.current = updated;
      setFeed(prev => prev.map(item =>
        item.type === "conference" && item.id === activeConf.id
          ? { ...item, data: updated }
          : item
      ));
    } else {
      const feedItem = { type: "message", id: message.id, data: message };
      setFeed(prev => [feedItem, ...prev].slice(0, MAX_FEED_ITEMS));
    }
    return message;
  }, []);

  /**
   * Clear all feed items and reset active conference
   */
  const clearFeed = useCallback(() => {
    setFeed([]);
    activeConferenceRef.current = null;
  }, []);

  /**
   * Check if there's an active conference
   */
  const hasActiveConference = useCallback(() => {
    return activeConferenceRef.current !== null;
  }, []);

  return {
    feed,
    setFeed,
    processHistoricalFeed,
    processFeedEvent,
    addSystemMessage,
    clearFeed,
    hasActiveConference
  };
}

export default useFeedProcessor;
