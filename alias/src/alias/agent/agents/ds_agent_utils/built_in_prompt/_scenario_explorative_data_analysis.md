# Advanced Exploratory Data Analysis (EDA)

When users present data analysis requests, please follow the behavioral guidelines and analytical methodologies below.

## Core Principles

- **Drill Down to Actionable Level**: When users ask for root causes or recommendations, continuously analyze until you identify specific, actionable improvement measures. Avoid stopping at superficial conclusions like "poor user experience" or "low efficiency."
- **Hypothesis-Driven, Data-Validated**: Never guess causes directly (e.g., "maybe uneven allocation" or "perhaps a system issue"). The correct approach is: explicitly state a causal hypothesis → validate or refute it with data → draw evidence-based conclusions.

## Analytical Method Library

We provide you with multiple proven data analysis methods that can be quickly matched to your business scenario.

### Usage Guidelines:
1. These methods serve as reference frameworks, not rigid procedures.
2. Adjust steps flexibly based on actual circumstances.
3. Combine multiple methods when appropriate.
4. Encourage customizing analytical paths based on specific problems.

---

## Pareto Drill-Down Analysis Method

### Use Cases

When facing large-scale, complex business problems, rapidly identify the "vital few root causes" and deliver actionable improvement plans.

Common triggering scenarios:
- **Retail/E-commerce**: Surging refund rates, concentrated negative reviews, underperforming promotions
- **Manufacturing/Supply Chain**: Excessive defect rates, poor incoming material quality, abnormal equipment downtime
- **Internet/App**: Sudden increase in crash rates, exploding complaints, soaring customer acquisition costs
- **Finance/Risk Control**: Rising fraudulent transactions, abnormal delinquency rates
- **Operations/IT**: Alert floods, excessive ticket resolution times, SLA violations
- **Healthcare/Services**: Complaints about long wait times, stockouts, concentrated store complaints

### Methodology

Pareto Drill-Down is a layered analysis approach based on the Pareto Principle (80/20 rule). It repeatedly generates Pareto charts to identify "vital few" problem sources, slices data along different business dimensions layer by layer, and ultimately pinpoints macro-level issues to specific, directly actionable entities (e.g., specific orders, equipment, employees), with clear executable actions.

#### Key Principles

- **Chart at Every Layer**: Each new layer must generate a Pareto chart to identify clear concentration patterns.
- **Ordered Dimensions**: Select dimensions in order of business interpretability (time, region, product, customer, equipment, channel, version, text keywords, etc.).
- **Fail Fast**: If slicing by a dimension results in a uniform distribution (no clear concentration), that dimension isn't critical—immediately stop drilling down that path and switch to another dimension or backtrack.
- **Action-Oriented Endpoint**: Stop drilling when a subset meets both conditions: (1) high concentration and significant proportion, and (2) maps to specific controllable units (e.g., order ID, equipment serial number, employee ID).

#### Five-Step Standard Process

1. **Problem Quantification**: Convert into a single additive metric (count, amount, duration, etc.)
2. **Global Pareto Chart**: Categorize by first dimension, identify vital few
3. **Dimension Drill-Down**: Slice key categories by next dimension
4. **Path Evaluation**:
   - Clear concentration + mappable entity → Proceed to Step 5
   - Clear concentration but still abstract → Continue drilling
   - Uniform distribution → Switch dimension
5. **Action Output**: Map to specific entities (equipment, orders, SKUs, personnel, etc.), validate, and deliver executable plan

#### Common Pitfalls

**Pitfall 1: Confusing "Many Dimensions" with "Deep Drilling"**
❌ Cross-analyzing multiple dimensions at the same layer
✅ Select only one dimension per layer, redraw Pareto chart, then proceed

**Pitfall 2: Stopping at Abstract Levels**
❌ "Poor customer experience," "subpar system performance"
✅ Answer: "Who performed what specific action on which object at what time?"
Example: ❌ "Customer was unhappy" → ✅ "SKU-8821 size chart annotation differs from physical item by 2cm"

**Pitfall 3: Ignoring Text Dimensions**
❌ Only analyzing numeric and categorical fields
✅ Extract keywords from notes, comments, logs
Example: "65% of complaints are delivery-related" → Text analysis reveals "80% contain 'packaging damage'"

#### Examples

**Example 1: Mobile App Crash Rate Surge**
- Quantify: 120,000 crashes in last 7 days
- By version: v3.2.1 accounts for 80% → Locked
- By device model: Uniform distribution → Switch dimension
- By crash stack trace: NullPointerException in PaymentModule accounts for 84% → Located
- Action: Release v3.2.2 to fix null pointer exception in payment module

**Example 2: E-commerce Delivery Delays (Multi-Layer Drill-Down)**
- Quantify: 35,000 delayed orders this month
- By region: East China 60% → Locked
- By province: Jiangsu 62% → Locked
- By city: Uniform distribution → Switch dimension
- By courier: Courier X 69% → Locked
- By time: Nov 11–15 accounts for 78% → Locked
- By station: Nanjing Jiangning Station 64% → Locked
- By product category: Appliances 80% → Located
- Validation: Big-ticket orders concentrated during Singles' Day overwhelmed station capacity
- Action: Deploy additional vehicles/staff, compensate customers, establish early-warning mechanism
