# Wallet Risk Scoring System - Compound V2 Protocol

A comprehensive Python-based system for analyzing wallet transaction history on Compound V2 protocol and assigning risk scores from 0-1000, where **0 represents highest risk** and **1000 represents lowest risk (safest)**.

## 🎯 Problem Statement

This system addresses Round 2 Assignment: "Wallet Risk Scoring From Scratch" by:
- Fetching transaction history from Compound V2 protocol for 100+ wallet addresses
- Engineering meaningful features that reflect wallet risk profiles
- Developing a transparent, rule-based scoring model
- Outputting actionable risk scores with detailed explanations

## 🏗️ Architecture & Approach

### Data Collection Method: TheGraph API
- **Source**: [Compound V2 Subgraph](https://api.thegraph.com/subgraphs/name/graphprotocol/compound-v2)
- **Why TheGraph**: 
  - ✅ Free and reliable API access
  - ✅ Structured GraphQL queries for efficient data retrieval
  - ✅ Pre-indexed blockchain data (faster than raw blockchain scans)
  - ✅ User-specific transaction filtering
  - ✅ Avoids rate limits and API key requirements of services like Etherscan

### Feature Engineering Strategy

Our risk assessment focuses on **7 key behavioral indicators**:

| Feature | Risk Indication | Reasoning |
|---------|----------------|-----------|
| **Liquidation Count** | Direct default risk | Any liquidation proves inability to maintain collateral ratios |
| **Repay Rate** (repays/borrows) | Debt management ability | Low rates indicate unpaid debts (similar to credit defaults) |
| **Borrow-to-Deposit Ratio** | Leverage risk | High leverage increases vulnerability to market volatility |
| **Days Active** | Usage pattern | Very short activity periods suggest exploitative behavior |
| **Transaction Frequency** | Bot detection | Extremely high frequency indicates automated exploitation |
| **Current Debt Status** | Immediate risk | Outstanding borrows without adequate collateral |
| **Deposit Behavior** | Capital backing | Borrowing without depositing relies on volatile external collateral |

### Normalization Method: Min-Max Scaling
- **Range**: 0-1 for all features
- **Why Min-Max**: Simple, bounds features uniformly, handles varying scales without assuming normal distributions
- **Implementation**: sklearn.preprocessing.MinMaxScaler

### Scoring Logic: Rule-Based System
**Base Score**: 1000 (perfect score)  
**Deduction Rules**:
- **-300 points**: Per liquidation event (capped at 3 liquidations)
- **-200 points**: Repay rate < 30%
- **-150 points**: Borrow-to-deposit ratio > 5.0 (extreme leverage)
- **-100 points**: High transaction frequency (>10/day, bot-like)
- **-100 points**: High current debt ratio (>80%)
- **-75 points**: Very short activity period with multiple borrows
- **-150 points**: Borrowing without any deposits

**Bonus Points**:
- **+100 points**: Consistent good behavior (deposits, repays, no liquidations)
- **+50 points**: Over-repayment behavior (repay rate > 120%)
- **+50 points**: Long-term user (>365 days active)
- **+25 points**: Conservative borrowing or diversified portfolio

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Internet connection for TheGraph API access

### Installation
```bash
# Clone or download the repository
git clone <your-repo-url>
cd wallet-risk-scoring

# Install dependencies
pip install -r requirements.txt

# Ensure wallets.csv exists with your wallet addresses
# (Download from Google Sheets and save as CSV with 'wallet_id' column)
```

### Usage
```bash
# Run the complete scoring pipeline
python score_wallets.py

# This will generate:
# - wallet_scores.csv (final scores)
# - wallet_features.csv (detailed features for analysis)
```

## 📊 Output Format

### wallet_scores.csv
```csv
wallet_id,score
0xfaa0768bde629806739c3a4620656c5d26f44ef2,732
0x0039f22efb07a647557c7c5d17854cfd6d489ef3,856
...
```

### wallet_features.csv (Detailed Analysis)
Contains all engineered features plus scores for deeper analysis:
- `total_borrows`, `total_repays`, `total_deposits`
- `liquidation_count`, `repay_rate`, `borrow_to_deposit_ratio`
- `days_active`, `transaction_frequency`
- `current_borrow_balance`, `current_supply_balance`
- Plus normalized versions and final `score`

## 🔍 Risk Indicators Justification

### 1. Liquidation Events (Strongest Indicator)
- **DeFi Context**: Liquidations occur when collateral falls below required ratios
- **Risk Correlation**: Proven inability to manage positions during market volatility
- **Real-world Parallel**: Similar to foreclosures in traditional finance

### 2. Repay Rate Analysis
- **Calculation**: Total repaid amount / Total borrowed amount
- **Risk Logic**: Low rates indicate defaults or abandoned positions
- **Threshold**: <50% considered high risk, >80% considered good behavior

### 3. Leverage Assessment
- **Metric**: Borrowed amount / Deposited amount
- **Risk Factor**: Over-leveraged positions fail quickly in volatile markets
- **DeFi Reality**: Many protocol exploits involve high leverage strategies

### 4. Behavioral Pattern Detection
- **Short-term Activity**: Users active <7 days with multiple borrows often exploit and exit
- **High Frequency**: >10 transactions/day suggests automated strategies (higher failure rates)
- **No-deposit Borrowing**: Relying solely on external collateral increases liquidation risk

## 🎛️ Configuration & Customization

### Adjusting Score Thresholds
Edit the `calculate_risk_score()` method in `score_wallets.py`:

```python
# Example: Increase liquidation penalty
if features['liquidation_count'] > 0:
    base_score -= 400 * min(features['liquidation_count'], 3)  # Increased from 300

# Example: Adjust repay rate thresholds
if features['repay_rate'] < 0.2:  # More strict threshold
    base_score -= 250  # Higher penalty
```

### Adding New Features
1. Modify `process_wallet_features()` to extract new metrics
2. Update `normalize_features()` to include new columns
3. Add scoring logic in `calculate_risk_score()`

## 📈 Scalability Considerations

### Current Capacity
- **API Limits**: 0.5s delay between requests prevents rate limiting
- **Memory**: Processes 100+ wallets efficiently in memory
- **Time**: ~1-2 minutes per 100 wallets

### Scaling to 10,000+ Wallets
- **Batch Processing**: Implement chunked processing with progress saving
- **Database Storage**: Replace CSV with PostgreSQL/MongoDB for large datasets
- **Parallel Processing**: Use asyncio for concurrent API requests
- **Caching**: Implement Redis for repeated wallet lookups

### Production Considerations
- **Error Handling**: Robust retry logic for API failures
- **Monitoring**: Add metrics for API response times and success rates
- **Data Validation**: Implement schema validation for API responses

## 🔬 Model Validation & Testing

### Test Wallet Analysis
The system includes several test cases with known risk profiles:

1. **High-Risk Wallet**: Multiple liquidations, poor repay rates
2. **Low-Risk Wallet**: Consistent deposits, good repayment history
3. **Inactive Wallet**: No transactions (neutral score: 500)

### Score Distribution Analysis
Run the system to see:
- Mean and median scores
- Standard deviation
- Risk distribution across the portfolio

## 📋 Project Structure

```
wallet-risk-scoring/
├── score_wallets.py       # Main scoring engine
├── wallets.csv           # Input wallet addresses
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── explanation.md       # Detailed methodology
├── wallet_scores.csv    # Output scores (generated)
└── wallet_features.csv  # Detailed features (generated)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-risk-indicator`)
3. Commit changes (`git commit -am 'Add new risk indicator'`)
4. Push to branch (`git push origin feature/new-risk-indicator`)
5. Create Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

**API Timeout Errors**:
```bash
# Increase timeout in score_wallets.py
response = requests.post(..., timeout=60)  # Increase from 30
```

**Memory Issues with Large Datasets**:
```python
# Process in chunks
for chunk in pd.read_csv('wallets.csv', chunksize=100):
    # Process each chunk separately
```

**Missing Dependencies**:
```bash
pip install --upgrade -r requirements.txt
```

## 📞 Support

For questions or issues:
1. Check the troubleshooting section above
2. Review the explanation.md for detailed methodology
3. Create an issue in the repository
4. Contact: [Your contact information]

---

**Built with ❤️ for DeFi Risk Analysis**
