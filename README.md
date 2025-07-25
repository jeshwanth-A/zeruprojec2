# DeFi Wallet Risk Scorer

Analyzes wallet addresses and gives them risk scores (0-1000). Lower score = higher risk.

## Quick Start

```bash
pip install pandas requests scikit-learn
python wallet_risk_scorer.py
```

## Files

- `wallet_risk_scorer.py` - Main program (everything in one file)
- `wallets.csv` - Input wallet addresses
- `wallet_scores.csv` - Output scores
- `wallet_features.csv` - Detailed analysis

## Options

```bash
python wallet_risk_scorer.py              # Normal mode
python wallet_risk_scorer.py --simulation # Test mode
python wallet_risk_scorer.py --test       # Run tests
```

## How It Works

1. Takes wallet addresses from `wallets.csv`
2. Gets transaction data from Compound V2 protocol
3. Analyzes risk factors (liquidations, borrowing patterns, repayment history)
4. Assigns scores: 700+ = low risk, 400-699 = medium risk, 0-399 = high risk
5. Saves results to CSV files

## Risk Factors

- **Liquidation history** - Past liquidations reduce score significantly
- **Borrowing patterns** - High leverage reduces score
- **Repayment behavior** - Poor repayment reduces score
- **Activity frequency** - Extreme activity reduces score
- **Health factor** - Low collateralization reduces score

## Requirements

- Python 3.7+
- pandas, requests, scikit-learn
