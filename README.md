# Coupons Management API

A FastAPI service to manage and apply discount coupons (cart-wise, product-wise, and BxGy) for an e-commerce cart.

## Requirements

* Python 3.11+
* PostgreSQL 13+ (running and reachable)
* Install dependencies from `requirements.txt`

## Setup

```bash
git clone <repository-url>
cd coupon-management-backend

python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the project root:

```dotenv

# Runtime DB (psycopg v3 driver)
DATABASE_URL=postgresql+psycopg://<USER>:<PASSWORD>@<HOST>:5432/coupons

# Test DB (used by pytest)
# Create this database once (see "Test DB Setup" below), then set:
TEST_DATABASE_URL=postgresql+psycopg://<USER>:<PASSWORD>@<HOST>:5432/coupons_test
```

## Test DB Setup (PostgreSQL)

Create a dedicated user and databases (one-time):

```sql
-- connect as admin, e.g.:
-- psql -U postgres -h localhost -p 5432

CREATE ROLE coupons_user WITH LOGIN PASSWORD 'StrongPassword' NOSUPERUSER NOCREATEDB NOCREATEROLE;

CREATE DATABASE coupons      OWNER coupons_user;
CREATE DATABASE coupons_test OWNER coupons_user;
```

Then update `.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://coupons_user:StrongPassword@localhost:5432/coupons
TEST_DATABASE_URL=postgresql+psycopg://coupons_user:StrongPassword@localhost:5432/coupons_test
```

> If your provider requires SSL, append `?sslmode=require` to the URLs.

## Run

```bash
uvicorn app.main:app --reload
```

* Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
* ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
* Health: [http://localhost:8000/health](http://localhost:8000/health)

## Seed Test Data (optional)

Creates tables (if needed) and inserts sample coupons.

```bash
python scripts/seed.py
```

## Tests

Ensure `TEST_DATABASE_URL` is set (in `.env` or the shell), then:

```bash
pytest -q
```

* macOS/Linux (inline):

  ```bash
  TEST_DATABASE_URL="postgresql+psycopg://coupons_user:StrongPassword@localhost:5432/coupons_test" pytest -q
  ```
* Windows PowerShell:

  ```powershell
  $env:TEST_DATABASE_URL="postgresql+psycopg://coupons_user:StrongPassword@localhost:5432/coupons_test"; pytest -q
  ```

## API Endpoints

**Coupons (CRUD)**

* `POST   /coupons` — create coupon
* `GET    /coupons` — list coupons
* `GET    /coupons/{id}` — get coupon
* `PUT    /coupons/{id}` — update coupon
* `DELETE /coupons/{id}` — delete coupon

**Coupon Application**

* `POST /applicable-coupons` — list applicable coupons for a cart
* `POST /apply-coupon/{id}` — apply a coupon to a cart

## Request Examples

Create a cart-wise coupon:

```json
{
  "type": "cart-wise",
  "details": {
    "threshold": 100,
    "discount": 10,
    "discount_type": "percentage"
  }
}
```

Find applicable coupons (supports `{ "cart": {...} }` or top-level cart):

```json
{
  "cart": {
    "items": [
      { "product_id": 1, "quantity": 2, "price": 60 },
      { "product_id": 2, "quantity": 1, "price": 100 }
    ]
  }
}
```

Apply a coupon:

```json
{
  "items": [
    { "product_id": 1, "quantity": 2, "price": 60 },
    { "product_id": 2, "quantity": 1, "price": 100 }
  ]
}
```

## Notes

* Monetary calculations use `Decimal` internally; responses return floats rounded to 2 decimals.
* BxGy: free items are added to the cart (price `0`) if not already present; if present, their quantity increases and discounts are computed using their price.
* CORS is permissive (`*`) for demo; restrict in production.

## Future Improvements

* Add expiration dates and basic usage limits.
* Enable coupon stacking with simple conflict rules.
* Add authentication/authorization (API keys or JWT).
* Introduce Alembic migrations for schema changes.
* Add basic caching for applicable-coupon lookups.
