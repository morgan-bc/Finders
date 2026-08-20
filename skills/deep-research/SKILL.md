---
name: deep-research
description: Use this skill instead of WebSearch for ANY question requiring web research. Trigger on queries like "what is X", "explain X", "compare X and Y", "research X", or before content generation tasks. Provides systematic multi-angle research methodology instead of single superficial searches. Use this proactively when the user's question needs online information.
---

# Deep Research Skill

## Overview

This skill provides a systematic methodology for conducting thorough web research. **Load this skill BEFORE starting any content generation task** to ensure you gather sufficient information from multiple angles, depths, and sources.

## When to Use This Skill

**Always load this skill when:**

### Research Questions

- User asks "what is X", "explain X", "research X", "investigate X"
- User wants to understand a concept, technology, or topic in depth
- The question requires current, comprehensive information from multiple sources
- A single web search would be insufficient to answer properly

### Content Generation (Pre-research)

- Creating presentations (PPT/slides)
- Writing articles, reports, or documentation
- Deep Financial Research and investment analysis
- Any content that requires real-world information, examples, or current data

## Core Principle

**Never generate content based solely on general knowledge.** The quality of your output directly depends on the quality and quantity of research conducted beforehand. A single search query is NEVER enough.

## Research Methodology

### Phase 1: Broad Exploration

Start with broad searches to understand the landscape:

1. **Initial Survey**: Search for the main topic to understand the overall context
2. **Identify Dimensions**: From initial results, identify key subtopics, themes, angles, or aspects that need deeper exploration
3. **Map the Territory**: Note different perspectives, stakeholders, or viewpoints that exist

### Phase 2: Deep Dive

For each important dimension identified, conduct targeted research:

1. **Specific Queries**: Search with precise keywords for each subtopic
2. **Multiple Phrasings**: Try different keyword combinations and phrasings
3. **Fetch Full Content**: Use `web_fetch` to read important sources in full, not just snippets
4. **Follow References**: When sources mention other important resources, search for those too

### Phase 3: Diversity & Validation

Ensure comprehensive coverage by seeking diverse information types:

| Information Type | Purpose | Example Searches |
|-----------------|---------|------------------|
| **Facts & Data** | Concrete evidence | "statistics", "data", "numbers", "market size" |
| **Examples & Cases** | Real-world applications | "case study", "example", "implementation" |
| **Expert Opinions** | Authority perspectives | "expert analysis", "interview", "commentary" |
| **Trends & Predictions** | Future direction | "trends 2024", "forecast", "future of" |
| **Comparisons** | Context and alternatives | "vs", "comparison", "alternatives" |
| **Challenges & Criticisms** | Balanced view | "challenges", "limitations", "criticism" |

### Phase 4: Synthesis Check

Before proceeding to content generation, verify:

- [ ] Have I searched from at least 3-5 different angles?
- [ ] Have I fetched and read the most important sources in full?
- [ ] Do I have concrete data, examples, and expert perspectives?
- [ ] Have I explored both positive aspects and challenges/limitations?
- [ ] Is my information current and from authoritative sources?

**If any answer is NO, continue researching before generating content.**

## Search Strategy Tips

### Effective Query Patterns

```
# Be specific with context
[topic] + year/context qualifier
"[topic] industry analysis"

# Include authoritative source hints
"[topic] research paper"
"[topic] SEC filing"
"[topic] earnings report"

# Search for specific content types
"[topic] case study"
"[topic] statistics"
"[topic] analyst report"

# Use temporal qualifiers — always use the ACTUAL current year from the Date section in system prompt
"[topic] 2026"   # replace with real current year, never hardcode a past year
"[topic] latest"
"[topic] recent developments"
```

### Temporal Awareness

**Always check the `## Date` section in your system prompt before forming ANY search query.**

Use the right level of precision depending on what the user is asking:

