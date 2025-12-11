import React, { useState, useEffect, useRef } from 'react';
import { LLM_MODEL_LOGOS } from '../config/constants';

export default function RulesView() {
  const [language, setLanguage] = useState('en'); // 'en' or 'zh'
  const [scale, setScale] = useState(1);
  const containerRef = useRef(null);
  const contentRef = useRef(null);

  // Auto-scale content to fit container without scrolling
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current && contentRef.current) {
        const containerHeight = containerRef.current.clientHeight;
        const contentHeight = contentRef.current.scrollHeight;

        if (contentHeight > containerHeight) {
          const newScale = containerHeight / contentHeight;
          setScale(Math.max(newScale * 0.95, 0.5)); // Min scale 0.5, with 95% of available space
        } else {
          setScale(1);
        }
      }
    };

    // Initial resize
    handleResize();

    // Listen to window resize
    window.addEventListener('resize', handleResize);

    // Observe content changes
    const observer = new ResizeObserver(handleResize);
    if (contentRef.current) {
      observer.observe(contentRef.current);
    }

    return () => {
      window.removeEventListener('resize', handleResize);
      observer.disconnect();
    };
  }, [language]);

  const containerStyle = {
    width: '100%',
    height: '100%',
    overflow: 'hidden',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#FFFFFF',
    padding: '10px'
  };

  const contentWrapperStyle = {
    transform: `scale(${scale})`,
    transformOrigin: 'center center',
    transition: 'transform 0.3s ease',
    width: '100%',
    maxWidth: '900px'
  };

  const innerContentStyle = {
    color: '#000000',
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: '13px',
    lineHeight: '1.6',
    letterSpacing: '0.01em',
    padding: '0 10px'
  };

  const highlight = {
    color: '#000000',
    fontWeight: 700
  };

  const sectionTitleStyle = {
    color: '#615CED',
    fontSize: '16px',
    fontWeight: 700,
    marginBottom: '8px',
    marginTop: '12px',
    marginLeft: '-10px',
    marginRight: '-10px',
    width: 'calc(100% + 20px)',
    padding: '8px 10px',
    backgroundColor: '#FFFFFF',
    letterSpacing: '0.5px',
    boxSizing: 'border-box'
  };

  const subsectionStyle = {
    marginBottom: '8px',
    paddingLeft: '10px',
    borderLeft: '2px solid #CCCCCC'
  };

  const linkStyle = {
    color: '#615CED',
    textDecoration: 'none',
    borderBottom: '1px solid #615CED',
    transition: 'all 0.2s'
  };

  const languageSwitchStyle = {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: '12px',
    gap: '0px',
    fontSize: '11px',
    fontFamily: "'IBM Plex Mono', monospace"
  };

  const getLangStyle = (isActive) => ({
    padding: '4px 10px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    background: isActive ? '#000000' : 'transparent',
    color: isActive ? '#FFFFFF' : '#666666',
    border: 'none',
    borderRadius: '2px'
  });

  const llmLogos = [
    { name: 'Alibaba', file: 'Alibaba.jpeg', label: 'Qwen', url: LLM_MODEL_LOGOS['Alibaba'] },
    { name: 'DeepSeek', file: 'DeepSeek.png', label: 'DeepSeek', url: LLM_MODEL_LOGOS['DeepSeek'] },
    { name: 'Moonshot', file: 'Moonshot.jpeg', label: 'Moonshot', url: LLM_MODEL_LOGOS['Moonshot'] },
    { name: 'Zhipu AI', file: 'Zhipu AI.png', label: 'Zhipu AI', url: LLM_MODEL_LOGOS['Zhipu AI'] }
  ];

  const content = {
    en: {
      section1Title: "Agent Setup",
      pmRole: "Portfolio Manager",
      pmDesc: "Makes final trading decisions and orchestrates team collaboration",
      rmRole: "Risk Manager",
      rmDesc: "Monitors portfolio risk and enforces risk limits",
      analystsRole: "Analysts",
      analystsDesc: "Conduct specialized research with different tools and AI models:",
      analysts: [
        { name: "Valuation Analyst", model: "Moonshot", modelKey: "Moonshot" },
        { name: "Sentiment Analyst", model: "Qwen", modelKey: "Alibaba" },
        { name: "Fundamentals Analyst", model: "DeepSeek", modelKey: "DeepSeek" },
        { name: "Technical Analyst", model: "Zhipu AI", modelKey: "Zhipu AI" }
      ],

      section2Title: "Agent Decision Mechanism",

      tradingProcess: "Daily Trading Process",
      tradingDesc: "Agents trade on a daily frequency while continuously tracking portfolio performance. Before each day's final trading decision, agents go through three key phases:",

      analysisPhase: "• Analysis Phase",
      analysisDesc: "All agents independently analyze information and form judgments based on their specialized tools.",

      communicationPhase: "• Communication Phase",
      commIntro: "Multiple communication channels enable effective collaboration: 1v1 Private Chat / 1vN Notification / NvN Conference",

      decisionPhase: "• Decision Phase",
      decisionDesc: "Portfolio Manager aggregates all information and makes the final team trading decision. The original trading signals from analysts are only used for individual-level ranking.",

      reflectionTitle: "Learning & Evolution",
      reflectionDesc: "Agents reflect on daily investment performance, summarize insights, and store them in ",
      remeLink: "ReMe",
      reflectionDesc2: " memory framework for continuous improvement.",

      section3Title: "Performance Evaluation",

      chartTitle: "• Performance Chart",
      chartDesc: "Track portfolio equity curve vs. benchmarks (equal-weight, value-weighted, momentum). Use this to assess overall strategy effectiveness.",

      rankingTitle: "• Analyst Rankings",
      rankingDesc: "Click avatars in Trading Room to view analyst performance (Win Rate, Bull/Bear Win Rate). Use this to understand which analysts provide the most valuable insights.",

      statsTitle: "• Statistics",
      statsDesc: "Detailed holdings and trade history. Use this for in-depth analysis of position management and execution quality.",

      callToAction: "Fork on ",
      repoLink: "GitHub",
      callToAction2: " to customize!"
    },
    zh: {
      section1Title: "Agent 设定",
      pmRole: "Portfolio Manager",
      pmDesc: "负责最终交易决策和团队协作",
      rmRole: "Risk Manager",
      rmDesc: "监控组合风险并执行风险限制",
      analystsRole: "Analysts",
      analystsDesc: "使用不同工具和 AI 模型进行专业研究：",
      analysts: [
        { name: "Valuation Analyst", model: "Moonshot", modelKey: "Moonshot" },
        { name: "Sentiment Analyst", model: "Qwen", modelKey: "Alibaba" },
        { name: "Fundamentals Analyst", model: "DeepSeek", modelKey: "DeepSeek" },
        { name: "Technical Analyst", model: "Zhipu AI", modelKey: "Zhipu AI" }
      ],

      section2Title: "Agent 决策机制",

      tradingProcess: "交易流程",
      tradingDesc: "Agents 进行日频交易并持续跟踪组合净值。每天最终交易决策前，agents 经历三个关键阶段：",

      analysisPhase: "• 分析阶段",
      analysisDesc: "所有 agents 根据各自的工具和信息独立分析并形成判断。",

      communicationPhase: "• 沟通阶段",
      commIntro: "提供了多种沟通渠道：1v1 私聊 / 1vN 通知 / NvN 会议",

      decisionPhase: "• 决策阶段",
      decisionDesc: "由 portfolio manager 汇总所有信息，并给出最终的团队交易。analysts 给出的原始交易信号仅做个人维度的排名。",

      reflectionTitle: "学习与进化",
      reflectionDesc: "Agents 根据当日实际收益反思决策、总结经验，并存入 ",
      remeLink: "ReMe",
      reflectionDesc2: " 记忆框架以持续改进。",

      section3Title: "收益评估",

      chartTitle: "• 业绩图表",
      chartDesc: "追踪组合收益曲线 vs. 基准策略（等权、市值加权、动量）。用于评估整体策略有效性。",

      rankingTitle: "• 分析师排名",
      rankingDesc: "在 Trading Room 点击头像查看分析师表现（胜率、牛/熊市胜率）。用于了解哪些分析师提供最有价值的洞察。",

      statsTitle: "• 统计数据",
      statsDesc: "详细的持仓和交易历史。用于深入分析仓位管理和执行质量。",

      callToAction: "在 ",
      repoLink: "GitHub",
      callToAction2: " 上 fork 并自定义！"
    }
  };

  return (
    <div ref={containerRef} style={containerStyle}>
      <div ref={contentRef} style={contentWrapperStyle}>
        <div style={innerContentStyle}>
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
              {/* Section 1: Agent Setup */}
              <div style={sectionTitleStyle}>{content.en.section1Title}</div>

              {/* Roles */}
              <div style={{ marginBottom: '8px', fontSize: '12px' }}>
                <div style={{ marginBottom: '3px' }}>
                  <span style={{ fontWeight: 600 }}>{content.en.pmRole}:</span> {content.en.pmDesc}
                </div>
                <div style={{ marginBottom: '3px' }}>
                  <span style={{ fontWeight: 600 }}>{content.en.rmRole}:</span> {content.en.rmDesc}
                </div>
                <div style={{ marginBottom: '3px' }}>
                  <span style={{ fontWeight: 600 }}>{content.en.analystsRole}:</span> {content.en.analystsDesc}
                </div>
              </div>

              {/* Analysts with AI Models */}
              <div style={{ marginLeft: '10px', marginBottom: '8px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '3px 14px', fontSize: '11px' }}>
                {content.en.analysts.map(analyst => {
                  const logo = llmLogos.find(l => l.name === analyst.modelKey);
                  return (
                    <div key={analyst.name} style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}>
                      {logo && (
                        <img
                          src={logo.url}
                          alt={logo.label}
                          style={{
                            height: '16px',
                            width: 'auto',
                            objectFit: 'contain'
                          }}
                        />
                      )}
                      <span style={{ fontWeight: 600 }}>{analyst.name}</span>
                      <span style={{ color: '#666' }}>- {analyst.model}</span>
                    </div>
                  );
                })}
              </div>

              <div style={{ marginBottom: '10px', fontSize: '11px', fontStyle: 'italic', opacity: 0.8 }}>
                {content.en.callToAction}
                <a
                  href="https://github.com/agentscope-ai/agentscope-samples"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={linkStyle}
                >
                  {content.en.repoLink}
                </a>
                {content.en.callToAction2}
              </div>

              {/* Section 2: Agent Decision Mechanism */}
              <div style={sectionTitleStyle}>{content.en.section2Title}</div>

              <div style={{ marginBottom: '6px' }}>
                <div style={{ fontWeight: 600, marginBottom: '3px' }}>{content.en.tradingProcess}</div>
                <div style={{ marginBottom: '6px', fontSize: '12px' }}>{content.en.tradingDesc}</div>

                <div style={subsectionStyle}>
                  <div style={{ marginBottom: '4px', fontSize: '12px' }}>
                    <span style={highlight}>{content.en.analysisPhase.replace('• ', '')}:</span> {content.en.analysisDesc}
                  </div>

                  <div style={{ marginBottom: '4px', fontSize: '12px' }}>
                    <span style={highlight}>{content.en.communicationPhase.replace('• ', '')}:</span> {content.en.commIntro}
                  </div>

                  <div style={{ fontSize: '12px' }}>
                    <span style={highlight}>{content.en.decisionPhase.replace('• ', '')}:</span> {content.en.decisionDesc}
                  </div>
                </div>
              </div>

              <div style={{ marginBottom: '10px' }}>
                <div style={{ fontWeight: 600, marginBottom: '3px' }}>{content.en.reflectionTitle}</div>
                <div style={{ fontSize: '12px' }}>
                  {content.en.reflectionDesc}
                  <a
                    href="https://github.com/agentscope-ai/ReMe"
                    target="_blank"
                    rel="noopener noreferrer"
                    style={linkStyle}
                  >
                    {content.en.remeLink}
                  </a>
                  {content.en.reflectionDesc2}
                </div>
              </div>

              {/* Section 3: Performance Evaluation */}
              <div style={sectionTitleStyle}>{content.en.section3Title}</div>
              <div style={subsectionStyle}>
                <div style={{ marginBottom: '3px', fontSize: '12px' }}>
                  <span style={{ fontWeight: 600 }}>{content.en.chartTitle.replace('• ', '')}:</span> {content.en.chartDesc}
                </div>
                <div style={{ marginBottom: '3px', fontSize: '12px' }}>
                  <span style={{ fontWeight: 600 }}>{content.en.rankingTitle.replace('• ', '')}:</span> {content.en.rankingDesc}
                </div>
                <div style={{ fontSize: '12px' }}>
                  <span style={{ fontWeight: 600 }}>{content.en.statsTitle.replace('• ', '')}:</span> {content.en.statsDesc}
                </div>
              </div>
            </>
          ) : (
            // Chinese Content
            <>
              {/* 第一部分：Agent 设定 */}
              <div style={sectionTitleStyle}>{content.zh.section1Title}</div>

              {/* 角色 */}
              <div style={{ marginBottom: '8px', fontSize: '12px' }}>
                <div style={{ marginBottom: '3px' }}>
                  <span style={{ fontWeight: 600 }}>{content.zh.pmRole}:</span> {content.zh.pmDesc}
                </div>
                <div style={{ marginBottom: '3px' }}>
                  <span style={{ fontWeight: 600 }}>{content.zh.rmRole}:</span> {content.zh.rmDesc}
                </div>
                <div style={{ marginBottom: '3px' }}>
                  <span style={{ fontWeight: 600 }}>{content.zh.analystsRole}:</span> {content.zh.analystsDesc}
                </div>
              </div>

              {/* Analysts 与 AI 模型 */}
              <div style={{ marginLeft: '10px', marginBottom: '8px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '3px 14px', fontSize: '11px' }}>
                {content.zh.analysts.map(analyst => {
                  const logo = llmLogos.find(l => l.name === analyst.modelKey);
                  return (
                    <div key={analyst.name} style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}>
                      {logo && (
                        <img
                          src={logo.url}
                          alt={logo.label}
                          style={{
                            height: '16px',
                            width: 'auto',
                            objectFit: 'contain'
                          }}
                        />
                      )}
                      <span style={{ fontWeight: 600 }}>{analyst.name}</span>
                      <span style={{ color: '#666' }}>- {analyst.model}</span>
                    </div>
                  );
                })}
              </div>

              <div style={{ marginBottom: '10px', fontSize: '11px', fontStyle: 'italic', opacity: 0.8 }}>
                {content.zh.callToAction}
                <a
                  href="https://github.com/agentscope-ai/agentscope-samples"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={linkStyle}
                >
                  {content.zh.repoLink}
                </a>
                {content.zh.callToAction2}
              </div>

              {/* 第二部分：Agent 决策机制 */}
              <div style={sectionTitleStyle}>{content.zh.section2Title}</div>

              <div style={{ marginBottom: '6px' }}>
                <div style={{ fontWeight: 600, marginBottom: '3px' }}>{content.zh.tradingProcess}</div>
                <div style={{ marginBottom: '6px', fontSize: '12px' }}>{content.zh.tradingDesc}</div>

                <div style={subsectionStyle}>
                  <div style={{ marginBottom: '4px', fontSize: '12px' }}>
                    <span style={highlight}>{content.zh.analysisPhase.replace('• ', '')}:</span> {content.zh.analysisDesc}
                  </div>

                  <div style={{ marginBottom: '4px', fontSize: '12px' }}>
                    <span style={highlight}>{content.zh.communicationPhase.replace('• ', '')}:</span> {content.zh.commIntro}
                  </div>

                  <div style={{ fontSize: '12px' }}>
                    <span style={highlight}>{content.zh.decisionPhase.replace('• ', '')}:</span> {content.zh.decisionDesc}
                  </div>
                </div>
              </div>

              <div style={{ marginBottom: '10px' }}>
                <div style={{ fontWeight: 600, marginBottom: '3px' }}>{content.zh.reflectionTitle}</div>
                <div style={{ fontSize: '12px' }}>
                  {content.zh.reflectionDesc}
                  <a
                    href="https://github.com/agentscope-ai/ReMe"
                    target="_blank"
                    rel="noopener noreferrer"
                    style={linkStyle}
                  >
                    {content.zh.remeLink}
                  </a>
                  {content.zh.reflectionDesc2}
                </div>
              </div>

              {/* 第三部分：收益评估 */}
              <div style={sectionTitleStyle}>{content.zh.section3Title}</div>
              <div style={subsectionStyle}>
                <div style={{ marginBottom: '3px', fontSize: '12px' }}>
                  <span style={{ fontWeight: 600 }}>{content.zh.chartTitle.replace('• ', '')}:</span> {content.zh.chartDesc}
                </div>
                <div style={{ marginBottom: '3px', fontSize: '12px' }}>
                  <span style={{ fontWeight: 600 }}>{content.zh.rankingTitle.replace('• ', '')}:</span> {content.zh.rankingDesc}
                </div>
                <div style={{ fontSize: '12px' }}>
                  <span style={{ fontWeight: 600 }}>{content.zh.statsTitle.replace('• ', '')}:</span> {content.zh.statsDesc}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
