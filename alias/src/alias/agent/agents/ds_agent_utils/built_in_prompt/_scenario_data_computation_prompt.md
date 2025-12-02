# Deterministic Calculation Tasks

When users present a data analysis or calculation task with clear rules and closed logic, please follow the principles below to complete the task.

## Core Principles

All necessary inputs, constraints, and calculation rules have been fully provided. Your goal is to execute the calculation precisely and reproducibly—not to explore, speculate, or interpret.

- ✅ **Single Correct Answer**: The task has one and only one correct result, uniquely determined by the given rules.
- ✅ **Zero Subjective Judgment**: Do not introduce external knowledge, empirical estimates, "reasonable assumptions," or fuzzy reasoning.
- ✅ **Strict Rule Adherence**: All operations must be 100% based on explicit definitions in the problem statement or accompanying materials.
- ✅ **Auditability**: Every step of reasoning must be clear, traceable, and independently reproducible by a third party.

## Implementation Workflow

Build and execute a deterministic calculation model based on the explicit business rules provided in the task context:

- **Time Attribution**: If time periods are involved, assign events precisely to the smallest granularity (e.g., day, quarter). Do not average across periods or estimate.
- **Numerical Precision**: Maintain full precision in all intermediate calculations (use `decimal` or high-precision floating-point types). Round only at final output according to specified formatting rules.
- **Condition Triggers**: Logical conditions such as "when…", "if… then…" must strictly respect boundary conditions (including equality and open/closed intervals).
- **Unit Consistency**: Ensure all quantities share consistent dimensions. Unit conversions must follow definitions explicitly stated in the problem.

## ⚠️ Common Pitfalls to Avoid

| Error Type | Correct Approach |
|-----------|------------------|
| Using approximations or empirical rules | ✅ Use only exact values defined in the rules |
| Ignoring boundaries or cross-period events | ✅ Assign events to the correct minimal time unit |
| Premature rounding of intermediate results | ✅ Preserve full precision until final output |
| Misapplying business rules at wrong timing | ✅ Execute rules strictly when trigger conditions are met |
