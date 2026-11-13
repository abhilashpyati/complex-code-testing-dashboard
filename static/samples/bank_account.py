"""
Bank Account Management — Sample Program 2
Demonstrates class-based design with validation and exception handling.
"""
from datetime import datetime
from typing import List, Dict


class InsufficientFundsError(Exception):
    """Raised when a withdrawal exceeds the available balance."""
    pass


class AccountFrozenError(Exception):
    """Raised when an operation is attempted on a frozen account."""
    pass


class Transaction:
    """Represents a single account transaction."""

    def __init__(self, transaction_type: str, amount: float, description: str = ""):
        if amount <= 0:
            raise ValueError("Transaction amount must be positive")
        self.type = transaction_type
        self.amount = amount
        self.description = description
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Convert transaction details to dictionary representation."""
        return {
            "type": self.type,
            "amount": self.amount,
            "description": self.description,
            "timestamp": self.timestamp,
        }


class BankAccount:
    """A bank account with deposit, withdrawal, and transaction history."""

    INTEREST_RATE = 0.035  # 3.5% annual

    def __init__(self, owner: str, account_number: str, initial_balance: float = 0.0):
        """Initialize a new bank account with owner and starting balance."""
        if not owner.strip():
            raise ValueError("Account owner name cannot be empty")
        if initial_balance < 0:
            raise ValueError("Initial balance cannot be negative")
        self.owner = owner.strip()
        self.account_number = account_number
        self._balance = initial_balance
        self._frozen = False
        self._transactions: List[Transaction] = []
        if initial_balance > 0:
            self._transactions.append(
                Transaction("CREDIT", initial_balance, "Initial deposit")
            )

    @property
    def balance(self) -> float:
        """Return the current available balance."""
        return self._balance

    @property
    def is_frozen(self) -> bool:
        """Check whether the account is currently frozen."""
        return self._frozen

    def deposit(self, amount: float, description: str = "Deposit") -> float:
        """Deposit funds into the account and record credit transaction."""
        self._check_not_frozen()
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self._balance += amount
        self._transactions.append(Transaction("CREDIT", amount, description))
        return self._balance

    def withdraw(self, amount: float, description: str = "Withdrawal") -> float:
        """Withdraw funds from the account if sufficient balance exists."""
        self._check_not_frozen()
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        if amount > self._balance:
            raise InsufficientFundsError(
                f"Insufficient funds: balance is {self._balance:.2f}, "
                f"requested {amount:.2f}"
            )
        self._balance -= amount
        self._transactions.append(Transaction("DEBIT", amount, description))
        return self._balance

    def transfer(self, target: "BankAccount", amount: float) -> float:
        """Transfer funds from this account to a destination target account."""
        self.withdraw(amount, f"Transfer to {target.account_number}")
        target.deposit(amount, f"Transfer from {self.account_number}")
        return self._balance

    def apply_interest(self) -> float:
        """Calculate and apply accrued annual interest to account balance."""
        self._check_not_frozen()
        interest = self._balance * self.INTEREST_RATE
        if interest > 0:
            self._balance += interest
            self._transactions.append(
                Transaction("CREDIT", interest, "Annual interest")
            )
        return interest

    def freeze(self):
        """Freeze account to prevent further withdrawals or transactions."""
        self._frozen = True

    def unfreeze(self):
        """Unfreeze account to restore normal transaction processing."""
        self._frozen = False

    def get_statement(self) -> List[Dict]:
        """Retrieve complete chronological list of transaction records."""
        return [t.to_dict() for t in self._transactions]

    def _check_not_frozen(self):
        """Verify account is active; raise error if account is frozen."""
        if self._frozen:
            raise AccountFrozenError("Account is frozen and cannot process transactions")

    def __repr__(self) -> str:
        return (
            f"BankAccount(owner={self.owner!r}, "
            f"account={self.account_number!r}, "
            f"balance={self._balance:.2f})"
        )


def calculate_loan_payment(principal: float, annual_rate: float, months: int) -> Dict:
    """Calculate monthly loan payment using the annuity formula."""
    if principal <= 0 or annual_rate < 0 or months <= 0:
        raise ValueError("Invalid loan parameters")
    if annual_rate == 0:
        monthly_payment = principal / months
    else:
        monthly_rate = annual_rate / 12
        monthly_payment = (
            principal
            * monthly_rate
            * (1 + monthly_rate) ** months
            / ((1 + monthly_rate) ** months - 1)
        )
    total_payment = monthly_payment * months
    total_interest = total_payment - principal
    return {
        "monthly_payment": round(monthly_payment, 2),
        "total_payment": round(total_payment, 2),
        "total_interest": round(total_interest, 2),
    }
