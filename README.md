# DeFi Wallet Risk Scorer

A Python tool that analyzes Ethereum wallet addresses for risk in Compound V2 lending protocol. Assigns scores from 0-1000 (lower = higher risk) based on transaction history.

## Features
- Fetches real on-chain data via TheGraph API (with simulation fallback)
- Engineers 17+ risk features (e.g., liquidation count, repay rate, health factor)
- Rule-based scoring with Min-Max normalization
- Parallel processing for efficiency (100+ wallets in ~1 minute)
- Unit tests and logging included

## Quick Start

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Prepare `wallets.csv` (one column: `wallet_id` with addresses).

3. Run:
   ```
   python wallet_risk_scorer.py
   ```

Outputs:
- `wallet_scores.csv`: Wallet IDs and final risk scores
- `wallet_features.csv`: Detailed feature breakdowns
- `wallet_scoring.log`: Process logs

## Options
```
python wallet_risk_scorer.py --help          # Show all options
python wallet_risk_scorer.py --simulation    # Use simulation mode for testing
python wallet_risk_scorer.py --test          # Run unit tests
python wallet_risk_scorer.py --workers 10    # Use more concurrent workers
```

For a clear, detailed explanation of methodology, features, scoring logic, and risk justification, see [explanation.md](explanation.md).

## Risk Scoring Overview
- **700-1000**: Low risk (responsible users)
- **400-699**: Medium risk (needs monitoring)
- **0-399**: High risk (avoid lending)

Factors: Liquidations (-major points), over-borrowing, poor repayment, extreme activity, low health factor.

## Requirements
- Python 3.7+
- Libraries: pandas, requests, scikit-learn (in `requirements.txt`)

## License
MIT License - see [LICENSE](LICENSE) for details.

## Contributing
Fork and PR! Issues welcome for bugs or features.