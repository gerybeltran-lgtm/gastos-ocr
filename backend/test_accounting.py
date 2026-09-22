import unittest
from decimal import Decimal

from fastapi import HTTPException

from accounting import calculate_vat, normalize_ledger


class AccountingRulesTests(unittest.TestCase):
    def test_invoice_vat_uses_chilean_gross_formula(self):
        self.assertEqual(calculate_vat(Decimal("11900"), "Factura"), Decimal("1900"))

    def test_receipt_has_no_recoverable_vat(self):
        self.assertEqual(calculate_vat(Decimal("11900"), "Boleta"), Decimal("0.00"))

    def test_mixed_funds_must_balance_exactly(self):
        origin, cash, credit, total = normalize_ledger(10000, "Fondos Mixtos", "Factura", 7500, 2500)
        self.assertEqual((origin, cash, credit, total), (
            "Fondos Mixtos", Decimal("7500.00"), Decimal("2500.00"), Decimal("10000.00")
        ))

    def test_mixed_funds_reject_imbalance(self):
        with self.assertRaises(HTTPException):
            normalize_ledger(10000, "Fondos Mixtos", "Factura", 7500, 2499)

    def test_negative_amount_is_rejected(self):
        with self.assertRaises(HTTPException):
            normalize_ledger(-1, "Caja Principal", "Boleta")


if __name__ == "__main__":
    unittest.main()
