"""
AI Business Assistant — uses Gemini to answer business questions
grounded in the user's actual business data.
"""

import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def _build_business_context(business_info: dict, analytics: dict) -> str:
    """Build a concise data context string from analytics for the AI."""
    ctx = []
    ctx.append(f"Business: {business_info.get('business_name', 'Unknown')}")
    ctx.append(f"Type: {business_info.get('business_type', 'Unknown')}")
    ctx.append(f"Location: {business_info.get('location', 'Unknown')}")
    ctx.append(f"Currency: {business_info.get('currency', 'INR')}")
    ctx.append("")

    kpis = analytics.get("kpis", {})
    if kpis:
        ctx.append("=== Key Performance Indicators ===")
        ctx.append(f"Total Revenue: {kpis.get('total_revenue', 0):,.2f}")
        ctx.append(f"Total Orders/Transactions: {kpis.get('total_orders', 0)}")
        ctx.append(f"Total Quantity Sold: {kpis.get('total_quantity', 0):,.2f}")
        ctx.append(f"Total Expenses: {kpis.get('total_expenses', 0):,.2f}")
        ctx.append(f"Gross Profit: {kpis.get('gross_profit', 0):,.2f}")
        ctx.append(f"Profit Margin: {kpis.get('profit_margin', 0):.1f}%")
        ctx.append(f"Average Order Value: {kpis.get('avg_order_value', 0):,.2f}")
        ctx.append(f"Unique Products: {kpis.get('unique_products', 0)}")
        ctx.append(f"Total Stock: {kpis.get('total_stock', 0):,.2f}")
        ctx.append(f"Revenue Trend: {kpis.get('revenue_trend', 0):+.1f}%")
        ctx.append("")

    top = analytics.get("top_products", [])
    if top:
        ctx.append("=== Top Products by Revenue ===")
        for p in top[:5]:
            ctx.append(f"  {p['product']}: Revenue={p['revenue']:,.2f}, Qty={p['quantity']:,.0f}, Orders={p['orders']}")
        ctx.append("")

    bottom = analytics.get("bottom_products", [])
    if bottom:
        ctx.append("=== Lowest Performing Products ===")
        for p in bottom[:5]:
            ctx.append(f"  {p['product']}: Revenue={p['revenue']:,.2f}, Qty={p['quantity']:,.0f}")
        ctx.append("")

    cats = analytics.get("category_breakdown", [])
    if cats:
        ctx.append("=== Expense Categories ===")
        for c in cats[:8]:
            ctx.append(f"  {c['category']}: Total={c['total']:,.2f} ({c['count']} transactions)")
        ctx.append("")

    inv = analytics.get("inventory_summary", [])
    if inv:
        ctx.append("=== Inventory Summary (low stock first) ===")
        for i in inv[:10]:
            ctx.append(f"  {i['product']}: {i['total_quantity']:,.0f} units across {i['locations']} location(s)")
        ctx.append("")

    trends = analytics.get("sales_trends", [])
    if trends:
        ctx.append("=== Recent Weekly Sales Trends ===")
        for t in trends[-6:]:
            ctx.append(f"  {t.get('year','')}-{t['week']}: Revenue={t['revenue']:,.2f}, Orders={t['orders']}")
        ctx.append("")

    alerts = analytics.get("alerts", [])
    if alerts:
        ctx.append("=== Active Alerts ===")
        for a in alerts:
            ctx.append(f"  [{a['type'].upper()}] {a['title']}: {a['message']}")
        ctx.append("")

    monthly = analytics.get("monthly_revenue", [])
    if monthly:
        ctx.append("=== Monthly Revenue ===")
        for m in monthly:
            ctx.append(f"  {m['month']}: Revenue={m['revenue']:,.2f}, Orders={m['orders']}")
        ctx.append("")

    return "\n".join(ctx)


SYSTEM_PROMPT = """You are an AI Business Assistant for a small/micro business. Your role is to:

1. Answer questions about the business using ONLY the provided business data context
2. Explain KPIs and metrics in simple, practical language
3. Identify trends, problems, and opportunities in the data
4. Provide actionable, practical business suggestions
5. Be honest when data is insufficient to answer a question

RULES:
- Always ground your answers in the actual data provided
- Use the business's currency when mentioning monetary values
- Be concise but thorough
- Use bullet points for clarity
- If asked about data you don't have, say so clearly
- Never make up numbers or fabricate data
- Suggest practical next steps when relevant
- Format your responses with clear sections when appropriate
- Use markdown formatting (bold, bullets, etc.) for readability
"""


