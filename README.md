# 🏦 DeFi Wallet Risk Scoring System

[![Tests](https://github.com/YOUR_USERNAME/wallet-risk-scoring-round2/workflows/DeFi%20Wallet%20Risk%20Scorer%20Tests/badge.svg)](https://github.com/YOUR_USERNAME/wallet-risk-scoring-round2/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A comprehensive risk scoring system for DeFi wallets using Compound V2 protocol data. Analyzes on-chain transaction patterns to assign risk scores (0-1000) to wallet addresses.

![Score Distribution](score_distribution.png)

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/YOUR_USERNAME/wallet-risk-scoring-round2.git
cd wallet-risk-scoring-round2
./setup.sh

# Run with real API data (default)
python score_wallets_improved.py

# Run with simulation data
python score_wallets_improved.py --simulation

# Run with custom options
python score_wallets_improved.py --workers 10 --quiet
```

## 📊 What It Does

- **Processes 100+ wallet addresses** from `wallets.csv`
- **Fetches real on-chain data** from TheGraph Compound V2 API
- **Analyzes 17+ risk factors** including liquidations, borrow patterns, repayment behavior
- **Generates risk scores 0-1000** (lower = safer)
- **Outputs results** in CSV format with visualization

## 🔧 Core Features

### Transaction Analysis
- **Mint Events**: Deposit patterns and amounts
- **Borrow Events**: Borrowing behavior and frequency  
- **Repay Events**: Repayment consistency and rates
- **Redeem Events**: Withdrawal patterns
- **Liquidation Events**: Default incidents

### Risk Factors
- Liquidation history (-300 points max)
- Borrow-to-deposit ratio (high ratio = higher risk)
- Repayment rate (low rate = higher risk)
- Activity frequency (extreme values penalized)
- Health factor (current supply vs borrow)
- Token diversification (bonus for multiple tokens)

### Technical Capabilities
- **Parallel Processing**: 5 concurrent API requests
- **Retry Logic**: Exponential backoff for failed requests
- **Simulation Fallback**: Deterministic fake data when API unavailable
- **Input Validation**: Ethereum address verification
- **Comprehensive Logging**: File and console output

## 📁 Output Files

- `wallet_scores.csv` - Primary deliverable with risk scores
- `wallet_features.csv` - Detailed feature analysis
- `score_distribution.png` - Score distribution histogram
- `scoring.log` - Processing logs and errors

## 🛠️ Architecture

```
CompoundWalletScorer
├── Data Fetching (TheGraph API + Simulation)
├── Feature Engineering (17+ metrics)
├── Risk Scoring (0-1000 scale)
├── Parallel Processing (ThreadPoolExecutor)
└── Results Export (CSV + Visualization)
```

## 📋 Requirements

- Python 3.8+
- pandas, requests, scikit-learn
- web3, retrying, matplotlib
- 103 wallet addresses in `wallets.csv`

## ✅ Verification

All 16 project requirements met. See `verification.md` for detailed compliance report.

## 🧪 Testing

```bash
# Run unit tests
python tests.py

# Run with GitHub Actions
# Tests automatically run on push/PR to main branch
```

## 📖 Documentation

- `README.md` - This quick start guide
- `explanation.md` - Detailed technical methodology
- `verification.md` - Requirements compliance report

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

MIT License - see `LICENSE` file for details.

---

**Built for DeFi risk assessment and portfolio management.**
