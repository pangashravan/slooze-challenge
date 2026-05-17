"""
demo_data.py — Realistic synthetic data generator.

Generates plausible IndiaMART-style product data for all configured
categories. Used when live scraping is blocked in automated environments.

The data distributions are modelled on real B2B marketplace patterns:
  - Price ranges vary significantly by category (IQR spans orders of magnitude)
  - Supplier concentration mirrors actual IndiaMART geography (Mumbai, Delhi, Surat, etc.)
  - ~15% of prices are intentionally null (mimics "Price on Request" listings)
  - ~10% of locations are null (mimics incomplete supplier profiles)
"""

import random
from datetime import datetime, timezone, timedelta

# ── Seed data pools ────────────────────────────────────────────────────────────

CATEGORY_CONFIG = {
    "electronics": {
        "products": [
            "LED Display Module", "MOSFET Transistor", "PCB Board",
            "Capacitor 100uF", "Arduino Uno Clone", "Relay Module 5V",
            "Bluetooth HC-05 Module", "Raspberry Pi Case", "SMPS Power Supply",
            "Copper Wire 1mm", "Breadboard 830 Tie", "Voltage Regulator IC",
            "Sensor DHT22", "LCD 16x2 Display", "Stepper Motor Driver",
            "Li-Ion Battery 18650", "USB Type-C Connector", "Ethernet Switch",
        ],
        "price_range": (20, 15000),
        "unit": "Piece",
    },
    "industrial_machinery": {
        "products": [
            "Hydraulic Press Machine", "CNC Lathe Machine", "Air Compressor",
            "Belt Conveyor System", "Industrial Gearbox", "Centrifugal Pump",
            "Diesel Generator 10KVA", "Pneumatic Cylinder", "Industrial Fan",
            "Metal Shearing Machine", "Welding Machine MIG", "Cooling Tower",
            "Vibrating Screen", "Screw Conveyor", "Hydraulic Jack 10 Ton",
        ],
        "price_range": (5000, 1500000),
        "unit": "Unit",
    },
    "textiles": {
        "products": [
            "Cotton Fabric 40s Count", "Polyester Yarn", "Silk Dupioni",
            "Denim Fabric 12oz", "Knitted Jersey Fabric", "Linen Fabric",
            "Rayon Fabric", "Chiffon Dupatta", "Woollen Blanket",
            "Batik Print Cotton", "Terry Cloth Towel", "Non Woven Fabric",
            "Embroidered Kurta Fabric", "Jacquard Weave", "Net Fabric",
        ],
        "price_range": (50, 800),
        "unit": "Meter",
    },
    "agriculture_equipment": {
        "products": [
            "Tractor Rotavator", "Drip Irrigation Kit", "Sprayer Pump",
            "Paddy Transplanter", "Grain Thresher Machine", "Mini Tractor",
            "Greenhouse Poly Sheet", "Soil Testing Kit", "Harvesting Machine",
            "Seed Drill Machine", "Chaff Cutter", "Farm Water Pump",
            "Mulching Film", "Fertigation System", "Agri Drone Sprayer",
        ],
        "price_range": (500, 800000),
        "unit": "Unit",
    },
    "chemicals": {
        "products": [
            "Hydrochloric Acid 30%", "Sodium Hydroxide Flakes", "Acetic Acid",
            "Ferric Chloride Anhydrous", "Hydrogen Peroxide 50%",
            "Caustic Soda Liquid", "Sulphuric Acid", "Sodium Hypochlorite",
            "Potassium Permanganate", "Citric Acid Monohydrate",
            "Zinc Oxide Powder", "Titanium Dioxide", "Glycerine",
            "Isopropyl Alcohol IPA", "Acetone Industrial Grade",
        ],
        "price_range": (30, 5000),
        "unit": "Kg",
    },
}

SUPPLIER_DATA = {
    "Maharashtra": {
        "cities": ["Mumbai", "Pune", "Nashik", "Nagpur", "Aurangabad"],
        "weight": 0.22,
    },
    "Gujarat": {
        "cities": ["Ahmedabad", "Surat", "Rajkot", "Vadodara", "Gandhinagar"],
        "weight": 0.18,
    },
    "Delhi": {
        "cities": ["New Delhi", "Noida", "Gurgaon", "Faridabad"],
        "weight": 0.15,
    },
    "Tamil Nadu": {
        "cities": ["Chennai", "Coimbatore", "Madurai", "Tirupur", "Salem"],
        "weight": 0.12,
    },
    "Uttar Pradesh": {
        "cities": ["Kanpur", "Agra", "Lucknow", "Varanasi", "Meerut"],
        "weight": 0.10,
    },
    "West Bengal": {
        "cities": ["Kolkata", "Howrah", "Durgapur", "Asansol"],
        "weight": 0.07,
    },
    "Rajasthan": {
        "cities": ["Jaipur", "Jodhpur", "Udaipur", "Kota"],
        "weight": 0.06,
    },
    "Karnataka": {
        "cities": ["Bengaluru", "Mysuru", "Mangaluru", "Hubli"],
        "weight": 0.10,
    },
}

