# json-syntax

A Python library to translate between JSON compatible structures and native Python classes using customizable rules.

## Rationale

Annotations, `typing` and `dataclasses` can provide enough information to fully describe the structure of data, and this library exploits this information to build encoders and decoders.

## Usage

```python
@dataclass
class Account:
    user: str
    transactions: List['Trans']
    balance: decimal = 0

class TransType(Enum):
    withdraw = 0
    deposit = 1

@dataclass
class Trans:
    type: TransType
    amount: decimal
    stamp: date

>>> import json_syntax as syn

>>> rules = syn.std_ruleset()
>>> encode_account = rules.lookup(typ=Account, verb='python_to_json')

>>> encode_account(Account('bob', [Trans(TransType.withdraw, Decimal('523.33'), date(2019, 4, 4))], Decimal('77.00')))
{
  'user': 'bob',
  'transactions': [
    {
      'type': 'withdraw',
      'amount': '523.33',
      'stamp': '2019-04-04'
    }
  ], 'balance': '77.00'
}
```

## Maintenance

This is maintained via the poetry[1][] tool. Some useful commands:

1. Setup: `poetry install`
2. Run tests: `poetry run pytest tests/`
3. Reformat: `poetry run black json_syntax/ tests/`
4. Publish: `poetry publish`

[1]: https://poetry.eustace.io/docs/#installation
