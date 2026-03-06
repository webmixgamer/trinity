# Calling Paid Trinity Agents

Trinity agents can be monetized using the [Nevermined x402 payment protocol](https://docs.nevermined.app/docs/development-guide/nevermined-x402). This document describes the HTTP-level protocol for any client to discover, purchase, and call a paid agent.

---

## Protocol Summary

```
Client                          Trinity                        Nevermined
  |                               |                               |
  |-- GET /api/paid/{agent}/info ->|                               |
  |<- 200 payment_required -------|                               |
  |                               |                               |
  |-- Order plan (one-time) ------|------------------------------>|
  |<- Credits issued -------------|-------------------------------|
  |                               |                               |
  |-- Get x402 access token ------|------------------------------>|
  |<- accessToken ----------------|-------------------------------|
  |                               |                               |
  |-- POST /api/paid/{agent}/chat |                               |
  |   Header: payment-signature   |                               |
  |------------------------------>|-- verify_permissions -------->|
  |                               |<- valid ----------------------|
  |                               |                               |
  |                               |   [execute task]              |
  |                               |                               |
  |                               |-- settle_permissions -------->|
  |                               |<- credits burned ------------|
  |<- 200 response + receipt -----|                               |
```

---

## Step 1: Discover

Call the agent's public info endpoint. No authentication required.

```
GET /api/paid/{agent_name}/info
```

**Response (200):**

```json
{
  "agent_name": "my-agent",
  "credits_per_request": 1,
  "nvm_plan_id": "<plan_id>",
  "payment_required": {
    "x402Version": 2,
    "resource": {
      "url": "/api/paid/my-agent/chat"
    },
    "accepts": [
      {
        "scheme": "nvm:erc4337",
        "network": "eip155:84532",
        "planId": "<plan_id>",
        "extra": {
          "agentId": "<agent_id>",
          "httpVerb": "POST"
        }
      }
    ]
  }
}
```

This response contains everything you need:

| Field | Meaning |
|-------|---------|
| `planId` | The payment plan to purchase and generate tokens against |
| `agentId` | The agent identity within Nevermined |
| `network` | `eip155:84532` = sandbox (testnet), `eip155:8453` = live (mainnet) |
| `credits_per_request` | How many credits each call costs |

Always use the values from this endpoint. Do not copy plan or agent IDs from other sources.

**Response (404):** Agent does not exist or payments are not enabled.

---

## Step 2: Purchase Credits

Before calling the agent, you need credits on its plan. This is a one-time purchase (you can top up later when credits run low).

You need a Nevermined API key from [nevermined.app](https://nevermined.app) (Settings > API Keys). Your key's environment prefix (`sandbox:` or `live:`) must match the agent's `network`.

### Nevermined Order Plan API

```
POST https://api.{environment}.nevermined.app/api/v1/protocol/plans/{planId}/order
Authorization: Bearer {your_nvm_api_key}
```

| Environment | Base URL |
|-------------|----------|
| sandbox | `https://api.sandbox.nevermined.app/api/v1` |
| live | `https://api.live.nevermined.app/api/v1` |

**Response (200):**

```json
{
  "success": true,
  "txHash": "0x...",
  "balance": {
    "isSubscriber": true,
    "total": 100,
    "used": 0,
    "remaining": 100
  }
}
```

### Web Checkout

Agents may also provide a checkout URL for browser-based purchase:

```
https://nevermined.app/checkout/{agent_id}
```

### Check Balance

```
GET https://api.{environment}.nevermined.app/api/v1/protocol/plans/{planId}/balance/{your_wallet_address}
Authorization: Bearer {your_nvm_api_key}
```

### SDK and CLI Alternatives

Nevermined provides SDKs ([Python](https://docs.nevermined.app/docs/api-reference/python/plans-module), [TypeScript](https://docs.nevermined.app/docs/api-reference/typescript/payment-plans)) and a [CLI](https://docs.nevermined.app/docs/api-reference/cli/purchases) that wrap these APIs. Use whichever fits your stack.

---

## Step 3: Get an Access Token

Each request to a paid agent requires an x402 access token. Generate one through the Nevermined API using the `planId` and `agentId` from Step 1.

```
GET https://api.{environment}.nevermined.app/api/v1/protocol/token/{planId}/{agentId}
Authorization: Bearer {your_nvm_api_key}
```

**Response (200):**

```json
{
  "accessToken": "string",
  "neverminedProxyUri": "string",
  "expiresAt": "2026-04-01T00:00:00Z"
}
```

The `accessToken` value is what you pass as the `payment-signature` header in Step 4.

Tokens are short-lived. Generate a fresh one before each request or batch of requests. If you get a 403, your token has likely expired.

See the [Nevermined access token documentation](https://docs.nevermined.app/docs/api-reference/protocol/get-access-token) for advanced options. SDKs ([Python](https://docs.nevermined.app/docs/api-reference/python/x402-module), [TypeScript](https://docs.nevermined.app/docs/api-reference/typescript/x402)) and the [CLI](https://docs.nevermined.app/docs/api-reference/cli/querying) also wrap this endpoint.

---

## Step 4: Call the Agent

Send a POST request with the access token in the `payment-signature` header:

```
POST /api/paid/{agent_name}/chat
Content-Type: application/json
payment-signature: {access_token}

{
  "message": "Your prompt or question"
}
```

Optionally include `session_id` to continue a previous conversation:

```json
{
  "message": "Follow-up question",
  "session_id": "uuid-from-previous-response"
}
```

Each request costs credits regardless of session continuity.

---

## Complete Python Example

This script runs the full flow: discover payment requirements, order credits, generate an access token, and call the agent.

```bash
pip install payments-py requests python-dotenv
```

```python
import requests
from payments_py import Payments, PaymentOptions

# --- Configuration ---
NVM_API_KEY = "sandbox:your-jwt-here"       # From nevermined.app > Settings > API Keys
NVM_ENVIRONMENT = "sandbox"                  # "sandbox" or "live"
AGENT_URL = "https://your-trinity-instance/api/paid/my-agent/chat"
INFO_URL = "https://your-trinity-instance/api/paid/my-agent/info"

# --- Step 1: Discover ---
info = requests.get(INFO_URL).json()
plan_id = info["payment_required"]["accepts"][0]["planId"]
agent_id = info["payment_required"]["accepts"][0]["extra"]["agentId"]
print(f"Plan: {plan_id}, Agent: {agent_id}, Cost: {info['credits_per_request']} credits")

# --- Step 2: Purchase credits (one-time) ---
payments = Payments.get_instance(PaymentOptions(
    nvm_api_key=NVM_API_KEY,
    environment=NVM_ENVIRONMENT,
))
order = payments.plans.order_plan(plan_id)
print(f"Balance: {order['balance']['remaining']} credits")

# --- Step 3: Get access token ---
token_result = payments.x402.get_x402_access_token(plan_id, agent_id)
access_token = token_result["accessToken"]

# --- Step 4: Call the agent ---
response = requests.post(
    AGENT_URL,
    json={"message": "What is the weather in San Francisco?"},
    headers={"payment-signature": access_token},
    timeout=120,
)
result = response.json()
print(f"Status: {result['status']}")
print(f"Response: {result['response']}")
if result.get("payment", {}).get("settled"):
    print(f"Credits burned: {result['payment']['credits_burned']}")
    print(f"Remaining: {result['payment']['remaining_balance']}")
```

Step 2 only needs to run once (or when credits run low). Steps 3-4 repeat for each request — generate a fresh token each time.

---

## Ready-Made Client

The **[Nevermined Purchaser](https://github.com/Abilityai/nevermined-purchaser)** is a working client agent that handles the full payment flow. Configure three environment variables and call any paid Trinity agent:

```bash
git clone https://github.com/Abilityai/nevermined-purchaser.git
cd nevermined-purchaser
cp .env.example .env
# Edit .env: set NVM_API_KEY, NVM_PLAN_ID, NVM_AGENT_ID

pip install -r requirements.txt
python pay_and_call.py call --url https://your-instance/api/paid/my-agent/chat --message "Hello"
```

The purchaser also supports balance checking (`python pay_and_call.py balance`) and can override plan/agent IDs per call for multi-agent scenarios.

---

## Responses

### 200 — Success (credits charged)

```json
{
  "response": "The agent's answer.",
  "execution_id": "uuid",
  "status": "success",
  "payment": {
    "settled": true,
    "credits_burned": 1,
    "remaining_balance": "16",
    "tx_hash": "0x..."
  }
}
```

### 200 — Execution failed (no charge)

The agent attempted the task but failed. No credits are burned.

```json
{
  "response": "Error details...",
  "execution_id": "uuid",
  "status": "failed",
  "payment": {
    "settled": false,
    "reason": "Execution failed — no charge"
  }
}
```

### 200 — Success but settlement failed

The agent completed the work but on-chain settlement did not succeed after retries. The response is still returned.

```json
{
  "response": "The agent's answer.",
  "execution_id": "uuid",
  "status": "success",
  "payment": {
    "settled": false,
    "settle_retry_needed": true,
    "error": "Settlement failed after 3 attempts: ..."
  }
}
```

### 402 — Payment Required

Returned when the `payment-signature` header is missing.

**Response header:**

```
payment-required: <base64-encoded JSON>
```

The `payment-required` header contains the x402 payment requirements as a base64-encoded JSON string, per the [x402 protocol spec](https://docs.nevermined.app/docs/development-guide/nevermined-x402). Decode it to extract the `planId`, `agentId`, and `network` needed to purchase credits and generate an access token.

**Response body:**

```json
{
  "detail": "Payment required",
  "payment_required": {
    "x402Version": 2,
    "accepts": [{ "scheme": "nvm:erc4337", "planId": "...", "...": "..." }]
  },
  "credits_per_request": 1
}
```

The body contains the same payment requirements as the header in plain JSON. A client can use either to self-correct and retry with a valid token.

### 403 — Verification Failed

The token was provided but is invalid, expired, or has insufficient balance.

```json
{
  "detail": "Payment verification failed",
  "error": "Reason for failure"
}
```

### 404 — Not Found

Agent does not exist or payments are not enabled.

### 501 — Not Available

The Trinity instance does not have the Nevermined SDK installed. Server-side issue.

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `BCK.PROTOCOL.0003 — Plan not found` | Wrong plan ID, or API key environment does not match the agent | Use the `planId` from the `/info` endpoint. Ensure your API key prefix matches the agent's network. |
| `Invalid access token` | Token expired, malformed, or generated for a different plan/agent | Generate a fresh token using the exact `planId` and `agentId` from `/info`. |
| 402 even with `payment-signature` | You haven't purchased the plan yet | Order the plan first, then generate a new token. |
| `Insufficient balance` | Credits exhausted | Purchase the plan again to top up credits. |
| 403 after working previously | Token expired | Generate a new access token before each request (or batch). |

---

## Environment Reference

| Environment | API key prefix | Network ID | Blockchain |
|-------------|---------------|------------|------------|
| Sandbox | `sandbox:` | `eip155:84532` | Base Sepolia (testnet) |
| Live | `live:` | `eip155:8453` | Base (mainnet) |

Your API key's environment **must** match the agent's network. A `sandbox:` key cannot interact with plans on the `live` network, and vice versa.

---

## Further Reading

- [Nevermined Purchaser Agent](https://github.com/Abilityai/nevermined-purchaser) — Ready-made client for calling paid agents
- [Nevermined x402 Protocol](https://docs.nevermined.app/docs/development-guide/nevermined-x402)
- [Nevermined 5-Minute Setup](https://docs.nevermined.app/docs/integrate/quickstart/5-minute-setup)
- [Python SDK](https://docs.nevermined.app/docs/api-reference/python/x402-module) | [TypeScript SDK](https://docs.nevermined.app/docs/api-reference/typescript/x402) | [CLI](https://docs.nevermined.app/docs/api-reference/cli/purchases)
- [Order Plan API](https://docs.nevermined.app/docs/api-reference/protocol/order-plan)
- [Access Token API](https://docs.nevermined.app/docs/api-reference/protocol/get-access-token)
