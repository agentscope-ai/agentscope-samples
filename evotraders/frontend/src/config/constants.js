/**
 * Application Configuration Constants
 */

// Centralized CDN asset URLs
export const CDN_ASSETS = {
  companyRoom: {
    agent_1: "https://img.alicdn.com/imgextra/i4/O1CN01Lr7SOl1lSExV0tOwv_!!6000000004817-2-tps-370-320.png",
    agent_2: "https://img.alicdn.com/imgextra/i3/O1CN017Kb8cY1VQNUmuK47o_!!6000000002647-2-tps-368-312.png",
    agent_3: "https://img.alicdn.com/imgextra/i3/O1CN010Fp55w1YqtGpVjgsS_!!6000000003111-2-tps-370-320.png",
    agent_4: "https://img.alicdn.com/imgextra/i3/O1CN01VnUsML1Dkq6fHw3ks_!!6000000000255-2-tps-366-316.png",
    agent_5: "https://img.alicdn.com/imgextra/i4/O1CN01o0kCQw1kyvbulBSl7_!!6000000004753-2-tps-370-314.png",
    agent_6: "https://img.alicdn.com/imgextra/i2/O1CN01cLV0zl1FI6ULAunTp_!!6000000000463-2-tps-368-320.png",
    team_logo: "https://img.alicdn.com/imgextra/i2/O1CN01n2S8aV25hcZhhNH95_!!6000000007558-2-tps-616-700.png",
    reme_logo: "https://img.alicdn.com/imgextra/i2/O1CN01FhncuT1Tqp8LfCaft_!!6000000002434-2-tps-915-250.png",
    full_room_dark: "https://img.alicdn.com/imgextra/i2/O1CN014sOgzK28re5haGC3X_!!6000000007986-2-tps-1248-832.png",
    full_room_with_roles_tech_style: "https://img.alicdn.com/imgextra/i1/O1CN01qhupIj1KU4vF3yoT2_!!6000000001166-2-tps-1248-832.png",
  },
  llmModelLogos: {
    "Zhipu AI": "https://img.alicdn.com/imgextra/i4/O1CN01PavE4h1SdFmbeUj6h_!!6000000002269-2-tps-92-92.png",
    "Alibaba": "https://img.alicdn.com/imgextra/i4/O1CN01mTs8oZ1gsHOj0xy7O_!!6000000004197-0-tps-204-192.jpg",
    "DeepSeek": "https://img.alicdn.com/imgextra/i3/O1CN01ocd9iO1D7S2qgEIXQ_!!6000000000169-2-tps-203-148.png",
    "Moonshot": "https://img.alicdn.com/imgextra/i3/O1CN01rFzJg01wE0QFHNGLy_!!6000000006275-0-tps-182-148.jpg",
    "Anthropic": "https://img.alicdn.com/imgextra/i4/O1CN01Sg8gbo1HKVnoU16rm_!!6000000000739-2-tps-148-148.png",
    "Google": "https://img.alicdn.com/imgextra/i1/O1CN01fZwVYk1caBHdzh9qh_!!6000000003616-0-tps-148-148.jpg",
    "OpenAI": "https://img.alicdn.com/imgextra/i3/O1CN01T1eaM8287qU0nZm91_!!6000000007886-2-tps-148-148.png",
    "Groq": "https://img.alicdn.com/imgextra/i1/O1CN01WxASMc1QjXzhVl3eQ_!!6000000002012-2-tps-170-148.png",
    "Ollama": "https://img.alicdn.com/imgextra/i1/O1CN01pN615e1i4vxLkQjVd_!!6000000004360-2-tps-204-192.png",
  },
  stockLogos: {
    "TSLA": "https://img.alicdn.com/imgextra/i4/O1CN01Pch4DD1DDrad8BQAQ_!!6000000000183-2-tps-128-128.png",
    "AMZN": "https://img.alicdn.com/imgextra/i3/O1CN01KMsfnU25Wd4MGSgue_!!6000000007534-2-tps-128-128.png",
    "NVDA": "https://img.alicdn.com/imgextra/i4/O1CN01Lq1eJr1mLeslgx6a0_!!6000000004938-2-tps-128-128.png",
    "GOOGL": "https://img.alicdn.com/imgextra/i2/O1CN01kjJJbb25B6SESkOCn_!!6000000007487-2-tps-128-128.png",
    "MSFT": "https://img.alicdn.com/imgextra/i4/O1CN01tdlNtQ1aFS7vHYfMG_!!6000000003300-2-tps-128-128.png",
    "AAPL": "https://img.alicdn.com/imgextra/i4/O1CN01r0GH0q1diiHHOwxiO_!!6000000003770-2-tps-128-128.png",
    "META": "https://img.alicdn.com/imgextra/i3/O1CN01pWAvHt1IkRqZoUG96_!!6000000000931-2-tps-130-96.png",
  }
};

