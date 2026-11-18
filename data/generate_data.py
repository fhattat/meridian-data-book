#!/usr/bin/env python3
"""generate_data.py - builds the synthetic Meridian Market and Bazaarly data set (Chapter 3, Appendix F).

Usage:
    python data/generate_data.py --size small --seed 2027 --out data/raw
    python data/generate_data.py --size large --seed 2027 --out data/raw     # Databricks / PySpark size

The same seed always produces the same files. The script first builds the "clean truth"
(every sale, every order), writes control_totals.json and answer_key.json from it, and only
then writes the source files with the 30 deliberate traps of Appendix D. That is why
control totals are the reference for every "keep the number" check in the book.

ALL DATA IS SYNTHETIC. Names, e-mail addresses (example.com/.net/.org), phone numbers
(555-01xx range), addresses and transactions belong to no real person or company.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import zlib
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data"))
import _texts as T  # noqa: E402  (names, cities, templates, PDF writer)

START, END = date(2025, 1, 1), date(2027, 6, 30)
ACQUISITION = date(2027, 1, 1)
DRIFT_DAY = date(2027, 4, 15)            # trap 28: status_code -> status
EVENT_RENAME_DAY = date(2026, 6, 1)      # trap 10: ts -> event_time
BLACK_FRIDAYS = {date(2025, 11, 28), date(2026, 11, 27)}
MISSING_POS_DAY = date(2026, 2, 9)       # trap 9: file lands in the wrong folder
CHANNEL_50_FROM = date(2027, 1, 1)       # trap 22: new, undocumented channel code
SIZES = {
    "small": {"pos_lambda": 1.6, "bz_orders_per_day": (25, 52), "events_per_day": 275,
              "members": 18000, "users": 11000, "accounts": 400, "tickets": 3000},
    "large": {"pos_lambda": 210.0, "bz_orders_per_day": (3200, 6800), "events_per_day": 66000,
              "members": 180000, "users": 110000, "accounts": 4000, "tickets": 30000},
}
TZ = {"ET": "America/New_York", "CT": "America/Chicago", "MT": "America/Denver", "PT": "America/Los_Angeles"}
CENT = Decimal("0.01")
DISCONTINUED = [f"PRD-{i:05d}" for i in range(595, 601)]   # in campaigns, never sold


def h(text: str) -> int:
    """Deterministic hash (Python's hash() changes between runs)."""
    return zlib.crc32(str(text).encode("utf-8"))


def money(x) -> Decimal:
    return Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_UP)


def usd_text(d: Decimal) -> str:
    """'$1,299.00' style, as the Meridian ERP and POS export it (trap 1)."""
    sign = "-" if d < 0 else ""
    return f"{sign}${abs(d):,.2f}"


def daterange(a: date, b: date):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


def write_csv(path: Path, df: pd.DataFrame, **kw) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, **kw)


# --------------------------------------------------------------------------- reference data
def build_fx(rng) -> pd.DataFrame:
    """OP02: business-day rates only (no weekend rows, trap 20). 6 decimals."""
    base = {"CAD": 0.735, "GBP": 1.268, "EUR": 1.082}
    rows = []
    level = dict(base)
    for d in daterange(date(2024, 12, 30), END):
        for cur in level:
            level[cur] *= float(np.exp(rng.normal(0, 0.0035)))
            level[cur] = min(max(level[cur], base[cur] * 0.9), base[cur] * 1.1)
        if d.weekday() < 5:
            for cur, v in level.items():
                rows.append({"date": d.isoformat(), "currency": cur, "rate_to_usd": f"{v:.6f}"})
    return pd.DataFrame(rows)


def fx_lookup(fx: pd.DataFrame):
    """Rate of the order date; for weekends the last business day before it (same rule as silver)."""
    table = {}
    for cur, g in fx.groupby("currency"):
        days = sorted((date.fromisoformat(d), Decimal(r)) for d, r in zip(g["date"], g["rate_to_usd"]))
        table[cur] = days
    cache = {}

    def rate(cur: str, d: date) -> tuple[Decimal, date]:
        key = (cur, d)
        if key not in cache:
            seq = table[cur]
            lo, hi = 0, len(seq) - 1
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if seq[mid][0] <= d:
                    lo = mid
                else:
                    hi = mid - 1
            cache[key] = (seq[lo][1], seq[lo][0])
        return cache[key]
    return rate


# --------------------------------------------------------------------------- Meridian Market
def build_stores() -> pd.DataFrame:
    rows = []
    for i, (city, state, region, tz) in enumerate(T.STORES, start=1):
        rows.append({"STORE_CD": f"MM-{i:03d}", "STORE_NAME": f"{city} {T.STORE_SUFFIX[i % len(T.STORE_SUFFIX)]}",
                     "CITY": city, "STATE": state, "REGION": region, "TIME_ZONE": tz,
                     "OPEN_DATE": f"{2008 + i % 15}-{1 + i % 12:02d}-01"})
    return pd.DataFrame(rows)


