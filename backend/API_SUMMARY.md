# API Summary

## Authentication (`/api/auth`)

| Method | Endpoint | Description | Request Payload | Response Payload | DB Table(s) Affected |
|--------|----------|-------------|-----------------|------------------|----------------------|
| POST | `/api/auth/send-otp` | Send OTP to email for verification | `SendOTPRequest` (email) | `StandardResponse` (success, message) | Inserts a row into **OTPRecord** (email, otp_code, expires_at) |
| POST | `/api/auth/verify-otp` | Verify OTP code | `VerifyOTPRequest` (email, otp) | `StandardResponse` (success, message) | Deletes the matched **OTPRecord** after verification |
| POST | `/api/auth/register` | Register a new user | `UserCreate` (name, email, password, phone?) | `TokenResponse` (access_token, user) | Inserts a new **User** record |
| POST | `/api/auth/login` | Authenticate user and obtain JWT | `LoginRequest` (email, password) | `TokenResponse` (access_token, user) | Reads **User** for credential check |
| GET | `/api/auth/me` | Get current authenticated user profile | – | `UserResponse` (full user details) | Reads **User** (current user) |
| PUT | `/api/auth/profile` | Update current user profile | `ProfileUpdateRequest` (name?, phone?, address?) | `UserResponse` (updated user) | Updates fields on **User** |
| POST | `/api/auth/subscribe` | Set subscription tier for user | `SubscribeRequest` (tier) | `UserResponse` (updated user) | Updates **User.subscription_tier** |
| GET | `/api/auth/users` | List all users (admin/employee/shopkeeper) | Query params: `limit`, `offset` | List of `UserResponse` | Reads **User** (selected columns) |

## Products (`/api/products`)

| Method | Endpoint | Description | Request Payload | Response Payload | DB Table(s) Affected |
|--------|----------|-------------|-----------------|------------------|----------------------|
| GET | `/api/products` | Retrieve paginated list of products (optional category filter) | Query params: `category`, `limit`, `offset` | List of `ProductResponse` | Reads **Product** (selected columns) |
| GET | `/api/products/{product_id}` | Get a single product by its ID | – | `ProductResponse` | Reads **Product** by `id` |
| POST | `/api/products` | Create a new product (admin only) | `ProductCreate` (name, description, price, category, badge, image_url, mrp, rating, images, features, specs) | `ProductResponse` (created product) | Inserts a new **Product** record |
| PATCH | `/api/products/{product_id}` | Update product attributes (admin only) | `ProductUpdate` (partial fields) | `ProductResponse` (updated product) | Updates the matching **Product** row |

## Orders (`/api/orders`)

| Method | Endpoint | Description | Request Payload | Response Payload | DB Table(s) Affected |
|--------|----------|-------------|-----------------|------------------|----------------------|
| POST | `/api/orders` | Create a new order for the authenticated user | `OrderCreate` (total_amount, delivery_type, delivery_cost, payment_screenshot_url, address fields, items[]) | `OrderResponse` (order with items) | Inserts a new **Order** and multiple **OrderItem** rows |
| GET | `/api/orders` | List orders (customers see own, staff see all) | Query params: `limit`, `offset` | List of `OrderResponse` | Reads **Order** (with related **OrderItem**) |
| POST | `/api/orders/{order_id}/status` | Update order status (admin/shopkeeper or customer cancellation) | `OrderStatusUpdate` (status) | `OrderResponse` (updated order) | Updates **Order.status** |

## Health Check

| Method | Endpoint | Description | Response Payload |
|--------|----------|-------------|-------------------|
| GET | `/api/health` | Simple health endpoint that pings the database | `{ "status": "healthy" | "unhealthy", "database": "connected" | "error_message" }` |

*All endpoints use FastAPI and rely on the authentication dependency `get_current_user` where appropriate.*