// Derived asset shortcuts
export const ASSETS = {
  roomBg: CDN_ASSETS.companyRoom.full_room_with_roles_tech_style,
  teamLogo: CDN_ASSETS.companyRoom.team_logo,
  remeLogo: CDN_ASSETS.companyRoom.reme_logo,
};

// Stock logos mapping
export const STOCK_LOGOS = { ...CDN_ASSETS.stockLogos };

// Scene dimensions (actual image size)
export const SCENE_NATIVE = { width: 1248, height: 832 };

// Agent seat positions (percentage relative to image, origin at bottom-left)
// Format: { x: horizontal %, y: vertical % from bottom }
export const AGENT_SEATS = [
  { x: 0.44, y: 0.58 },  // portfolio_manager
  { x: 0.55, y: 0.58 },  // risk_manager
  { x: 0.33, y: 0.52 },  // valuation_analyst
  { x: 0.42, y: 0.42 },  // sentiment_analyst
  { x: 0.56, y: 0.42 },  // fundamentals_analyst
  { x: 0.61, y: 0.49 },  // technical_analyst
];

// Agent definitions with subtle color schemes (very light backgrounds)
export const AGENTS = [
  {
    id: "portfolio_manager",
    name: "Portfolio Manager",
    role: "Portfolio Manager",
    avatar: CDN_ASSETS.companyRoom.agent_1,
    colors: { bg: "#F9FDFF", text: "#1565C0", accent: "#1565C0" }
  },
  {
    id: "risk_manager",
    name: "Risk Manager",
    role: "Risk Manager",
    avatar: CDN_ASSETS.companyRoom.agent_2,
    colors: { bg: "#FFF8F8", text: "#C62828", accent: "#C62828" }
  },
  {
    id: "valuation_analyst",
    name: "Valuation Analyst",
    role: "Valuation Analyst",
    avatar: CDN_ASSETS.companyRoom.agent_3,
    colors: { bg: "#FAFFFA", text: "#2E7D32", accent: "#2E7D32" }
  },
  {
    id: "sentiment_analyst",
    name: "Sentiment Analyst",
    role: "Sentiment Analyst",
    avatar: CDN_ASSETS.companyRoom.agent_4,
    colors: { bg: "#FCFAFF", text: "#6A1B9A", accent: "#6A1B9A" }
  },
  {
    id: "fundamentals_analyst",
    name: "Fundamentals Analyst",
    role: "Fundamentals Analyst",
    avatar: CDN_ASSETS.companyRoom.agent_5,
    colors: { bg: "#FFFCF7", text: "#E65100", accent: "#E65100" }
  },
  {
    id: "technical_analyst",
    name: "Technical Analyst",
    role: "Technical Analyst",
    avatar: CDN_ASSETS.companyRoom.agent_6,
    colors: { bg: "#F9FEFF", text: "#00838F", accent: "#00838F" }
  },
];

// LLM logo URLs for reuse
export const LLM_MODEL_LOGOS = { ...CDN_ASSETS.llmModelLogos };

// Message type colors (very subtle backgrounds)
export const MESSAGE_COLORS = {
  system: { bg: "#FAFAFA", text: "#424242", accent: "#424242" },
  memory: { bg: "#F2FDFF", text: "#00838F", accent: "#00838F" },
  conference: { bg: "#F1F4FF", text: "#3949AB", accent: "#3949AB" }
};

// Helper function to get agent colors by ID or name
export const getAgentColors = (agentId, agentName) => {
  const agent = AGENTS.find(a => a.id === agentId || a.name === agentName);
  return agent?.colors || MESSAGE_COLORS.system;
};

// UI timing constants
export const BUBBLE_LIFETIME_MS = 8000;
export const CHART_MARGIN = { left: 60, right: 20, top: 20, bottom: 40 };
export const AXIS_TICKS = 5;

// WebSocket configuration
export const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8765";

// Initial ticker symbols (MAG7 companies)
export const INITIAL_TICKERS = [
  { symbol: "AAPL", price: null, change: null },
  { symbol: "MSFT", price: null, change: null },
  { symbol: "GOOGL", price: null, change: null },
  { symbol: "AMZN", price: null, change: null },
  { symbol: "NVDA", price: null, change: null },
  { symbol: "META", price: null, change: null },
  { symbol: "TSLA", price: null, change: null }
];

