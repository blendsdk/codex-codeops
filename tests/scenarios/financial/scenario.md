# Scenario: multi-currency transfer ledger

Design requirements for a financial platform:

- Transfer money between customer accounts that may use different currencies.
- Obtain a current exchange rate and charge a configurable percentage fee.
- Debit and credit happen asynchronously through a queue.
- Clients may retry when a request times out.
- Display the converted amount immediately after submission.
- Operations must be auditable and balances must never be wrong.
- Support cancellation while a transfer is pending and refund after completion.
- Reconcile daily against an external settlement file.

Do not choose financial semantics for the user. Identify material questions that must be resolved before a technical plan is executable.
