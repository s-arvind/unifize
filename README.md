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
  "cart_items": [{"product": {"id":"p1","brand":"PUMA","brand_tier":"premium","category":"T-shirts","base_price":150000,"current_price":150000}, "quantity":1, "size":"M"}],
  "customer": {"id":"c1","tier":"regular"},
  "payment_info": {"method":"CARD","bank_name":"ICICI","card_type":"CREDIT"}
}'
# base_price/current_price are paisa (1 rupee = 100 paisa, e.g. 99.99 -> 9999) — 150000 = ₹1500.00
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

- `enums.py` — `BrandTier`, `CustomerTier`, `Category`, `DiscountType`.
- `models/` — dataclass domain layer. `Entity` (`id`/`created_at`/`updated_at`/`deleted`, ulid-generated id) is the base class for `CartItem`, `PaymentInfo`, `DiscountedPrice`, `DiscountRule`. `Product` and `CustomerProfile` keep their own caller-supplied `id` (real business/catalog keys) and don't extend `Entity`. No FastAPI/pydantic dependency in this layer.
- `models/discount_rule.py` — `DiscountRule`, a single model covering all four discount types (`DiscountType.BRAND`/`CATEGORY`/`VOUCHER`/`BANK_OFFER`), discriminated by `type`. Adding a new discount type means adding a `DiscountType` member + a branch here, not a new class.
- `services/discount_service.py` — `DiscountService`, the given core interface. Holds no rule state itself — reads the current `DiscountRule` catalog from `core.db` (entity `DISCOUNT_RULES`) on every call, so rules added/removed at runtime take effect immediately.
- `schemas/` — pydantic request/response DTOs for the API layer, with `to_entity()` converters into `models/`. Kept separate so the service logic stays framework-agnostic.
- `routers/discounts.py` — FastAPI `APIRouter` with `POST /discounts/calculate` and `POST /discounts/validate`.
- `main.py` — FastAPI app, mounts the router, `/health` endpoint, seeds `core.db` at import so the API works out of the box. Also registers exception handlers: domain validation errors (`ValueError`, e.g. bad quantity) → `400`, anything else unhandled → `500` with a generic message.
- `core/db.py` — `InMemoryDB`, a singleton keyed by entity name then record key (`insert`/`find_one`/`find`/`update`/`delete`/`clear`).
- `seed.py` — populates `core.db` with the doc's dummy scenario (PUMA T-shirt, T-shirts category, ICICI bank offer, SUPER69 voucher) *and* the discount rule catalog `DiscountService` reads. `seed()` clears and re-inserts, so it's safe to call more than once.
- `tests/test_discount_service.py` — pytest coverage of the service layer.
- `tests/test_api.py` — pytest coverage of the HTTP layer via FastAPI's `TestClient`.
- `PROBLEM_STATEMENT.md` — the assignment text as given, saved for reference.

## Design

`DiscountRule` is one model, not one class per discount type — a `type: DiscountType` field discriminates
BRAND/CATEGORY/VOUCHER/BANK_OFFER, with `applies_to_item()`/`applies_to_payment()` branching on it. This
keeps every discount type storable in a single `core.db` entity bucket (`DISCOUNT_RULES`) rather than one
bucket per rule class. `DiscountService` holds no rule state of its own — it reads the current catalog from
`core.db` fresh on every call and applies rules in the order the interface's docstring specifies: brand →
category → coupon codes → bank offers.

If multiple brand or category rules exist that match the same item, only the best one (highest `percent`) is applied.

`DiscountRule.percent` must be in `(0, 100]`, enforced at construction. `_percent_of` also caps any single
discount at the amount it's discounting from, as a second guard against a negative price.

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

5. **Money is stored as `int` paisa internally** (e.g. ₹99.99 = `9999`), not `Decimal` rupees — avoids
   float/`Decimal` drift in calculations. `percent` on `DiscountRule` stays `Decimal`. The API response
   converts back to rupees as `float` (e.g. `729.0`) for display.

6. **`Product.category` is the `Category` enum**, not a string — avoids case/typo mismatches.

7. **`CartItem`, `PaymentInfo`, `DiscountedPrice` extend `Entity`** (`id`/`created_at`/`updated_at`/
   `deleted`) — needed once they became db records. `Product`/`CustomerProfile` keep their own caller-supplied
   `id` (real keys) instead.

8. **Dummy data lives in `seed.py`, not `fake_data.py`** — it now also seeds the discount rule catalog.
