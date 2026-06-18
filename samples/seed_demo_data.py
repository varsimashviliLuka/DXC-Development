#!/usr/bin/env python3
"""
Populate the Elevator Chip database with random demo data.

Standalone testing tool — not imported by the app.

Usage (from project root):
  python samples/seed_demo_data.py 50
  python samples/seed_demo_data.py --count 100 --seed 42

Requires .env (or environment) with DATABASE_URL pointing at your dev database.
Scheduler is disabled for this run.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
os.environ["SCHEDULER_ENABLED"] = "false"

from app import create_app
from app.enums import (
  ChipStatus,
  SubscriptionStatus,
  TransactionStatus,
  TransactionType,
  UserRole,
  UserStatus,
)
from app.extensions import db
from app.models import Building, Chip, Subscription, Transaction, User, UserPhone
from app.security.password import hash_password

DEMO_PASSWORD = "DemoPass123!"

FIRST_NAMES = (
  "ნინო", "გიორგი", "მარიამ", "დავით", "ანა", "ლუკა", "თამარ", "ირაკლი",
  "სალომე", "ნიკა", "თეა", "გიგა", "ელენე", "ლევან", "კეტევან",
  "Nino", "Giorgi", "Mariam", "David", "Ana", "Luka", "Tamar",
)
LAST_NAMES = (
  "ბერიძე", "კაპანაძე", "ჩხეიძე", "მელაძე", "გელაშვილი", "ხარაძე",
  "ჯანელიძე", "ლომიძე", "ნოზაძე", "კვარაცხელია", "Beridze", "Kapanadze",
)
STREETS = (
  "Rustaveli Ave", "Chavchavadze Ave", "Vazha-Pshavela Ave", "Agmashenebeli Ave",
  "Kostava St", "Pekini Ave", "Saburtalo", "Vake", "Gldani", "Didube",
)
BUILDING_PREFIXES = ("Tower", "Residence", "Plaza", "House", "Court", "Block")


class DemoSeeder:
  def __init__(self, count: int, seed: int | None = None):
    self.count = max(1, count)
    if seed is not None:
      random.seed(seed)
    self._used_id_numbers: set[str] = set()
    self._used_phones: set[str] = set()
    self._used_emails: set[str] = set()
    self._used_chip_numbers: set[str] = set()
    self._used_txn_refs: set[str] = set()
    self._used_building_doors: set[tuple[int, str]] = set()

  def _load_existing_keys(self) -> None:
    self._used_id_numbers.update(
      row[0] for row in db.session.query(User.id_number).all()
    )
    self._used_phones.update(
      row[0] for row in db.session.query(UserPhone.phone_number).all()
    )
    self._used_emails.update(
      row[0] for row in db.session.query(User.email).filter(User.email.isnot(None)).all()
    )
    self._used_chip_numbers.update(
      row[0] for row in db.session.query(Chip.chip_number).all()
    )
    self._used_txn_refs.update(
      row[0] for row in db.session.query(Transaction.reference).filter(
        Transaction.reference.isnot(None)
      ).all()
    )
    for building_id, door in db.session.query(
      Subscription.building_id, Subscription.door_number
    ).all():
      self._used_building_doors.add((building_id, door))

  def _unique_id_number(self) -> str:
    while True:
      candidate = f"01{random.randint(0, 999_999_999):09d}"
      if candidate not in self._used_id_numbers:
        self._used_id_numbers.add(candidate)
        return candidate

  def _unique_phone(self) -> str:
    while True:
      candidate = f"+9955{random.randint(0, 99_999_999):08d}"
      if candidate not in self._used_phones:
        self._used_phones.add(candidate)
        return candidate

  def _unique_email(self, first: str, last: str) -> str | None:
    if random.random() < 0.15:
      return None
    base = f"{first}.{last}".lower().replace(" ", "")
    for attempt in range(20):
      suffix = "" if attempt == 0 else str(random.randint(1, 9999))
      candidate = f"{base}{suffix}@demo.local"
      if candidate not in self._used_emails:
        self._used_emails.add(candidate)
        return candidate
    return f"user{uuid.uuid4().hex[:8]}@demo.local"

  def _unique_chip_number(self) -> str:
    while True:
      candidate = f"CHIP-{random.randint(100000, 999999)}"
      if candidate not in self._used_chip_numbers:
        self._used_chip_numbers.add(candidate)
        return candidate

  def _unique_txn_ref(self, prefix: str) -> str:
    while True:
      candidate = f"{prefix}-{uuid.uuid4().hex[:10].upper()}"
      if candidate not in self._used_txn_refs:
        self._used_txn_refs.add(candidate)
        return candidate

  def _pick_status(self) -> UserStatus:
    return random.choices(
      [UserStatus.ACTIVE, UserStatus.INACTIVE, UserStatus.SUSPENDED],
      weights=[85, 10, 5],
      k=1,
    )[0]

  def create_users(self) -> list[User]:
    users: list[User] = []
    for _ in range(self.count):
      first = random.choice(FIRST_NAMES)
      last = random.choice(LAST_NAMES)
      user = User(
        id_number=self._unique_id_number(),
        email=self._unique_email(first, last),
        password_hash=hash_password(DEMO_PASSWORD),
        role=UserRole.USER,
        status=self._pick_status(),
        balance=Decimal("0.00"),
        first_name=first,
        last_name=last,
        admin_comment=random.choice([None, None, "Demo resident"]),
      )
      db.session.add(user)
      db.session.flush()

      db.session.add(
        UserPhone(
          user_id=user.id,
          phone_number=self._unique_phone(),
          label="Personal",
          is_primary=True,
        )
      )
      if random.random() < 0.25:
        db.session.add(
          UserPhone(
            user_id=user.id,
            phone_number=self._unique_phone(),
            label=random.choice(["Family", "Spouse", "Parent"]),
            is_primary=False,
          )
        )
      users.append(user)
    return users

  def create_buildings(self) -> list[Building]:
    buildings: list[Building] = []
    for i in range(self.count):
      number = str(random.randint(100, 9999))
      prefix = random.choice(BUILDING_PREFIXES)
      building = Building(
        building_number=number,
        name=f"{prefix} {number}",
        address=f"{random.randint(1, 120)} {random.choice(STREETS)}, Tbilisi",
        admin_comment=random.choice([None, None, "Demo building"]),
      )
      db.session.add(building)
      buildings.append(building)
    db.session.flush()
    return buildings

  def create_subscriptions(
    self, users: list[User], buildings: list[Building]
  ) -> list[Subscription]:
    subscriptions: list[Subscription] = []
    attempts = 0
    max_attempts = self.count * 5

    while len(subscriptions) < self.count and attempts < max_attempts:
      attempts += 1
      user = random.choice(users)
      building = random.choice(buildings)
      door = f"{random.randint(1, 25)}{random.choice('ABCD')}"

      key = (building.id, door)
      if key in self._used_building_doors:
        continue
      self._used_building_doors.add(key)

      fee = Decimal(str(random.choice([15, 20, 25, 30, 35, 40, 50, 75])))
      status = random.choices(
        [SubscriptionStatus.ACTIVE, SubscriptionStatus.OVERDUE, SubscriptionStatus.INACTIVE],
        weights=[70, 20, 10],
        k=1,
      )[0]
      due = date.today() + timedelta(days=random.randint(-14, 45))

      sub = Subscription(
        user_id=user.id,
        building_id=building.id,
        door_number=door,
        monthly_fee=fee,
        status=status,
        next_payment_due=due,
      )
      db.session.add(sub)
      subscriptions.append(sub)

    db.session.flush()
    return subscriptions

  def create_chips(self, users: list[User]) -> list[Chip]:
    chips: list[Chip] = []
    pool = users.copy()
    random.shuffle(pool)
    for user in pool[: self.count]:
      status = random.choices(
        [ChipStatus.ACTIVE, ChipStatus.INACTIVE],
        weights=[80, 20],
        k=1,
      )[0]
      chip = Chip(
        chip_number=self._unique_chip_number(),
        user_id=user.id,
        status=status,
        deactivated_at=None,
      )
      db.session.add(chip)
      chips.append(chip)
    db.session.flush()
    return chips

  def create_transactions(
    self,
    users: list[User],
    subscriptions: list[Subscription],
  ) -> list[Transaction]:
    transactions: list[Transaction] = []
    subs_by_user: dict[int, list[Subscription]] = {}
    for sub in subscriptions:
      subs_by_user.setdefault(sub.user_id, []).append(sub)

    target = self.count * 2
    for _ in range(target):
      user = random.choice(users)
      is_payment = random.random() < 0.65
      if is_payment:
        amount = Decimal(str(random.choice([20, 30, 50, 75, 100, 150, 200])))
        txn = Transaction(
          user_id=user.id,
          amount=amount,
          transaction_type=TransactionType.PAYMENT,
          status=TransactionStatus.COMPLETED,
          description=random.choice([
            "Bank payment",
            "TBC transfer",
            "BoG income",
            "Monthly top-up",
          ]),
          reference=self._unique_txn_ref("PAY"),
        )
        user.balance += amount
      else:
        user_subs = subs_by_user.get(user.id) or subscriptions
        sub = random.choice(user_subs) if user_subs else None
        fee = Decimal(str(random.choice([15, 25, 30, 40, 50])))
        txn = Transaction(
          user_id=user.id,
          subscription_id=sub.id if sub else None,
          amount=-fee,
          transaction_type=TransactionType.FEE,
          status=TransactionStatus.COMPLETED,
          description=(
            f"Monthly fee for building {sub.building.building_number}, door {sub.door_number}"
            if sub and sub.building
            else "Monthly subscription fee"
          ),
          reference=self._unique_txn_ref("FEE"),
        )
        user.balance -= fee
        if sub and user.balance < 0:
          sub.status = SubscriptionStatus.OVERDUE
        elif sub and user.balance >= 0 and sub.status == SubscriptionStatus.OVERDUE:
          sub.status = SubscriptionStatus.ACTIVE

      db.session.add(txn)
      transactions.append(txn)

    db.session.flush()
    return transactions

  def run(self) -> dict[str, int]:
    self._load_existing_keys()
    users = self.create_users()
    buildings = self.create_buildings()
    subscriptions = self.create_subscriptions(users, buildings)
    chips = self.create_chips(users)
    transactions = self.create_transactions(users, subscriptions)
    db.session.commit()
    return {
      "users": len(users),
      "buildings": len(buildings),
      "subscriptions": len(subscriptions),
      "chips": len(chips),
      "transactions": len(transactions),
    }


def main() -> int:
  parser = argparse.ArgumentParser(
    description="Seed the Elevator Chip database with random demo data.",
  )
  parser.add_argument(
    "count",
    nargs="?",
    type=int,
    help="How many of each entity type to create (users, buildings, subscriptions, chips; ~2x transactions).",
  )
  parser.add_argument(
    "-n", "--count",
    dest="count_flag",
    type=int,
    help="Same as positional count.",
  )
  parser.add_argument(
    "--seed",
    type=int,
    default=None,
    help="Random seed for reproducible data.",
  )
  args = parser.parse_args()
  count = args.count_flag if args.count_flag is not None else args.count
  if not count or count < 1:
    parser.error("Provide a positive count, e.g. python samples/seed_demo_data.py 50")

  app = create_app()
  with app.app_context():
    seeder = DemoSeeder(count=count, seed=args.seed)
    result = seeder.run()

  print("Demo data created:")
  for key, value in result.items():
    print(f"  {key}: {value}")
  print(f"\nDemo user password: {DEMO_PASSWORD}")
  print("Log in with any generated resident ID number and that password.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