| User intent | Temporal precision needed | Example query |
|---|---|---|
| "today / this morning / just released" | **Month + Day** | `"tech news February 28 2026"` |
| "this week" | **Week range** | `"technology releases week of Feb 24 2026"` |
| "recently / latest / new" | **Month** | `"AI breakthroughs February 2026"` |
| "this year / trends" | **Year** | `"software trends 2026"` |

**Rules:**

- When the user asks about "today" or "just released", use **month + day + year** in your search queries to get same-day results
- Never drop to year-only when day-level precision is needed
- Try multiple phrasings: numeric form (`2026-02-28`), written form (`February 28 2026`), and relative terms (`today`, `this week`) across different queries

### When to Use web_fetch

Use `web_fetch` to read full content when:

- A search result looks highly relevant and authoritative
- You need detailed information beyond the snippet
- The source contains data, case studies, or expert analysis
- You want to understand the full context of a finding

### Iterative Refinement

Research is iterative. After initial searches:

1. Review what you've learned
2. Identify gaps in your understanding
3. Formulate new, more targeted queries
4. Repeat until you have comprehensive coverage

## Quality Bar

Your research is sufficient when you can confidently answer:

- What are the key facts and data points?
- What are 2-3 concrete real-world examples?
- What do experts say about this topic?
- What are the current trends and future directions?
- What are the challenges or limitations?
- What makes this topic relevant or important now?

## Common Mistakes to Avoid

- Stopping after 1-2 searches
- Relying on search snippets without reading full sources
- Searching only one aspect of a multi-faceted topic
- Ignoring contradicting viewpoints or challenges
- Using outdated information when current data exists
- Starting content generation before research is complete

## Output

After completing research, you should have:

1. A comprehensive understanding of the topic from multiple angles
2. Specific facts, data points, and statistics
3. Real-world examples and case studies
4. Expert perspectives and authoritative sources
5. Current trends and relevant context

**Only then proceed to content generation**, using the gathered information to create high-quality, well-informed content.

## Citation & References

**Every piece of data, statistic, fact, or claim sourced from the web MUST be cited inline using markdown footnote references.**

### Inline Citation Rules

1. **Append a reference number at the end of each sentence** (before the period) that contains sourced data, statistics, facts, or claims.
2. Reference numbers use the format `[^x]` where `x` is a sequential integer starting from 1.
3. Each unique source gets its own number. If the same source is cited multiple times, reuse the same number.
4. Place the reference marker **before the period/punctuation** at the end of the sentence.

**Example:**

> 比亚迪2025年全年累计销售新能源汽车427.21万辆，同比增长41.2%[^1]。其中，纯电动车销量约为176.5万辆，首次超越特斯拉成为全球纯电动汽车销量冠军[^2]。

### References Section

At the **end of your output**, include a "参考资料" (References) section listing all cited sources in the following format:

```
## 参考资料

[^1]: (比亚迪2025年销量数据-懂车帝)[https://www.dongchedi.com/example1]
[^2]: (全球纯电动车销量排名-汽车之家)[https://www.autohome.com.cn/example2]
[^3]: (新能源汽车行业分析报告-中信证券)[https://www.citics.com/example3]
```

**Format specification:**
- Each entry starts with `[^x]:` matching the inline reference number
- Followed by a space and the source title in parentheses: `(标题-来源名称)`
- Immediately followed by the URL in square brackets: `[https://...]`
- Sources should be listed in numerical order
- The title should be descriptive and include the source name (website, publication, organization, etc.)

### When to Cite

| Content Type | Cite? | Example |
|---|---|---|
| Specific numbers / statistics | **Yes** | "销量达到427万辆[^1]" |
| Direct quotes or paraphrased claims | **Yes** | "专家指出……[^2]" |
| Facts from a specific source | **Yes** | "该公司成立于2003年[^3]" |
| Data from reports / studies | **Yes** | "根据麦肯锡报告[^4]" |
| Common knowledge / general knowledge | No | "地球绕太阳公转" |
| Your own analysis / synthesis | No | "综合来看……" |
