// Match the corresponding prompt key based on chatMode
export const promptJson = {
  // General
  general: [
    {
      title: "Alibaba Stock Price",
      describe: "What's the current stock price of Alibaba?",
    },
    {
      title: "Travel Plan to Hangzhou",
      describe:
        "Help generate a two-day travel plan to Hangzhou this weekend from Shanghai",
    },
    {
      title: "Alibaba Stock Report",
      describe:
        "Generate a detailed report about Alibaba stock price in US market",
    },
    {
      title: "AI Agents Courses on Coursera",
      describe:
        "On Coursera, find 3 popular beginner-level courses about AI agents",
    },
    {
      title: "AI Service Investment",
      describe:
        "Evaluate the investment outlook and primary risks for AI infrastructure software and services outside the core AI chip sector over the next year, driven by large language models and edge computing",
    },
    {
      title: "Fed Rate Outlook",
      describe:
        "Conduct a deep analysis of the expected Federal Reserve (Fed) interest rate cuts in early 2026",
    },
    {
      title: "Nvidia Future Earnings",
      describe: "Forecast Nvidia’s financial data for the coming year (2026)",
    },
    {
      title: "US-China Chip Impact",
      describe:
        "Perform a comprehensive analysis of the long-term impact of US-China trade tensions on the semiconductor supply chain.",
    },
  ],
  // Browser Use
  browser: [
    {
      title: "AI Agents Courses on Coursera",
      describe:
        "On Coursera, find 3 popular beginner-level courses about AI agents",
    },
    {
      title: "AI Service Investment",
      describe:
        "Evaluate the investment outlook and primary risks for AI infrastructure software and services outside the core AI chip sector over the next year, driven by large language models and edge computing",
    },
    {
      title: "Fed Rate Outlook",
      describe:
        "Conduct a deep analysis of the expected Federal Reserve (Fed) interest rate cuts in early 2026",
    },
    {
      title: "Nvidia Future Earnings",
      describe: "Forecast Nvidia’s financial data for the coming year (2026)",
    },
    {
      title: "US-China Chip Impact",
      describe:
        "Perform a comprehensive analysis of the long-term impact of US-China trade tensions on the semiconductor supply chain.",
    },
  ],
  // Deep Research
  dr: [
    {
      title: "AI Agents Courses on Coursera",
      describe:
        "On Coursera, find 3 popular beginner-level courses about AI agents",
    },
    {
      title: "AI Service Investment",
      describe:
        "Evaluate the investment outlook and primary risks for AI infrastructure software and services outside the core AI chip sector over the next year, driven by large language models and edge computing",
    },
    {
      title: "Fed Rate Outlook",
      describe:
        "Conduct a deep analysis of the expected Federal Reserve (Fed) interest rate cuts in early 2026",
    },
    {
      title: "Nvidia Future Earnings",
      describe: "Forecast Nvidia’s financial data for the coming year (2026)",
    },
    {
      title: "US-China Chip Impact",
      describe:
        "Perform a comprehensive analysis of the long-term impact of US-China trade tensions on the semiconductor supply chain.",
    },
  ],
  // Financial Analysis
  finance: [
    {
      title: "AI Agents Courses on Coursera",
      describe:
        "On Coursera, find 3 popular beginner-level courses about AI agents",
    },
    {
      title: "AI Service Investment",
      describe:
        "Evaluate the investment outlook and primary risks for AI infrastructure software and services outside the core AI chip sector over the next year, driven by large language models and edge computing",
    },
    {
      title: "Fed Rate Outlook",
      describe:
        "Conduct a deep analysis of the expected Federal Reserve (Fed) interest rate cuts in early 2026",
    },
    {
      title: "Nvidia Future Earnings",
      describe: "Forecast Nvidia’s financial data for the coming year (2026)",
    },
    {
      title: "US-China Chip Impact",
      describe:
        "Perform a comprehensive analysis of the long-term impact of US-China trade tensions on the semiconductor supply chain.",
    },
  ],
  // Data Science  The file needs to be placed in /src/assets/file
  // files: The files to the file to be uploaded. The files format is "/src/assets/file/filename" or ["/src/assets/file/filename"].
  ds: [
    {
      title: "Analysis of Disparities in Incident Allocation by Category",
      describe:
        "Find the discrepancy and imbalance in distribution of incidents assigned across categories",
      files: ["/src/assets/file/incident_records.csv"],
    },
    {
      title: "AI Agents Courses on Coursera",
      describe:
        "On Coursera, find 3 popular beginner-level courses about AI agents",
    },
    {
      title: "AI Service Investment",
      describe:
        "Evaluate the investment outlook and primary risks for AI infrastructure software and services outside the core AI chip sector over the next year, driven by large language models and edge computing",
    },
    {
      title: "Fed Rate Outlook",
      describe:
        "Conduct a deep analysis of the expected Federal Reserve (Fed) interest rate cuts in early 2026",
    },
    {
      title: "Nvidia Future Earnings",
      describe: "Forecast Nvidia’s financial data for the coming year (2026)",
    },
    {
      title: "US-China Chip Impact",
      describe:
        "Perform a comprehensive analysis of the long-term impact of US-China trade tensions on the semiconductor supply chain.",
    },
  ],
};

// If chatMode doesn't match any above, use the following
export const originalPromptsList = [
  {
    title: "Alibaba Stock Price",
    describe: "What's the current stock price of Alibaba?",
  },
  {
    title: "Travel Plan to Hangzhou",
    describe:
      "Help generate a two-day travel plan to Hangzhou this weekend from Shanghai",
  },
  {
    title: "Alibaba Stock Report",
    describe:
      "Generate a detailed report about Alibaba stock price in US market",
  },
  {
    title: "iPhone 17 vs 17 Pro",
    describe: "Give a detailed comparison between iPhone 17 and 17 Pro",
  },
  {
    title: "AI Agents Courses on Coursera",
    describe:
      "On Coursera, find 3 popular beginner-level courses about AI agents",
  },
  {
    title: "AI Service Investment",
    describe:
      "Evaluate the investment outlook and primary risks for AI infrastructure software and services outside the core AI chip sector over the next year, driven by large language models and edge computing",
  },
  {
    title: "Fed Rate Outlook",
    describe:
      "Conduct a deep analysis of the expected Federal Reserve (Fed) interest rate cuts in early 2026",
  },
  {
    title: "Nvidia Future Earnings",
    describe: "Forecast Nvidia's financial data for the coming year (2026)",
  },
  {
    title: "US-China Chip Impact",
    describe:
      "Perform a comprehensive analysis of the long-term impact of US-China trade tensions on the semiconductor supply chain.",
  },
];
