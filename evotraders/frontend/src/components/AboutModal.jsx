import React, { useState } from 'react';
import Header from './Header.jsx';

export default function AboutModal({ onClose }) {
  const [isClosing, setIsClosing] = useState(false);
  const [language, setLanguage] = useState('en'); // 'en' or 'zh'

  const handleClose = () => {
    setIsClosing(true);
    // Wait for animation to complete before actually closing
    setTimeout(() => {
      onClose();
    }, 600); // Match animation duration
  };

  const overlayStyle = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: '#ffffff',
    zIndex: 9999,
    animation: isClosing
      ? 'collapseUp 0.6s cubic-bezier(0.4, 0, 0.2, 1) forwards'
      : 'expandDown 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
    transformOrigin: 'top center',
    overflowY: 'auto'
  };

  const contentStyle = {
    maxWidth: '900px',
    width: '90%',
    margin: '0 auto',
    textAlign: 'left',
    fontFamily: "'IBM Plex Mono', monospace",
    color: '#000000',
    lineHeight: 1.8,
    fontSize: '14px',
    letterSpacing: '0.01em',
    padding: '60px 20px 80px',
    animation: isClosing
      ? 'fadeOutContent 0.4s ease forwards'
      : 'fadeInContent 0.8s ease 0.3s backwards'
  };

  const highlight = {
    color: '#615CED',
    fontWeight: 600
  };

  const linkStyle = {
    color: '#615CED',
    textDecoration: 'none',
    borderBottom: '1px solid #615CED',
    transition: 'all 0.2s'
  };

  const closeHintStyle = {
    marginTop: '50px',
    fontSize: '11px',
    color: '#999',
    cursor: 'pointer',
    textAlign: 'center'
  };

  const languageSwitchStyle = {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: '25px',
    marginTop: '10px',
    gap: '0px',
    fontSize: '11px',
    fontFamily: "'IBM Plex Mono', monospace"
  };

  const getLangStyle = (isActive) => ({
    padding: '3px 8px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    background: isActive ? '#000' : '#fff',
    color: isActive ? '#fff' : '#000',
    border: 'none'
  });

  const content = {
    en: {

      question: "What happens if AI models don't compete with each other, but instead trade like a ",
      questionHighlight: "well-coordinated, high-performance team",
      questionEnd: "?",

      intro: "Not arena, but TEAM. We Hope that AI is no longer entering the financial markets as isolated models—it is stepping in as ",
      introHighlight1: "teams",
      introContinue: ", collaborating in one of the most challenging and noise-filled ",
      introHighlight2: "real-time environments",
      introContinue2: ".",


      point1Highlight: "✦ Complementary skills",
      point1: " - across multiple agents—data analysis, strategy generation, risk management—working together like a real trading desk, exchanging information through notifications and meetings.",

      point2Highlight: "✦ An agent system that continually evolves",
      point2: " — with memory modules that retain experience, learn from market feedback, reflect, and develop their own methodology over time.",

      point3Highlight: "✦ AI teams interacting with live markets",
      point3: " — learning from real-time data and making immediate decisions, not just theoretical simulations."
    },
    zh: {
      intro: "如果不是让模型彼此竞争，而是像一支高效协作的团队一样进行实时交易，会发生什么？",
      question: "这里不是竞技场，而是团队。我们希望Agents不再单打独斗，而是「组团」进入实时金融市场——这一十分困难且充满噪声的环境。",

      title1: "✦ 多智能体的技能互补",
      point1: "不同模型、不同角色的智能体像真实的金融团队一样协作，各自承担数据分析、策略生成、风险控制等职责。",

      title2: "✦ 能够持续进化的智能体系统",
      point2: "依托「记忆」模块，每个智能体都能跨回合保留经验，不断学习、反思与调整。我们希望能看到在长期实时交易中，Agent形成自己的独特方法论，而不是一次性偶然的推理。",

      title3: "✦ 实时参与市场的 AI Agents",
      point3: "Agents从实时行情中学习，并给予即时决策；不是纸上谈兵，而是面对市场的真实波动。"
    }
  };

  return (
    <>
      <style>{`
        @keyframes expandDown {
          from {
            transform: scaleY(0);
            opacity: 0;
          }
          to {
            transform: scaleY(1);
            opacity: 1;
          }
        }

        @keyframes collapseUp {
          from {
            transform: scaleY(1);
            opacity: 1;
          }
          to {
            transform: scaleY(0);
            opacity: 0;
          }
        }

        @keyframes fadeInContent {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes fadeOutContent {
          from {
            opacity: 1;
            transform: translateY(0);
          }
          to {
            opacity: 0;
            transform: translateY(-20px);
          }
        }
      `}</style>

      <div style={overlayStyle} onClick={handleClose}>
        {/* Header */}
        <div className="header" style={{
          animation: isClosing
            ? 'fadeOutContent 0.4s ease forwards'
            : 'fadeInContent 0.8s ease 0.3s backwards'
        }} onClick={(e) => e.stopPropagation()}>
          <Header
            onEvoTradersClick={handleClose}
            evoTradersLinkStyle="close"
          />
        </div>

        {/* Content */}
        <div style={contentStyle} onClick={(e) => e.stopPropagation()}>
          {/* Language Switch */}
          <div style={languageSwitchStyle}>
            <span
              style={getLangStyle(language === 'zh')}
              onClick={() => setLanguage('zh')}
            >
              中文
            </span>
            <span style={{ padding: '0 4px', color: '#999' }}>｜</span>
            <span
              style={getLangStyle(language === 'en')}
              onClick={() => setLanguage('en')}
            >
              EN
            </span>
          </div>

          {language === 'en' ? (
            // English Content
            <>

              <div style={{ marginBottom: '40px', fontSize: '15px', fontWeight: 600 }}>
                {content.en.question}
                <span style={highlight}>{content.en.questionHighlight}</span>
                {content.en.questionEnd}
              </div>

              <div style={{ marginBottom: '30px' }}>
                {content.en.intro}
                <span style={highlight}>{content.en.introHighlight1}</span>
                {content.en.introContinue}
                <span style={highlight}>{content.en.introHighlight2}</span>
                {content.en.introContinue2}
              </div>

              <div style={{ marginBottom: '25px' }}>
                <span style={highlight}>{content.en.point1Highlight}</span>
                {content.en.point1}
              </div>

              <div style={{ marginBottom: '25px' }}>
                <span style={highlight}>{content.en.point2Highlight}</span>
                {content.en.point2}
              </div>

              <div style={{ marginBottom: '40px' }}>
                <span style={highlight}>{content.en.point3Highlight}</span>
                {content.en.point3}
              </div>

              <div style={{ marginBottom: '25px', opacity: 0.7 }}>
                Everything is fully open-source. Built on{' '}
                <a
                  href="https://github.com/agentscope-ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={linkStyle}
                >
                  AgentScope
                </a>
                , using{' '}
                <a
                  href="https://github.com/agentscope-ai/ReMe"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={linkStyle}
                >
                  ReMe
                </a>
                {' '}for memory management.
              </div>
            </>
          ) : (
            // Chinese Content
            <>
              <div style={{ marginBottom: '30px' }}>
                {content.zh.intro}
              </div>

              <div style={{ marginBottom: '40px', fontSize: '15px', fontWeight: 600 }}>
                {content.zh.question}
              </div>

              <div style={{ marginBottom: '30px', fontSize: '14px', opacity: 0.8 }}>
                {content.zh.trying}
              </div>

              <div style={{ marginBottom: '30px' }}>
                <div style={{ ...highlight, marginBottom: '10px' }}>
                  {content.zh.title1}
                </div>
                <div style={{ marginBottom: '10px' }}>
                  {content.zh.point1}
                </div>
                <div style={{ fontSize: '13px', opacity: 0.7 }}>
                  {content.zh.point1Sub}
                </div>
              </div>

              <div style={{ marginBottom: '30px' }}>
                <div style={{ ...highlight, marginBottom: '10px' }}>
                  {content.zh.title2}
                </div>
                <div style={{ marginBottom: '10px' }}>
                  {content.zh.point2}
                </div>
                <div style={{ fontSize: '13px', opacity: 0.7 }}>
                  {content.zh.point2Sub}
                </div>
              </div>

              <div style={{ marginBottom: '30px' }}>
                <div style={{ ...highlight, marginBottom: '10px' }}>
                  {content.zh.title3}
                </div>
                <div>
                  {content.zh.point3}
                </div>
              </div>

              <div style={{ marginBottom: '10px', opacity: 0.7 }}>
                我们已经在github上开源。
              </div>
              <div style={{ marginBottom: '25px', opacity: 0.7 }}>
                EvoTraders 基于{' '}
                <a
                  href="https://github.com/agentscope-ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={linkStyle}
                >
                  AgentScope
                </a>
                {' '}搭建，并使用其中的{' '}
                <a
                  href="https://github.com/agentscope-ai/ReMe"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={linkStyle}
                >
                  ReMe
                </a>
                {' '}作为记忆管理核心。
              </div>

              <div style={{ marginBottom: '10px', fontSize: '14px' }}>
                你可以在此找到完整项目与示例：
              </div>
            </>
          )}

          <div style={{ marginTop: '40px' }}>
            <a
              href="https://github.com/agentscope-ai/agentscope-samples"
              target="_blank"
              rel="noopener noreferrer"
              style={linkStyle}
            >
              github.com/agentscope-ai/agentscope-samples
            </a>
          </div>

          <div style={closeHintStyle} onClick={handleClose}>
            {language === 'en' ? 'Click here to close' : '点击此处关闭'}
          </div>
        </div>
      </div>
    </>
  );
}