async def ask_assistant(question: str, business_info: dict, analytics: dict, conversation_history: list = None) -> str:
    """
    Send a question to the AI assistant with business context.
    Returns the AI response as a string.
    """
    if not GEMINI_API_KEY:
        return _fallback_response(question, analytics)

    try:
        from google import genai

        client = genai.Client(api_key=GEMINI_API_KEY)

        context = _build_business_context(business_info, analytics)

        # Build the user message with context
        user_message = f"""Here is the current business data context:

{context}

User Question: {question}

Please answer based on the business data above. Be practical and specific."""

        # Build contents list with history
        contents = []
        if conversation_history:
            for msg in conversation_history[-6:]:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append(genai.types.Content(
                    role=role,
                    parts=[genai.types.Part(text=msg.get("content", ""))]
                ))

        contents.append(genai.types.Content(
            role="user",
            parts=[genai.types.Part(text=user_message)]
        ))

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=1500,
            ),
        )

        return response.text

    except Exception as e:
        return _fallback_response(question, analytics)


def _fallback_response(question: str, analytics: dict) -> str:
    """Generate a basic response without AI when API is unavailable."""
    kpis = analytics.get("kpis", {})
    q = question.lower()

    if any(w in q for w in ["revenue", "sales", "income"]):
        return f"""**Revenue Summary**

- **Total Revenue**: {kpis.get('total_revenue', 0):,.2f}
- **Total Orders**: {kpis.get('total_orders', 0)}
- **Average Order Value**: {kpis.get('avg_order_value', 0):,.2f}
- **Revenue Trend**: {kpis.get('revenue_trend', 0):+.1f}%

Your business has generated {kpis.get('total_revenue', 0):,.2f} in total revenue across {kpis.get('total_orders', 0)} transactions."""

    elif any(w in q for w in ["profit", "margin", "earning"]):
        return f"""**Profit Summary**

- **Gross Profit**: {kpis.get('gross_profit', 0):,.2f}
- **Profit Margin**: {kpis.get('profit_margin', 0):.1f}%
- **Revenue**: {kpis.get('total_revenue', 0):,.2f}
- **Expenses**: {kpis.get('total_expenses', 0):,.2f}"""

    elif any(w in q for w in ["expense", "cost", "spending"]):
        return f"""**Expenses Summary**

- **Total Expenses**: {kpis.get('total_expenses', 0):,.2f}
- **As % of Revenue**: {(kpis.get('total_expenses', 0) / max(kpis.get('total_revenue', 1), 1) * 100):.1f}%"""

    elif any(w in q for w in ["stock", "inventory"]):
        return f"""**Inventory Summary**

- **Total Stock**: {kpis.get('total_stock', 0):,.0f} units
- **Products Tracked**: {kpis.get('unique_products', 0)}"""

    elif any(w in q for w in ["product", "top", "best", "worst"]):
        top = analytics.get("top_products", [])
        if top:
            lines = ["**Top Products by Revenue**\n"]
            for i, p in enumerate(top[:5], 1):
                lines.append(f"{i}. **{p['product']}** - Revenue: {p['revenue']:,.2f}, Qty: {p['quantity']:,.0f}")
            return "\n".join(lines)
        return "No product data available yet. Upload sales data to see product performance."

    else:
        return f"""**Business Overview**

- **Revenue**: {kpis.get('total_revenue', 0):,.2f}
- **Profit**: {kpis.get('gross_profit', 0):,.2f} ({kpis.get('profit_margin', 0):.1f}% margin)
- **Orders**: {kpis.get('total_orders', 0)}
- **Products**: {kpis.get('unique_products', 0)}
- **Stock**: {kpis.get('total_stock', 0):,.0f} units
- **Expenses**: {kpis.get('total_expenses', 0):,.2f}
- **Trend**: {kpis.get('revenue_trend', 0):+.1f}%

Ask me about specific metrics like revenue, profit, products, inventory, or expenses for more details!"""
