# Razorpay Payment Integration Guide

This guide details the integrated Razorpay payment flow for the backend.

## 1. Environment Configuration

Add the following keys to your `.env` file:

```env
RAZORPAY_KEY_ID=rzp_test_xxxxxx          # Your Razorpay API Key ID
RAZORPAY_KEY_SECRET=xxxxxx              # Your Razorpay API Key Secret
RAZORPAY_WEBHOOK_SECRET=xxxxxx          # Secret to verify incoming webhooks
RAZORPAY_CURRENCY=INR                   # Currency (Default is INR)
```

*Note: In development, if the Key ID is set to `rzp_test_xxxxxx` (or empty), the backend automatically falls back to **Mock Payment Mode** so you can test checkout and verify signature without valid credentials.*

---

## 2. API Endpoints

| Method & Path | Auth Required | Description |
| :--- | :--- | :--- |
| `POST /api/checkout` | Yes (Customer) | Places order from active cart, initializes Razorpay Order, clears cart. Returns order details and `razorpay_order_id`. |
| `POST /api/payment/verify` | Yes (Customer) | Verifies the signature of the client transaction and marks order status as paid. |
| `POST /api/webhooks/razorpay` | No (Public) | Receives webhook events (`payment.captured`, `payment.failed`) to update status asynchronously. |
| `GET /api/payment/status/{order_id}` | Yes (Owner/Staff) | Returns latest status of payments related to the order. |
| `POST /api/payment/refund` | Yes (Admin) | Initiates a partial or full refund for a captured payment. |

---

## 3. Standard Checkout Flow

1. **Create Order**: The frontend calls `POST /api/checkout` with delivery/address details.
2. **Initialize Checkout**: The backend returns the generated `razorpay_order_id` along with amount.
3. **Open Razorpay Gateway**: The frontend loads Razorpay Standard Checkout in the browser using the returned `razorpay_order_id`.
4. **Complete Payment**: The customer pays. Razorpay returns `razorpay_payment_id` and `razorpay_signature`.
5. **Verify Payment**: The frontend submits signature to `POST /api/payment/verify` to complete the order.