SUPPLIER_NAME_PARTS = [
    ["Shree", "Sri", "Jai", "Om", "Bharat", "National", "Global", "Prime",
     "Star", "New", "Modern", "United", "Allied", "Indo"],
    ["Industries", "Traders", "Enterprises", "Exports", "Pvt Ltd",
     "Corporation", "Solutions", "Manufacturing", "Suppliers", "Agency"],
]

RATINGS = [None, None, "3.2", "3.5", "3.7", "4.0", "4.2", "4.4", "4.5",
           "4.6", "4.7", "4.8", "5.0"]  # None is common (no reviews yet)

MOQ_TEMPLATES = [
    "1 Piece", "5 Pieces", "10 Pieces", "50 Pieces", "100 Pieces",
    "500 Pieces", "1 Kg", "5 Kg", "10 Kg", "50 Kg", "100 Kg",
    "1 Unit", "1 Set", "1 Meter", "50 Meters", "100 Meters",
]


def _random_supplier_name() -> str:
    a = random.choice(SUPPLIER_NAME_PARTS[0])
    b = random.choice(SUPPLIER_NAME_PARTS[1])
    return f"{a} {b}"


def _random_location():
    """Sample a state based on realistic weights, then a city from that state."""
    states  = list(SUPPLIER_DATA.keys())
    weights = [SUPPLIER_DATA[s]["weight"] for s in states]

    if random.random() < 0.10:  # 10% missing location
        return None, None

    state = random.choices(states, weights=weights, k=1)[0]
    city  = random.choice(SUPPLIER_DATA[state]["cities"])
    return city, state


def _random_price(low: float, high: float):
    """Sample a price log-uniformly (matches real B2B price distributions)."""
    if random.random() < 0.15:  # 15% "Price on Request"
        return None, None

    import math
    log_low  = math.log10(low)
    log_high = math.log10(high)
    mid_log  = random.uniform(log_low, log_high)
    mid      = 10 ** mid_log

    # Random ±30% spread for range
    spread = random.uniform(0.05, 0.30) * mid
    price_min = round(max(low, mid - spread), 2)
    price_max = round(min(high, mid + spread), 2)
    return price_min, price_max


def _random_timestamp() -> str:
    """Random timestamp within last 7 days (mimics a real crawl window)."""
    offset = timedelta(seconds=random.randint(0, 7 * 24 * 3600))
    ts = datetime.now(timezone.utc) - offset
    return ts.isoformat()


def generate_demo_data(n_per_category: int = 80) -> list[dict]:
    """
    Generate n_per_category synthetic product records for each category.
    Total records = n_per_category × len(CATEGORY_CONFIG).
    """
    random.seed(42)  # reproducibility
    records = []

    for category, config in CATEGORY_CONFIG.items():
        products  = config["products"]
        low, high = config["price_range"]
        unit      = config["unit"]

        for _ in range(n_per_category):
            price_min, price_max = _random_price(low, high)
            city, state          = _random_location()
            price_mid = (
                round((price_min + price_max) / 2, 2)
                if price_min is not None else None
            )

            # Compose a varied product name
            base    = random.choice(products)
            variant = random.choice(["", " HD", " Industrial Grade", " Premium",
                                     " Standard", " Bulk Pack", " OEM", " Export"])
            name    = f"{base}{variant}".strip()

            record = {
                "product_name":    name,
                "category":        category,
                "price_raw":       (
                    f"₹ {price_min:,.0f} - {price_max:,.0f} / {unit}"
                    if price_min else "Get Latest Price"
                ),
                "price_min_inr":   price_min,
                "price_max_inr":   price_max,
                "price_mid_inr":   price_mid,
                "price_unit":      unit if price_min else None,
                "min_order_qty":   random.choice(MOQ_TEMPLATES),
                "supplier_name":   _random_supplier_name(),
                "supplier_city":   city,
                "supplier_state":  state,
                "supplier_rating": random.choice(RATINGS),
                "product_url":     (
                    f"https://www.indiamart.com/proddetail/"
                    f"{name.lower().replace(' ', '-')}-"
                    f"{random.randint(10000000, 99999999)}.html"
                ),
                "source":          "indiamart.com (demo)",
                "scraped_at":      _random_timestamp(),
            }
            records.append(record)

    return records
