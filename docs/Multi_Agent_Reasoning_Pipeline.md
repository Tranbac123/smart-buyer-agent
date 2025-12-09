┌──────────────────────────────────────────────────────────────────┐
│                    Smart Buyer Agent Flow                         │
│                   (LangGraph-Style Orchestrator)                  │
└──────────────────────────────────────────────────────────────────┘

         User Query: "So sánh giá iPhone 15"
                        ↓
                  ┌─────────────┐
                  │   Planner   │  ← LLM generates execution plan
                  └──────┬──────┘
                         ↓
        Plan: [search → score → explain → finalize]
                         ↓
┌────────────────────────────────────────────────────────────────┐
│                     STATE FLOW                                 │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Step 1: PriceCompareNode                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Input:  state.query = "iPhone 15"                       │   │
│  │ Action: Call price_compare tool → search Shopee/Lazada  │   │
│  │ Output: state.facts["offers"] = [6 products]            │   │
│  │ Tokens: +50 tokens spent                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                         ↓                                      │
│  Step 2: DecisionNode                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Input:  state.facts["offers"]                           │   │
│  │ Action: Score by price/rating/reviews                   │   │
│  │ Output: state.facts["scoring"] = {best, confidence}     │   │
│  │         state.facts["explanation"] = {winner, tradeoffs}│   │
│  │ Tokens: +80 tokens spent                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                         ↓                                      │
│  Step 3: ExplainNode                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Input:  state.facts["offers"], state.facts["scoring"]   │   │
│  │ Action: LLM generates natural language explanation      │   │
│  │ Output: state.facts["explanation"]["summary"] = "..."   │   │
│  │ Tokens: +300 tokens spent                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                         ↓                                      │
│  Step 4: FinalizeNode                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Input:  All facts                                       │   │
│  │ Action: Package response + metadata                     │   │
│  │ Output: state.mark_done({offers, scoring, explanation}) │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
                         ↓
              Return: Complete response
              Total tokens: 430 / 5000
              Latency: 2.3s