# Discount Service

Implementation of `PROBLEM_STATEMENT.md` (Unifize Backend Developer Assignment, Python track).

## Run it

```bash
pip install -r requirements.txt
pytest -v

uvicorn main:app --reload
# → http://127.0.0.1:8000/docs for interactive Swagger UI
```

Example request:

```bash
curl -s -X POST http://127.0.0.1:8000/discounts/calculate -H "Content-Type: application/json" -d '{
  "cart_items": [{"product": {"id":"p1","brand":"PUMA","brand_tier":"premium","category":"T-shirts","base_price":"1500.00","current_price":"1500.00"}, "quantity":1, "size":"M"}],
  "customer": {"id":"c1","tier":"regular"},
  "payment_info": {"method":"CARD","bank_name":"ICICI","card_type":"CREDIT"}
}'
```

To poke at the service layer directly, without the API:

```bash
python3 -c "
import asyncio
from services.discount_service import DiscountService
from seed import seed

async def main():
    seeded = seed()
    result = await DiscountService().calculate_cart_discounts(
        seeded['cart_items'], seeded['customer'], seeded['payment_info']
    )
    print(result)

asyncio.run(main())
"
```

## Files

- `enums.py` — `BrandTier`, `CustomerTier`.
- `models/` — dataclass domain layer. `Entity` (`id`/`created_at`/`updated_at`/`deleted`, ulid-generated id) is the base class for `CartItem`, `PaymentInfo`, `DiscountedPrice`. `Product` and `CustomerProfile` keep their own caller-supplied `id` (real business/catalog keys) and don't extend `Entity`. No FastAPI/pydantic dependency in this layer.
- `services/rules.py` — one class per discount type (`BrandDiscountRule`, `CategoryDiscountRule`, `VoucherRule`, `BankOfferRule`).
- `services/discount_service.py` — `DiscountService`, the given core interface.
- `schemas/` — pydantic request/response DTOs for the API layer, with `to_domain()` converters into `models/`. Kept separate so the service logic stays framework-agnostic.
- `routers/discounts.py` — FastAPI `APIRouter` with `POST /discounts/calculate` and `POST /discounts/validate`.
- `main.py` — FastAPI app, mounts the router, `/health` endpoint.
- `core/db.py` — `InMemoryDB`, a singleton keyed by entity name then record key (`insert`/`find_one`/`find`/`update`/`delete`/`clear`).
- `seed.py` — populates `core.db` with the doc's dummy scenario (PUMA T-shirt, T-shirts category, ICICI bank offer). `seed()` clears and re-inserts, so it's safe to call more than once.
- `tests/test_discount_service.py` — pytest coverage of the service layer.
- `tests/test_api.py` — pytest coverage of the HTTP layer via FastAPI's `TestClient`.
- `PROBLEM_STATEMENT.md` — the assignment text as given, saved for reference.

## Design

Each discount type (`BrandDiscountRule`, `CategoryDiscountRule`, `VoucherRule`, `BankOfferRule`) is its own
class implementing a small `applies_to` / `percent_off` contract. `DiscountService` holds a rule catalog
(injected at construction, defaulted to the assignment's scenario) and applies rules in the order the
interface's docstring specifies: brand → category → coupon codes → bank offers. Adding a new discount
type means adding a new rule class and passing it into the catalog — `DiscountService` itself doesn't
change.

Stacking is sequential/multiplicative on the per-item price (each stage discounts the *already-discounted*
price, not the original), which matches the "Additional 10% off" wording in the business scenario. Bank
offers apply last, on the cart subtotal, since they're a payment-method-level discount rather than a
per-item one.

## Assumptions / gaps filled in

1. **`CustomerProfile`** is used in the given service interface but never defined in the doc's data models.
   Added minimally: `id: str` and `tier: CustomerTier` (`NEW` / `REGULAR` / `VIP`), since the
   `validate_discount_code` docstring calls out "customer tier requirements" as something to handle.

2. **`calculate_cart_discounts` has no way to pass a voucher code** in the signature given by the doc,
   even though its docstring says to apply coupon codes as a stacking stage. Added an optional
   `voucher_code: Optional[str] = None` keyword argument (default `None`, so the original call shape still
   works) so that stage is actually reachable. `validate_discount_code` is kept as given, for checking
   eligibility independently of applying it.

3. **`Product.current_price`** ("after brand/category discount") is not used as an input — the service
   computes brand/category discounts itself from `base_price` using the rule catalog, since that's the
   behavior the interface's docstring asks for. `current_price` is treated as a pre-existing field on the
   model that this service is responsible for producing the value of, not consuming.

4. Only the happy path from the dummy scenario plus the interface's documented cases (brand exclusion,
   category restriction, tier requirement, unknown code) are handled — no attempt at exhaustive edge-case
   coverage, per the assignment's explicit scope note.

5. Amounts are rounded to 2 decimal places (`ROUND_HALF_UP`) at the point each discount is recorded and at
   the final price, to avoid `Decimal` fractions leaking into `applied_discounts`.
