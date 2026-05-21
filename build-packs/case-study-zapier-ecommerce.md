# Case Study: Automating Order Fulfilment for a UK E-Commerce Brand

**Platform:** Zapier  
**Industry:** E-commerce (handmade goods, Shopify)  
**Time to build:** 2.5 hours  
**Time saved per month:** ~18 hours

---

## The Problem

A small UK-based e-commerce business selling handmade ceramics was processing around 200 orders per month through Shopify. Every time an order came in, their two-person team had to:

1. Manually update a shared Google Sheet to log the order and decrement stock
2. Copy the order details into a Slack message to notify the fulfilment team
3. Create a Trello card so the order could be tracked through packing and dispatch

During peak periods — holiday seasons, product launches — this manual loop took 5–6 minutes per order. At 200 orders a month, that was over 16 hours of pure admin, done by hand, prone to being forgotten when things got busy. Twice in the previous quarter, orders had slipped through without a Trello card and shipped late. One customer complaint had landed.

The owner didn't want to hire a part-time admin. She wanted the system to handle it.

---

## The Solution

A three-step Zapier automation triggered by every new Shopify order, completing the entire admin loop in under 10 seconds.

**Trigger:** New order in Shopify  
**Actions:**
1. Append a row to Google Sheets (order ID, product, quantity, SKU, customer name, timestamp)
2. Post a formatted Slack message to the `#fulfilment` channel
3. Create a Trello card in the "New Orders" list on their fulfilment board

No custom code. No monthly retainer. One Zap.

---

## Workflow Steps

**Step 1 — Trigger: Shopify "New Order"**  
The Zap fires the moment Shopify registers a completed order. All order data — line items, customer details, shipping address, order ID — is available to every downstream step automatically.

**Step 2 — Google Sheets: Log the Order**  
A new row is appended to a running inventory log. Columns populated automatically: Order ID, Product Name, SKU, Quantity, Customer Name, Order Date, Fulfilment Status (defaulting to "Pending"). The sheet acts as a live inventory tracker the team can filter and sort without touching Shopify.

**Step 3 — Slack: Notify the Fulfilment Team**  
A formatted message posts to `#fulfilment` containing the order number, product name and quantity, customer name, and a direct link to the Shopify order. The message uses Slack's block formatting so it's scannable at a glance — no digging through Shopify to understand what came in.

**Step 4 — Trello: Create the Order Card**  
A card is created in the "New Orders" list on the fulfilment board. Card name: `Order #XXXX — [Product Name]`. Description includes customer name, quantity, and order timestamp. The card moves through their existing columns (New → Packing → Dispatched → Done) as normal — the Zap just handles creation so no order is ever missed.

---

## What the Workflow Looks Like

*The Zapier editor shows a linear four-step flow: the Shopify trigger at the top, followed by the Google Sheets action, the Slack action, and the Trello action. Each step displays a green checkmark from the test run. The right panel shows the field mapping for the active step — in the Sheets action, Shopify's `order_id`, `line_items.name`, and `created_at` fields are mapped to the corresponding sheet columns. The overall structure is immediately readable: one trigger, three parallel outputs, zero branching logic.*

---

## Result

| Metric | Before | After |
|--------|--------|-------|
| Time per order (admin) | 5–6 min | 0 min |
| Monthly admin hours | ~18 hrs | 0 hrs |
| Orders missed in Trello | 2 per quarter | 0 |
| Time to fulfilment notification | 5–15 min (manual) | <10 sec |

The owner reclaimed roughly 18 hours per month — time she now spends on product development and customer relationships. The Trello miss rate dropped to zero in the following two months. The Google Sheet gives her an always-current inventory view she can check from her phone without logging into Shopify.

Total cost: the Zapier Starter plan at £17/month. The automation paid for itself on day one.

---

## What I'd Do Differently at Scale

At 200 orders/month this Zap runs comfortably on Starter. If volume scaled to 1,000+/month, I'd move the inventory tracking to a dedicated stock management tool (Linnworks, Katana) and use Zapier only for the notification and card creation. The Google Sheet approach works well for small teams but becomes a bottleneck when multiple people are editing it simultaneously.

For now, this is the right tool for the job: fast to build, easy to maintain, and zero ongoing input required from the client.