def build_mm_products(rng, n: int = 600) -> pd.DataFrame:
    rows = []
    used = set()
    for i in range(1, n + 1):
        cat = T.CATEGORIES[i % len(T.CATEGORIES)]
        sub = cat[1][(i // len(T.CATEGORIES)) % len(cat[1])]
        brand = T.BRANDS[(i * 7) % len(T.BRANDS)]
        noun = T.NOUNS[sub][(i // 3) % len(T.NOUNS[sub])]
        variant = T.VARIANTS[(i * 11) % len(T.VARIANTS)]
        name = f"{brand} {noun} {variant}"
        k = 2
        while name.lower() in used:
            name = f"{brand} {noun} {variant} {k}"
            k += 1
        if i % 37 == 5:
            name = name.replace("e", "é", 1)                     # becomes mojibake in the file (trap 15)
        used.add(name.lower())
        lo, hi = T.PRICE_RANGE[cat[0]]
        price = money(float(np.exp(rng.uniform(np.log(lo), np.log(hi)))))
        price = money(float(price) - (float(price) % 1) + 0.99) if price > 5 else price
        upc = f"{(i * 7919 + 12345) % 10**11:011d}"
        upc = upc + str((3 * sum(int(c) for c in upc[0::2]) + sum(int(c) for c in upc[1::2])) % 10)
        if i % 9 == 0:
            upc = "0" + upc[1:]                              # trap 16: leading zero, lost below
        rows.append({"PROD_CD": f"PRD-{i:05d}", "PROD_NAME": name, "BRAND": brand,
                     "CATEGORY_PATH": f"{cat[0]} > {sub}", "category": cat[0], "subcategory": sub,
                     "price": price, "UPC": upc, "STATUS": "ACTIVE"})
    rows.append({"PROD_CD": "PRD-99999", "PROD_NAME": "TEST – DO NOT USE", "BRAND": "TEST",
                 "CATEGORY_PATH": "Test > Test", "category": "Test", "subcategory": "Test",
                 "price": money("0.01"), "UPC": "000000000000", "STATUS": "TEST"})   # trap 6
    return pd.DataFrame(rows)


def mm_products_file(p: pd.DataFrame) -> pd.DataFrame:
    out = p.copy()
    out["UNIT_PRICE"] = out["price"].map(usd_text)                   # trap 1: "$1,299.00" text
    out["UPC"] = out["UPC"].str.lstrip("0")                          # trap 16: leading zero lost
    accents = out["PROD_NAME"].str.contains("é")
    out.loc[accents, "PROD_NAME"] = out.loc[accents, "PROD_NAME"].map(
        lambda s: s.encode("utf-8").decode("latin-1"))               # trap 15: mojibake (CafÃ©)
    out.loc[out.index % 50 == 7, "BRAND"] = "N/A"                    # trap 2: NULL spellings
    return out[["PROD_CD", "PROD_NAME", "BRAND", "CATEGORY_PATH", "UNIT_PRICE", "UPC", "STATUS"]]


def build_members(rng, n: int) -> pd.DataFrame:
    first = rng.choice(T.FIRST_NAMES, n)
    last = rng.choice(T.LAST_NAMES, n)
    stores = build_stores()
    states = rng.choice(stores["STATE"].values, n)
    rows = []
    for i in range(n):
        no = 100000 + i
        email = f"{first[i].lower()}.{last[i].lower()}{no % 997}@{T.EMAIL_DOMAINS[i % 3]}"
        rows.append({"MEMBER_NO": str(no), "FIRST_NAME": first[i], "LAST_NAME": last[i], "EMAIL": email,
                     "PHONE_DIGITS": f"{T.AREA_CODES[states[i]]}5550{100 + i % 100:03d}"[:10],
                     "BIRTH": date(1950, 1, 1) + timedelta(days=int(rng.integers(0, 18000))),
                     "ZIP": T.ZIP_PREFIX[states[i]] + f"{i % 1000:03d}"[-(5 - len(T.ZIP_PREFIX[states[i]])):],
                     "STATE": states[i],
                     "JOIN_DATE": date(2012, 1, 1) + timedelta(days=int(rng.integers(0, 5000)))})
    df = pd.DataFrame(rows)
    df.loc[len(df)] = {"MEMBER_NO": "999", "FIRST_NAME": "TEST", "LAST_NAME": "MEMBER",
                       "EMAIL": "test.member@example.com", "PHONE_DIGITS": "2125550100",
                       "BIRTH": date(1990, 1, 1), "ZIP": "10001", "STATE": "NY", "JOIN_DATE": date(2020, 1, 1)}
    return df


def members_file(m: pd.DataFrame) -> pd.DataFrame:
    out = m.copy()
    fmt = [lambda d: d.isoformat(), lambda d: d.strftime("%m/%d/%Y"), lambda d: d.strftime("%d-%b-%y")]
    out["BIRTH_DATE"] = [fmt[i % 3](d) for i, d in enumerate(out["BIRTH"])]             # trap 2
    ph = [lambda p: f"({p[:3]}) {p[3:6]}-{p[6:]}", lambda p: f"{p[:3]}-{p[3:6]}-{p[6:]}",
          lambda p: f"{p[:3]}.{p[3:6]}.{p[6:]}", lambda p: f"+1 {p[:3]} {p[3:6]} {p[6:]}"]
    out["PHONE"] = [ph[i % 4](p) for i, p in enumerate(out["PHONE_DIGITS"])]
    out["ZIP"] = out["ZIP"].str.lstrip("0")                                              # trap 16
    out["JOIN_DATE"] = out["JOIN_DATE"].map(lambda d: d.strftime("%m/%d/%Y"))
    bad = out.index % 113 == 17
    out.loc[bad, "EMAIL"] = out.loc[bad, "EMAIL"].str.replace("@", " at ", regex=False)  # trap 23
    out["MKT_OPT_IN"] = ["Y" if (i * 7) % 10 < 6 else "N" for i in range(len(out))]   # Chapter 12.2 segments
    out.loc[out.index % 211 == 3, "PHONE"] = "NULL"
    out.loc[out.index % 307 == 9, "EMAIL"] = ""
    cols = ["MEMBER_NO", "FIRST_NAME", "LAST_NAME", "EMAIL", "PHONE", "BIRTH_DATE", "ZIP", "STATE", "JOIN_DATE",
            "MKT_OPT_IN"]
    return out[cols]


def build_pos(rng, cfg, stores, products, members):
    """Clean truth of every receipt and line (before traps)."""
    days = list(daterange(START, END))
    prod = products[products["PROD_CD"] != "PRD-99999"].reset_index(drop=True)
    weights = 1.0 / np.arange(1, len(prod) + 1) ** 0.7
    weights = rng.permutation(weights)
    weights[prod["PROD_CD"].isin(DISCONTINUED).to_numpy()] = 0.0   # never sold (q10)
    weights /= weights.sum()
    price_cents = (prod["price"].map(lambda d: int(d * 100))).to_numpy()
    member_nos = members.loc[members["MEMBER_NO"] != "999", "MEMBER_NO"].to_numpy()
    store_ids = stores["STORE_CD"].to_numpy()
    store_tz = stores["TIME_ZONE"].map(TZ).to_numpy()
    store_factor = rng.uniform(0.6, 1.4, len(stores))
    tax = {s: T.SALES_TAX[st] for s, st in zip(stores["STORE_CD"], stores["STATE"])}
    receipts, lines = [], []
    test_days = set(rng.choice(len(days), 40, replace=False).tolist())
    for di, d in enumerate(days):
        season = 1.0 + 0.4 * (d.month == 12) + 0.15 * (d.month in (6, 7, 8)) + 0.12 * (d.year - 2025)
        if d in BLACK_FRIDAYS:
            season *= 4.0
        elif any(0 <= (d - bf).days <= 3 or -4 <= (d - bf).days < 0 for bf in BLACK_FRIDAYS):
            season *= 1.6
        counts = rng.poisson(cfg["pos_lambda"] * season * store_factor)
        for si, n_rec in enumerate(counts):
            for k in range(int(n_rec)):
                rno = f"{si + 1:03d}{d:%Y%m%d}{k + 1:04d}"
                minute = int(rng.integers(8 * 60, 21 * 60 + 50))
                ts_local = datetime.combine(d, time(minute // 60, minute % 60))
                member = str(rng.choice(member_nos)) if rng.random() < 0.6 else ""
                n_lines = 1 + int(rng.poisson(1.2))
                idx = rng.choice(len(prod), n_lines, p=weights)
                tender = T.TENDERS[int(rng.integers(0, len(T.TENDERS)))]
                total = 0
                for ln, pi in enumerate(idx, start=1):
                    qty = 1 + int(rng.random() < 0.18) + int(rng.random() < 0.05)
                    unit = int(price_cents[pi])
                    disc = int(round(qty * unit * 0.10)) if rng.random() < 0.10 else 0
                    amt = qty * unit - disc
                    if rng.random() < 0.03:                         # return line (trap 23: negative qty)
                        qty, disc, amt = -1, 0, -unit
                    total += amt
                    lines.append((rno, ln, prod.at[pi, "PROD_CD"], qty, unit, disc, amt))
                receipts.append((rno, store_ids[si], d, ts_local, store_tz[si], member, tender, total,
                                 tax[store_ids[si]], False))
        if di in test_days:                                          # trap 6: test member 999
            rno = f"999{d:%Y%m%d}0001"
            ts_local = datetime.combine(d, time(9, 15))
            lines.append((rno, 1, "PRD-99999", 1, 1, 0, 1))
            lines.append((rno, 2, prod.at[0, "PROD_CD"], 1, int(price_cents[0]), 0, int(price_cents[0])))
            receipts.append((rno, store_ids[0], d, ts_local, store_tz[0], "999", "CASH",
                             1 + int(price_cents[0]), tax[store_ids[0]], True))
    rec = pd.DataFrame(receipts, columns=["receipt_no", "store_id", "local_date", "ts_local", "iana_tz",
                                          "member_no", "tender_type", "lines_cents", "tax_rate", "is_test"])
    lin = pd.DataFrame(lines, columns=["receipt_no", "line_no", "product_id", "qty", "unit_cents",
                                       "disc_cents", "amount_cents"])
    return rec, lin


def write_pos_files(out: Path, rec: pd.DataFrame, lin: pd.DataFrame, rng) -> None:
    pos_dir = out / "meridian" / "pos"
    late_dir = out / "meridian" / "pos_late"
    pos_dir.mkdir(parents=True, exist_ok=True)
    late_dir.mkdir(parents=True, exist_ok=True)
    by_rec = {k: g for k, g in lin.groupby("receipt_no", sort=False)}
    for d, g in rec.groupby("local_date", sort=True):
        folder = late_dir if d == MISSING_POS_DAY else pos_dir      # trap 9: missing day
        path = folder / f"pos_{d:%Y%m%d}.csv"
        with open(path, "w", encoding="cp1252", newline="") as f:  # trap 1: ';' and Windows-1252
            w = csv.writer(f, delimiter=";", lineterminator="\r\n")
            for r in g.itertuples(index=False):
                total = Decimal(r.lines_cents) / 100 * (1 + Decimal(str(r.tax_rate)))
                if h(r.receipt_no) % 97 == 0:                    # trap 21: header total off
                    total += Decimal("1.00")
                w.writerow(["H", r.receipt_no, r.store_id if h(r.receipt_no) % 41 else r.store_id + " ",
                            r.ts_local.strftime("%m/%d/%Y %I:%M %p"), f"{1 + int(r.receipt_no[-1]) % 6:02d}",
                            r.member_no, r.tender_type, usd_text(money(total))])
                for l in by_rec[r.receipt_no].itertuples(index=False):
                    w.writerow(["L", l.receipt_no, l.line_no, l.product_id, l.qty,
                                usd_text(Decimal(l.unit_cents) / 100), usd_text(Decimal(l.disc_cents) / 100),
                                usd_text(Decimal(l.amount_cents) / 100)])
        if d in BLACK_FRIDAYS and d.year == 2025:                   # trap 8: resent the next day
            shutil.copyfile(path, pos_dir / f"pos_{d:%Y%m%d}_resend.csv")


# --------------------------------------------------------------------------- Bazaarly
def build_bz_geo():
    cities, states = [], []
    for code, name, region in T.US_STATES:
        states.append({"state_code": code, "state_name": name, "region": region, "country": "US"})
    for code, name, region, country in T.INTL_REGIONS:
        states.append({"state_code": code, "state_name": name, "region": region, "country": country})
    cid = 1
    for city, code, country in T.BZ_CITIES:
        cities.append({"city_id": cid, "city_name": city, "state_code": code, "country": country})
        cid += 1
    return pd.DataFrame(cities), pd.DataFrame(states)


def build_bz_products(rng, mm: pd.DataFrame, n: int = 700) -> pd.DataFrame:
    """BZ04. About a third of the catalogue overlaps with Meridian (same UPC)."""
    mm_real = mm[(mm["PROD_CD"] != "PRD-99999") & (~mm["PROD_CD"].isin(DISCONTINUED))].reset_index(drop=True)
    shared = mm_real.sample(220, random_state=int(rng.integers(0, 10**6))).reset_index(drop=True)
    rows = []
    seen = {str(x).lower() for x in shared["PROD_NAME"]}
    for i in range(1, n + 1):
        if i <= len(shared):
            s = shared.iloc[i - 1]
            name, brand, cat, sub, upc, price = (s["PROD_NAME"], s["BRAND"], s["category"], s["subcategory"],
                                                 s["UPC"], s["price"])
            price = money(float(price) * float(rng.uniform(0.92, 1.05)))
            mm_cd = s["PROD_CD"]
        else:
            cat_t = T.CATEGORIES[i % len(T.CATEGORIES)]
            cat, sub = cat_t[0], cat_t[1][(i // 5) % len(cat_t[1])]
            brand = T.BZ_BRANDS[(i * 3) % len(T.BZ_BRANDS)]
            noun = T.NOUNS[sub][(i // 2) % len(T.NOUNS[sub])]
            name = f"{brand} {noun} {T.VARIANTS[(i * 5) % len(T.VARIANTS)]}"
            k = 2
            while name.lower() in seen:
                name = f"{brand} {noun} {T.VARIANTS[(i * 5) % len(T.VARIANTS)]} {k}"
                k += 1
            lo, hi = T.PRICE_RANGE[cat]
            price = money(float(np.exp(rng.uniform(np.log(lo), np.log(hi)))))
            upc = f"{(i * 104729 + 777) % 10**12:012d}"
            mm_cd = None
        seen.add(name.lower())
        rows.append({"product_code": str(i), "product_name": name, "brand": brand, "category": cat,
                     "subcategory": sub, "upc": upc, "price_usd": price, "mm_match": mm_cd})
    df = pd.DataFrame(rows)
    dup = df[df.index % 41 == 0].head(15)                        # trap 24: twins with another code
    twins = []
    for k, r in enumerate(dup.itertuples(index=False)):
        twins.append({**r._asdict(), "product_code": str(n + 1 + k), "mm_match": None,
                      "product_name": r.product_name if k % 2 else r.product_name + " "})
    df = pd.concat([df, pd.DataFrame(twins)], ignore_index=True)
    df.loc[len(df)] = {"product_code": "99999", "product_name": "Test Product - QA", "brand": "QA",
                       "category": "Test", "subcategory": "Test", "upc": "", "price_usd": money("1.00"),
                       "mm_match": None}
    return df


def build_bz_users(rng, n: int, members: pd.DataFrame, cities: pd.DataFrame):
    first = rng.choice(T.FIRST_NAMES, n)
    last = rng.choice(T.LAST_NAMES, n)
    real_members = members[members["MEMBER_NO"] != "999"].reset_index(drop=True)
    overlap = set(rng.choice(n, 2600, replace=False).tolist())       # same person in both companies
    ov_members = real_members.sample(2600, random_state=7).reset_index(drop=True)
    us = cities[cities["country"] == "US"]["city_id"].to_numpy()
    ca = cities[cities["country"] == "CA"]["city_id"].to_numpy()
    gb = cities[cities["country"] == "GB"]["city_id"].to_numpy()
    eu = cities[cities["country"].isin(["DE", "FR"])]["city_id"].to_numpy()
    users, details, addrs = [], [], []
    aid = 1
    k_ov = 0
    for i in range(n):
        uid = 100001 + i
        r = rng.random()
        pool, country = (us, "US") if r < 0.85 else (ca, "CA") if r < 0.92 else (gb, "GB") if r < 0.96 else (eu, "EU")
        if i in overlap and country == "US":
            m = ov_members.iloc[k_ov % len(ov_members)]
            k_ov += 1
            fn, ln, email = m["FIRST_NAME"], m["LAST_NAME"], m["EMAIL"]
            email = email.upper() if i % 3 == 0 else email.capitalize()  # trap 18: case differs
        else:
            fn, ln = first[i], last[i]
            email = f"{fn.lower()}{ln.lower()[:4]}{uid % 1000}@{T.EMAIL_DOMAINS[(i + 1) % 3]}"
        created = START - timedelta(days=int(rng.integers(0, 900))) + timedelta(days=int(rng.integers(0, 880)))
        users.append({"user_id": str(uid), "email": email, "created_at": f"{created}T{int(rng.integers(0, 24)):02d}:"
                      f"{int(rng.integers(0, 60)):02d}:00Z", "status": "active", "country_group": country})
        details.append({"user_id": str(uid), "first_name": fn, "last_name": ln,
                        "phone": f"555-01{uid % 100:02d}", "birth_year": str(1950 + uid % 55)})
        n_addr = 1 + int(rng.random() < 0.35) + int(rng.random() < 0.10)   # trap 26: many addresses
        home = int(rng.choice(pool))
        for a in range(n_addr):
            city = home if a == 0 else int(rng.choice(pool))
            addrs.append({"address_id": str(aid), "user_id": str(uid),
                          "address_type": "shipping" if a != 1 else "billing",
                          "street": f"{100 + (uid * 7 + a) % 9800} {T.STREETS[(uid + a) % len(T.STREETS)]}",
                          "city_id": str(city), "zip_code": f"{(uid * 13 + a) % 99999:05d}",
                          "is_default": "1" if a == 0 else "0"})
            aid += 1
    u = pd.DataFrame(users)
    u.loc[len(u)] = {"user_id": "900000", "email": "qa.tester@example.com", "created_at": "2024-06-01T00:00:00Z",
                     "status": "test", "country_group": "US"}                 # trap 6: test user
    details.append({"user_id": "900000", "first_name": "QA", "last_name": "Tester", "phone": "555-0100",
                    "birth_year": "1990"})
    addrs.append({"address_id": str(aid), "user_id": "900000", "address_type": "shipping",
                  "street": "1 Test Way", "city_id": str(int(us[0])), "zip_code": "00000", "is_default": "1"})
    return u, pd.DataFrame(details), pd.DataFrame(addrs)


def build_bz_orders(rng, cfg, users, addrs, cities, products, fx):
    rate = fx_lookup(fx)
    country_cur = {"US": "USD", "CA": "CAD", "GB": "GBP", "DE": "EUR", "FR": "EUR"}
    city_country = dict(zip(cities["city_id"].astype(str), cities["country"]))
    ship_addr = addrs[addrs["is_default"] == "1"].set_index("user_id")["address_id"].to_dict()
    bill_addr = addrs[addrs["address_type"] == "billing"].groupby("user_id")["address_id"].first().to_dict()
    addr_city = dict(zip(addrs["address_id"], addrs["city_id"]))
    real_users = users[users["user_id"] != "900000"]
    uid_arr = real_users["user_id"].to_numpy()
    u_weights = rng.gamma(0.6, 1.0, len(uid_arr))
    u_weights /= u_weights.sum()
    sellable = products[(products["product_code"] != "99999") &
                        (products["product_code"].astype(int) <= 700)].reset_index(drop=True)
    p_w = 1.0 / np.arange(1, len(sellable) + 1) ** 0.8
    p_w = rng.permutation(p_w)
    p_w /= p_w.sum()
    sellers = [f"S{100 + i}" for i in range(60)]
    orders, items, ships, invoices, payments = [], [], [], [], []
    oid, iid, sid, inv_id, pay_id = 5000001, 1, 1, 700001, 900001
    n_days = (END - START).days
    lo, hi = cfg["bz_orders_per_day"]
    test_days = set(rng.choice(n_days + 1, 25, replace=False).tolist())
    ny = ZoneInfo("America/New_York")
    for di, d in enumerate(daterange(START, END)):
        lam = lo + (hi - lo) * di / n_days
        lam *= 2.5 if d in BLACK_FRIDAYS else (1.3 if d.month == 12 else 1.0)
        n = int(rng.poisson(lam))
        day_users = list(rng.choice(uid_arr, n, p=u_weights))
        if di in test_days:
            day_users.append("900000")
        for uid in day_users:
            local = datetime.combine(d, time(0)) + timedelta(minutes=int(rng.integers(0, 1440)))
            ts_utc = local.replace(tzinfo=ny).astimezone(timezone.utc)
            local_date = ts_utc.astimezone(ny).date()
            ship = ship_addr[uid]
            bill = bill_addr.get(uid, ship)
            country = city_country[addr_city[ship]]
            cur = country_cur[country]
            r, r_date = (Decimal(1), local_date) if cur == "USD" else rate(cur, local_date)
            if d >= CHANNEL_50_FROM and rng.random() < 0.08:
                ch = "50"
            else:
                ch = ["10", "20", "30", "40"][int(rng.choice(4, p=[0.45, 0.25, 0.22, 0.08]))]
            age = (END - d).days
            if uid == "900000":
                status = "delivered"
            elif age <= 2:
                status = "placed" if rng.random() < 0.6 else "shipped"
            elif age <= 6:
                status = "shipped" if rng.random() < 0.5 else "delivered"
            else:
                x = rng.random()
                status = "cancelled" if x < 0.06 else "returned" if x < 0.13 else "delivered"
            n_items = 1 + int(rng.poisson(1.2))
            pidx = rng.choice(len(sellable), n_items, p=p_w)
            total = Decimal(0)
            usd_total = Decimal(0)
            for pi in pidx:
                p = sellable.iloc[int(pi)]
                qty = 1 + int(rng.random() < 0.2)
                unit = p["price_usd"] if cur == "USD" else money(p["price_usd"] / r)
                amount = money(unit * qty)
                usd = amount if cur == "USD" else money(amount * r)
                total += amount
                usd_total += usd
                items.append({"order_item_id": str(iid), "order_id": str(oid), "product_name": p["product_name"],
                              "product_code_true": p["product_code"], "seller_id": sellers[int(pi) % 60],
                              "qty": qty, "unit_price": unit, "amount": amount, "amount_usd": usd})
                iid += 1
            orders.append({"order_id": str(oid), "user_id": uid, "ts_utc": ts_utc, "local_date": local_date,
                           "channel_code": ch, "status": status, "currency": cur, "items_total": total,
                           "usd_total": usd_total, "fx_rate": r, "fx_date": r_date, "ship_address_id": ship,
                           "bill_address_id": bill, "country": country})
            if status != "cancelled":
                invoices.append({"invoice_id": str(inv_id), "order_id": str(oid),
                                 "invoice_date": (ts_utc + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
                                 "amount": total, "currency": cur})
                payments.append({"payment_id": str(pay_id), "invoice_id": str(inv_id),
                                 "method": T.PAY_METHODS[int(rng.integers(0, len(T.PAY_METHODS)))],
                                 "amount": total, "paid_at": (ts_utc + timedelta(minutes=7)).isoformat().replace("+00:00", "Z")})
                inv_id += 1
                pay_id += 1
            if status in ("shipped", "delivered", "returned"):
                n_ship = 2 if rng.random() < 0.03 else 1                   # trap 27: double shipment
                for k in range(n_ship):
                    shipped = ts_utc + timedelta(hours=int(rng.integers(12, 72)) + 24 * k)
                    delivered = (shipped + timedelta(hours=int(rng.integers(30, 160)))
                                 if status != "shipped" else None)
                    ships.append({"shipment_id": str(sid), "order_id": str(oid), "carrier": T.CARRIERS[sid % 4],
                                  "shipped_at": shipped.isoformat().replace("+00:00", "Z"),
                                  "delivered_at": delivered.isoformat().replace("+00:00", "Z") if delivered else ""})
                    sid += 1
            oid += 1
    return (pd.DataFrame(orders), pd.DataFrame(items), pd.DataFrame(ships), pd.DataFrame(invoices),
            pd.DataFrame(payments))


def order_files(out: Path, orders: pd.DataFrame, items: pd.DataFrame, rng) -> None:
    """BZ05: split by year, schema differs per year, 2027 arrives as daily files (traps 4, 11, 28)."""
    csv_dir = out / "bazaarly" / "csv"
    o = orders.copy()
    o["order_date"] = o["ts_utc"].map(lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ"))
    o["order_total"] = o["items_total"]
    mism = o.index.isin(rng.choice(o.index.to_numpy(), 40, replace=False))  # trap 21: 40 headers != lines
    o.loc[mism, "order_total"] = o.loc[mism, "order_total"].map(lambda d: d + Decimal("4.99"))
    o["status_code"] = o["status"]
    o["year"] = o["local_date"].map(lambda d: d.year)
    y25 = o[o["year"] == 2025].copy()
    y25["legacy_ref"] = ["LEG-" + x[-6:] for x in y25["order_id"]]
    y25["hash_key"] = [f"{h(x) * 2654435761 % 16**12:012x}" for x in y25["order_id"]]
    y25["source_id"] = "bzapp-v1"
    y25["promo_code"] = ""                                                 # trap 4: empty column
    cols25 = ["order_id", "legacy_ref", "user_id", "order_date", "channel_code", "status_code", "currency",
              "order_total", "ship_address_id", "bill_address_id", "hash_key", "source_id", "promo_code"]
    write_csv(csv_dir / "bz_orders_2025.csv", y25[cols25])
    y26 = o[o["year"] == 2026].copy()
    y26["coupon_code"] = np.where(y26.index % 17 == 0, "SAVE10", "")
    cols26 = ["order_id", "user_id", "order_date", "channel_code", "status_code", "currency", "order_total",
              "ship_address_id", "bill_address_id", "coupon_code"]
    write_csv(csv_dir / "bz_orders_2026.csv", y26[cols26])
    y27 = o[o["year"] == 2027].copy()
    y27["notes"] = np.where(y27.index % 23 == 0, "gift wrap", "")
    d27 = out / "bazaarly" / "bz_orders_2027"
    d27.mkdir(parents=True, exist_ok=True)
    for d, g in y27.groupby("local_date"):
        g = g.copy()
        status_col = "status" if d >= DRIFT_DAY else "status_code"
        g[status_col] = g["status"] if status_col == "status" else g["status_code"]
        cols = ["order_id", "user_id", "order_date", "channel_code", status_col, "currency", "order_total",
                "ship_address_id", "bill_address_id", "notes"]
        write_csv(d27 / f"bz_orders_{d:%Y%m%d}.csv", g[cols])
    it = items.copy()
    it["product_name"] = [n.upper() if i % 53 == 0 else (" " + n if i % 71 == 0 else n)
                          for i, n in enumerate(it["product_name"])]       # trap 25: joined by name
    write_csv(csv_dir / "bz_order_items.csv",
              it[["order_item_id", "order_id", "product_name", "seller_id", "qty", "unit_price", "amount"]])


def build_events(rng, cfg, orders: pd.DataFrame, products: pd.DataFrame, out: Path) -> int:
    """BZ09: daily JSON Lines, duplicates and late events, ts renamed to event_time (trap 10)."""
    ev_dir = out / "bazaarly" / "events"
    ev_dir.mkdir(parents=True, exist_ok=True)
    users = orders["user_id"].unique()
    codes = products["product_code"].to_numpy()
    total, late_bucket = 0, []
    eid = 1
    for d in daterange(START, END):
        n = int(rng.poisson(cfg["events_per_day"] * (1.2 if d.month == 12 else 1.0)))
        rows = late_bucket
        late_bucket = []
        field = "event_time" if d >= EVENT_RENAME_DAY else "ts"
        for _ in range(n):
            t = datetime.combine(d, time(0), tzinfo=timezone.utc) + timedelta(seconds=int(rng.integers(0, 86400)))
            e = {"event_id": f"e{eid:09d}", field: t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "user_id": str(rng.choice(users)), "session_id": f"s{eid // 6:08d}",
                 "event_type": T.EVENT_TYPES[int(rng.choice(4, p=[0.62, 0.2, 0.1, 0.08]))],
                 "product_code": str(rng.choice(codes))}
            eid += 1
            if rng.random() < 0.02:
                late_bucket.append(e)                         # arrives in tomorrow's file
                continue
            rows.append(e)
            if rng.random() < 0.01:
                rows.append(dict(e))                          # duplicate
        with open(ev_dir / f"events_{d:%Y%m%d}.jsonl", "w", encoding="utf-8") as f:
            for e in rows:
                f.write(json.dumps(e, separators=(",", ":")) + "\n")
        total += len(rows)
    return total


def build_payment_txns(rng, orders: pd.DataFrame, users: pd.DataFrame) -> pd.DataFrame:
    """BZ10: one card transaction per paid order; about 0.6% fraud (imbalanced, Chapter 12)."""
    paid = orders[orders["status"] != "cancelled"].reset_index(drop=True)
    n = len(paid)
    fraud = rng.random(n) < 0.006
    country = paid["country"].replace({"DE": "DE", "FR": "FR"}).to_numpy()
    ip_country = np.where(fraud & (rng.random(n) < 0.7), rng.choice(["RU", "NG", "BR", "CN", "VN"], n), country)
    hour = paid["ts_utc"].map(lambda t: t.hour).to_numpy()
    hour = np.where(fraud & (rng.random(n) < 0.6), rng.integers(0, 5, n), hour)
    amount = paid["usd_total"].map(float).to_numpy()
    amount = np.where(fraud, np.round(amount * rng.uniform(2, 6, n), 2), amount)
    dev = np.array([f"d{h(u) % 10**7:07d}" for u in paid["user_id"]])
    dev = np.where(fraud & (rng.random(n) < 0.5), rng.choice(["d0666001", "d0666002", "d0666003"], n), dev)
    return pd.DataFrame({"txn_id": [f"T{9000000 + i}" for i in range(n)], "order_id": paid["order_id"],
                         "user_id": paid["user_id"], "device_id": dev, "card_country": country,
                         "ip_country": ip_country, "hour": hour.astype(int), "amount_usd": amount,
                         "is_fraud": fraud.astype(int)})


# --------------------------------------------------------------------------- truth -> control
def control_and_answers(rec, lin, mm_prod, stores, orders, items, bz_prod, members, users, ships,
                        campaign_products, targets, addrs, cities) -> tuple[dict, dict]:
    # Meridian: net sales = sum of line amounts, test receipts excluded, local date
    r = rec[~rec["is_test"]].copy()
    l = lin.merge(r[["receipt_no", "store_id", "local_date", "member_no"]], on="receipt_no", how="inner")
    l["period"] = l["local_date"].map(lambda d: f"{d:%Y-%m}")
    l["usd"] = l["amount_cents"].map(lambda c: Decimal(c) / 100)
    mm_month = l.groupby("period")["usd"].sum()
    # Bazaarly: net sales = items in USD, test user / cancelled / returned excluded, ET order date
    o = orders[(orders["user_id"] != "900000") & (~orders["status"].isin(["cancelled", "returned"]))]
    it = items.merge(o[["order_id", "local_date", "channel_code", "user_id", "ship_address_id"]],
                     on="order_id", how="inner")
    it["period"] = it["local_date"].map(lambda d: f"{d:%Y-%m}")
    bz_month = it.groupby("period")["amount_usd"].sum()
    periods = [f"{d:%Y-%m}" for d in pd.date_range(START, END, freq="MS")]
    net = {"MM": {p: float(mm_month.get(p, Decimal(0))) for p in periods},
           "BZ": {p: float(bz_month.get(p, Decimal(0))) for p in periods}}
    bz_orders_m = o.assign(period=o["local_date"].map(lambda d: f"{d:%Y-%m}")).groupby("period")["order_id"].nunique()
    control = {
        "_note": "Generated before the traps were added. Net sales: test records and cancelled/returned orders "
                 "excluded, returns netted, shipping and tax excluded, order-day FX (weekends: last business day).",
        "net_sales_usd": net,
        "orders": {"BZ": {p: int(bz_orders_m.get(p, 0)) for p in periods}},
        "receipts": {"MM": {p: int(l[l["period"] == p]["receipt_no"].nunique()) for p in periods}},
        "products": {"MM": int((mm_prod["PROD_CD"] != "PRD-99999").sum()),
                     "BZ": int((bz_prod["product_code"] != "99999").sum())},
        "active_customers_2026": None,
    }
    # ----------------------------------------------------------- answer key (Chapter 11, 17, 18)
    y26 = lambda df: df[df["period"].str.startswith("2026")]
    q01 = float(y26(l)["usd"].sum() + y26(it)["amount_usd"].sum())
    mar27 = it[it["period"] == "2027-03"]
    q02 = int(mar27["order_id"].nunique())
    cat_mm = l.merge(mm_prod[["PROD_CD", "category"]], left_on="product_id", right_on="PROD_CD")
    bzp = bz_prod.set_index("product_code")
    mm_cat = dict(zip(mm_prod["PROD_CD"], mm_prod["category"]))
    it["category"] = [mm_cat[bzp.at[c, "mm_match"]] if isinstance(bzp.at[c, "mm_match"], str)
                      else bzp.at[c, "category"] for c in it["product_code_true"]]
    cats = (y26(cat_mm).groupby("category")["usd"].sum()
            .add(y26(it).groupby("category")["amount_usd"].sum(), fill_value=Decimal(0)))
    q03 = [c for c, _ in sorted(cats.items(), key=lambda kv: -kv[1])[:3]]
    st_region = dict(zip(stores["STORE_CD"], stores["REGION"]))
    sales_reg = y26(l).assign(region=y26(l)["store_id"].map(st_region)).groupby("region")["usd"].sum()
    t26 = targets[targets["month"].str.startswith("2026")].copy()
    t26["region"] = t26["store_id"].map(st_region)
    tgt_reg = t26.groupby("region")["target_usd"].sum()
    margin = {reg: float(sales_reg[reg] - tgt_reg[reg]) for reg in sales_reg.index}
    q04 = max(margin, key=margin.get)
    od = orders[(orders["user_id"] != "900000") & (orders["status"] != "cancelled")]
    sh = ships[ships["delivered_at"] != ""].copy()
    sh["delivered"] = pd.to_datetime(sh["delivered_at"], utc=True)
    last_del = sh.groupby("order_id")["delivered"].max()
    od = od[od["order_id"].isin(last_del.index)]
    secs = [(last_del[oid] - ts).total_seconds() for oid, ts in zip(od["order_id"], od["ts_utc"])]
    q05 = round(float(np.mean(secs)) / 86400, 2)
    mf = members_file(members)
    m_emails = set(mf.loc[(mf["MEMBER_NO"] != "999") & (mf["EMAIL"].str.contains("@")), "EMAIL"].str.strip().str.lower())
    u_emails = set(users.loc[users["user_id"] != "900000", "email"].str.strip().str.lower())
    q06 = len(m_emails & u_emails)
    bfw = l[(l["local_date"] >= date(2025, 11, 24)) & (l["local_date"] <= date(2025, 11, 30))]
    q07 = float(bfw["usd"].sum())
    ch_names = {"10": "web", "20": "ios", "30": "android", "40": "partner_api"}
    ch = it.assign(channel=it["channel_code"].map(lambda c: ch_names.get(c, "UNMAPPED")))
    ch_sales = ch.groupby("channel")["amount_usd"].sum()
    q08 = ch_sales.idxmax()
    addr_city = dict(zip(addrs["address_id"], addrs["city_id"]))
    city_country = dict(zip(cities["city_id"].astype(str), cities["country"]))
    it["ship_country"] = it["ship_address_id"].map(lambda a: city_country[addr_city[a]])
    q09 = float(y26(it)[y26(it)["ship_country"] == "CA"]["amount_usd"].sum())
    camp = set(campaign_products["product_id"]) & set(mm_prod["PROD_CD"])
    sold = set(l["product_id"]) | {bzp.at[c, "mm_match"] for c in it["product_code_true"]
                                   if isinstance(bzp.at[c, "mm_match"], str)}
    q10 = len(camp - sold)
    answers = {"q01": round(q01, 2), "q02": q02, "q03": q03, "q04": q04, "q05": q05, "q06": q06,
               "q07": round(q07, 2), "q08": q08, "q09": round(q09, 2), "q10": q10,
               "_definitions": {
                   "q01": "SUM(gold.fact_sales.amount_usd) for 2026, both companies",
                   "q02": "COUNT(DISTINCT order_id) in gold.fact_sales, source_company='BZ', March 2027 (ET date)",
                   "q03": "top 3 dim_product.category by 2026 net sales, highest first",
                   "q04": "Census region with the largest (sales - target) in USD for 2026 (Meridian stores)",
                   "q05": "average days from order_ts_utc to last delivery, delivered non-test orders",
                   "q06": "distinct normalized e-mails present as both a Meridian member and a Bazaarly user",
                   "q07": "Meridian net sales, local dates 2025-11-24 .. 2025-11-30",
                   "q08": "channel name with the largest Bazaarly net sales (all periods)",
                   "q09": "Bazaarly 2026 net sales shipped to Canada, USD",
                   "q10": "Meridian products listed in a campaign that never appear in gold.fact_sales"}}
    return control, answers


# --------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description="Generate the Meridian Market / Bazaarly synthetic data set")
    ap.add_argument("--size", choices=list(SIZES), default="small")
    ap.add_argument("--seed", type=int, default=2027)
    ap.add_argument("--out", default="data/raw")
    a = ap.parse_args()
    cfg = SIZES[a.size]
    rng = np.random.default_rng(a.seed)
    out = Path(a.out)
    if out.exists():
        for child in out.iterdir():
            if child.name != ".gitkeep":
                shutil.rmtree(child) if child.is_dir() else child.unlink()
    out.mkdir(parents=True, exist_ok=True)
    ref = ROOT / "ref"
    ref.mkdir(exist_ok=True)
    print(f"[generate] size={a.size} seed={a.seed} out={out}")

    fx = build_fx(rng)
    stores = build_stores()
    mm_prod = build_mm_products(rng)
    members = build_members(rng, cfg["members"])
    rec, lin = build_pos(rng, cfg, stores, mm_prod, members)
    cities, states = build_bz_geo()
    bz_prod = build_bz_products(rng, mm_prod)
    users, details, addrs = build_bz_users(rng, cfg["users"], members, cities)
    orders, items, ships, invoices, payments = build_bz_orders(rng, cfg, users, addrs, cities, bz_prod, fx)
    items = items.merge(bz_prod[["product_code"]], left_on="product_code_true", right_on="product_code",
                        how="left").drop(columns="product_code")

    # ---------------- Meridian files
    mm = out / "meridian"
    st_file = stores.copy()
    st_file.loc[st_file["REGION"] == "Midwest", "REGION"] = np.where(
        st_file.loc[st_file["REGION"] == "Midwest"].index % 2 == 0, "Mid-West", "Midwest")   # trap 15
    write_csv(mm / "mm_stores.csv", st_file)
    regions = pd.DataFrame([{"STATE": s, "REGION_NAME": rg, "REGION_MANAGER": f"rm.{rg.lower()}@meridian.example.com"}
                            for s, rg in sorted({(r.STATE, r.REGION) for r in stores.itertuples()})])
    write_csv(mm / "mm_regions.csv", regions)
    write_csv(mm / "mm_products.csv", mm_products_file(mm_prod), encoding="utf-8")
    write_csv(mm / "mm_loyalty_members.csv", members_file(members))
    write_pos_files(out, rec, lin, rng)
    vendors = pd.DataFrame([{"VENDOR_ID": f"V{200 + i}", "VENDOR_NAME": f"{T.BRANDS[i % len(T.BRANDS)]} Supply Co.",
                             "HASH_KEY": f"{(i * 2654435761) % 16**16:016x}",
                             "TERMS": T.VENDOR_TERMS[i % len(T.VENDOR_TERMS)]} for i in range(80)])
    write_csv(mm / "mm_vendors.csv", vendors)
    # MM05 inventory: one column per month, product linked by NAME, header repeated inside the data
    real = mm_prod[mm_prod["PROD_CD"] != "PRD-99999"].reset_index(drop=True)
    months = [f"{d:%Y-%m}" for d in pd.date_range(START, END, freq="MS")]
    inv = pd.DataFrame({"PROD_NAME": real["PROD_NAME"]})
    for m in months:
        inv[m] = rng.integers(0, 400, len(inv))
    inv.loc[3, "PROD_NAME"] = inv.loc[3, "PROD_NAME"] + "x"                           # 3 names that will not match
    inv.loc[77, "PROD_NAME"] = inv.loc[77, "PROD_NAME"] + "s"
    inv.loc[151, "PROD_NAME"] = inv.loc[151, "PROD_NAME"].replace(" ", "  ", 1)
    header = pd.DataFrame([dict(zip(inv.columns, inv.columns))])
    inv_out = pd.concat([inv.iloc[:300], header, inv.iloc[300:]], ignore_index=True)  # trap 3 / 12
    with pd.ExcelWriter(mm / "mm_inventory_monthly.xlsx") as xw:
        inv_out.to_excel(xw, index=False, sheet_name="inventory")
    # MM07 / MM08 campaigns
    camps, cp_rows, log_rows = [], [], []
    for c in range(1, 25):
        startd = START + timedelta(days=int(rng.integers(0, 860)))
        endd = startd + timedelta(days=int(rng.integers(7, 35)))
        name = f"{T.CAMPAIGN_WORDS[c % len(T.CAMPAIGN_WORDS)]} {startd:%b %Y}"
        chan = ["email", "social", "tv", "in-store"][c % 4]
        n_p = int(rng.integers(4, 14))
        codes = list(rng.choice(real["PROD_CD"], n_p, replace=False))
        if c % 4 == 0:
            codes.append(DISCONTINUED[(c // 4) % len(DISCONTINUED)])           # never sold (q10)
        if c == 13:
            codes.append("PRD-0O042")                                           # typo: letter O, no such product
        sep = [", ", ";", " , ", "; "]
        cp_rows.append({"CAMPAIGN_NAME": name,
                        "PROD_CODES": "".join(code + sep[(c + j) % 4] for j, code in enumerate(codes)).rstrip(",; ")})
        for d in daterange(startd, min(endd, END)):
            log_rows.append({"CAMPAIGN_ID": f"C{c:03d}", "CAMPAIGN_NAME": name, "CHANNEL": chan,
                             "START_DATE": startd.isoformat(), "END_DATE": endd.isoformat(), "DAY": d.isoformat(),
                             "SPEND_USD": f"{rng.uniform(200, 4000):.2f}", "IMPRESSIONS": int(rng.integers(5000, 90000))})
        camps.append({"campaign": name, "codes": [x.strip() for x in codes]})
    cp = pd.DataFrame(cp_rows)
    cp = pd.concat([pd.DataFrame([{"CAMPAIGN_NAME": "CAMPAIGN_NAME", "PROD_CODES": "PROD_CODES"}]), cp],
                   ignore_index=True)                                            # trap 3: header in data
    write_csv(mm / "mm_campaign_products.csv", cp)
    write_csv(mm / "mm_campaign_log.csv", pd.DataFrame(log_rows))
    campaign_products = pd.DataFrame([{"campaign": c["campaign"], "product_id": p} for c in camps for p in c["codes"]])
    # MM09 targets: store x month, text month, about +/-10% around the true sales
    true_sm = (lin.merge(rec[~rec["is_test"]][["receipt_no", "store_id", "local_date"]], on="receipt_no")
               .assign(month=lambda df: df["local_date"].map(lambda d: f"{d:%Y-%m}"))
               .groupby(["store_id", "month"])["amount_cents"].sum().reset_index())
    true_sm["target_usd"] = [money(c / 100 * rng.uniform(0.9, 1.1)) for c in true_sm["amount_cents"]]
    targets = true_sm[["store_id", "month", "target_usd"]]
    write_csv(mm / "mm_sales_targets.csv", targets.rename(columns={"store_id": "STORE_CD", "month": "MONTH",
                                                                   "target_usd": "TARGET_USD"}))
    hr = pd.DataFrame([{"EMP_ID": f"E{1000 + i}", "FIRST_NAME": T.FIRST_NAMES[i % len(T.FIRST_NAMES)],
                        "LAST_NAME": T.LAST_NAMES[(i * 3) % len(T.LAST_NAMES)],
                        "EMAIL": f"emp{1000 + i}@meridian.example.com", "STORE_CD": f"MM-{1 + i % 48:03d}",
                        "DEPT": ["store", "store", "store", "logistics", "finance", "it"][i % 6],
                        "HIRE_DATE": f"{2010 + i % 16}-{1 + i % 12:02d}-15", "SALARY_BAND": f"B{1 + i % 6}"}
                       for i in range(900)])
    write_csv(mm / "mm_hr_employees.csv", hr)
    acc = pd.DataFrame([{"ACCOUNT_ID": f"A-{i:04d}", "ACCOUNT_NAME": f"{T.LAST_NAMES[i % len(T.LAST_NAMES)]} "
                         f"{['Catering', 'Office Supply', 'Fitness', 'Hotels', 'Schools'][i % 5]} LLC",
                         "CONTACT_EMAIL": (members.iloc[i * 11]["EMAIL"] if i % 9 == 0 else
                                           f"purchasing{i}@{T.EMAIL_DOMAINS[i % 3]}"),
                         "STATE": stores.iloc[i % 48]["STATE"], "CREDIT_LIMIT": f"{(i % 20 + 1) * 2500}"}
                        for i in range(1, cfg["accounts"] + 1)])
    write_csv(mm / "mm_finance_accounts.csv", acc)

    # ---------------- Bazaarly files
    bz = out / "bazaarly"
    csv_dir = bz / "csv"
    u_out = users.drop(columns="country_group")
    write_csv(csv_dir / "bz_users.csv", u_out)
    write_csv(csv_dir / "bz_user_details.csv", details)
    write_csv(csv_dir / "bz_user_addresses.csv", addrs)
    c_out = cities.merge(states[["state_code", "state_name", "region"]], on="state_code", how="left")
    c_out["state"] = [T.state_spelling(code, name, i) for i, (code, name) in
                      enumerate(zip(c_out["state_code"], c_out["state_name"]))]     # trap 15
    c_out = c_out[["city_id", "city_name", "state", "country", "region"]]
    c_out = pd.concat([pd.DataFrame([dict(zip(c_out.columns, c_out.columns))]), c_out], ignore_index=True)
    write_csv(csv_dir / "bz_cities.csv", c_out)
    write_csv(csv_dir / "bz_states.csv", states)
    sellers = pd.DataFrame([{"seller_id": f"S{100 + i}", "seller_name": f"{T.BZ_BRANDS[i % len(T.BZ_BRANDS)]} Store {i}",
                             "commission_rate": f"{8 + i % 10}%", "country": "US" if i % 7 else "CA",
                             "joined_at": f"{2019 + i % 6}-0{1 + i % 9}-01"} for i in range(60)])
    write_csv(csv_dir / "bz_sellers.csv", sellers)
    p_out = bz_prod.copy()
    p_out["price"] = p_out["price_usd"]
    p_out["upc"] = ["N/A" if i % 13 == 0 else "" if i % 17 == 0 else u for i, u in enumerate(p_out["upc"])]
    p_out["hash_key"] = [f"{(int(c) * 40503) % 16**10:010x}" for c in p_out["product_code"]]
    p_out["source_id"] = "catalog-svc"
    p_out["legacy_flag"] = ""                                                         # trap 4
    p_out["description"] = [T.long_description(n, i) for i, n in enumerate(p_out["product_name"])]
    write_csv(csv_dir / "bz_products.csv",
              p_out[["product_code", "product_name", "brand", "category", "subcategory", "upc", "price",
                     "hash_key", "source_id", "legacy_flag", "description"]])
    mapping = bz_prod[(bz_prod["mm_match"].notna()) & (bz_prod["product_code"].astype(int) <= 700)].copy()
    no_upc = mapping[[p_out.loc[i, "upc"] in ("", "N/A") for i in mapping.index]]
    write_csv(ref / "product_mapping.csv",
              no_upc.rename(columns={"mm_match": "mm_product_id", "product_code": "bz_product_id"})
              [["mm_product_id", "bz_product_id"]])
    order_files(out, orders, items, rng)
    write_csv(csv_dir / "bz_invoices.csv", invoices)
    write_csv(csv_dir / "bz_payments.csv", payments)
    write_csv(csv_dir / "bz_shipments.csv", ships)
    shutil.copyfile(csv_dir / "bz_shipments.csv", csv_dir / "Sheet1.csv")              # trap 5
    junk = pd.DataFrame({"col1": [f"x{i}" for i in range(40)], "col2": [""] * 40,
                         "Unnamed: 3": [str(i * 3.14) for i in range(40)]})
    write_csv(csv_dir / "dim_order.csv", junk)                                         # trap 5
    n_events = build_events(rng, cfg, orders, bz_prod, out)
    txns = build_payment_txns(rng, orders, users)
    try:
        txns.to_parquet(bz / "bz_payment_transactions.parquet", index=False)
    except ImportError:
        print("[generate] pyarrow not installed: BZ10 written as CSV (pip install pyarrow for Parquet)")
        write_csv(bz / "bz_payment_transactions.csv", txns)
    tickets = T.support_tickets(rng, users, details, cfg["tickets"])
    with open(bz / "bz_support_tickets.jsonl", "w", encoding="utf-8") as f:
        for t in tickets:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    docs = bz / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    for name, title, paras in T.HELP_DOCS:
        T.write_pdf(docs / f"{name}.pdf", title, paras)
    returns = T.returns_july(rng, orders, users)
    write_csv(bz / "bz_returns.csv", returns)
    if a.size == "small":
        T.write_sql_dump(bz / "dump" / "bazaarly_dump.sql",
                         {"bz_users": u_out, "bz_user_details": details, "bz_user_addresses": addrs,
                          "bz_cities": c_out, "bz_states": states, "bz_sellers": sellers,
                          "bz_products": p_out[["product_code", "product_name", "brand", "category", "subcategory",
                                                "upc", "price", "hash_key", "source_id", "legacy_flag"]]})

    # ---------------- operations files (OP)
    ops = out / "ops"
    T.write_pdf(ops / "source_system_guide.pdf", "Bazaarly source system guide (v3.2)", T.SOURCE_GUIDE_PDF)
    write_csv(ops / "fx_rates.csv", fx)
    write_csv(ref / "channel_codes.csv", pd.DataFrame(
        [{"channel_code": c, "channel_name": n} for c, n in [("10", "web"), ("20", "ios"), ("30", "android"),
                                                              ("40", "partner_api")]]))   # 50 missing: trap 22
    write_csv(ref / "test_records.csv", pd.DataFrame(
        [{"entity": "mm_member", "key_value": "999", "note": "loyalty test member"},
         {"entity": "mm_product", "key_value": "PRD-99999", "note": "TEST - DO NOT USE"},
         {"entity": "bz_user", "key_value": "900000", "note": "QA user"},
         {"entity": "bz_product", "key_value": "99999", "note": "QA product"}]))
    write_csv(ref / "state_aliases.csv", T.state_alias_table())
    write_csv(out / "security_user_region.csv", pd.DataFrame(T.SECURITY_USERS, columns=["email", "region"]))
    T.write_pipeline_logs(ops / "pipeline_logs", rng)
    write_csv(ops / "query_history.csv", T.query_history(rng))
    T.write_legacy_sql(ops / "sql_legacy")

    # ---------------- control totals and answer key
    control, answers = control_and_answers(rec, lin, mm_prod, stores, orders, items, bz_prod, members, users,
                                           ships, campaign_products, targets, addrs, cities)
    (out / "control_totals.json").write_text(json.dumps(control, indent=2), encoding="utf-8")
    (out / "answer_key.json").write_text(json.dumps(answers, indent=2), encoding="utf-8")
    (out / "README.md").write_text(T.SYNTHETIC_NOTE, encoding="utf-8")
    print(f"[generate] POS receipts {len(rec):,}, lines {len(lin):,} | BZ orders {len(orders):,}, "
          f"items {len(items):,} | events {n_events:,} | tickets {len(tickets):,}")
    print(f"[generate] control_totals.json and answer_key.json written; q01 = {answers['q01']:,.2f}")


if __name__ == "__main__":
    main()
