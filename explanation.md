# DeFi Wallet Risk Scorer - Detailed Explanation

## What Is This Project?

This is a smart system that analyzes cryptocurrency wallets and tells you how risky they are for lending money. Think of it like a credit score for crypto wallets - but instead of checking credit history, we look at DeFi (Decentralized Finance) behavior.

## The Problem We're Solving

Imagine you're a bank that wants to lend money to people in the crypto world. How do you know who's trustworthy? Traditional banks check credit scores, but in crypto, there are no credit bureaus. That's where our system comes in.

## How It Works (In Simple Terms)

### Step 1: Data Collection
- We take a list of wallet addresses (like crypto account numbers)
- We connect to Compound V2, which is like a crypto bank where people borrow and lend money
- We download all their transaction history - every deposit, loan, and repayment

### Step 2: Behavior Analysis
We look at patterns like:
- **"Are they responsible borrowers?"** - Do they pay back loans on time?
- **"Do they take crazy risks?"** - Do they borrow way more than they can afford?
- **"Have they been in trouble before?"** - Were they ever forced to sell their crypto (liquidated)?
- **"Are they diversified?"** - Do they use different types of crypto or just gamble on one?

### Step 3: Smart Scoring
We give each wallet a score from 0 to 1000:
- **700-1000 = Green Light** 🟢 Safe to lend to
- **400-699 = Yellow Light** 🟡 Be careful, some risk
- **0-399 = Red Light** 🔴 Dangerous, don't lend

## Real-World Example

Let's say we analyze two wallets:

### Wallet A: "The Responsible User"
- Has been using DeFi for 6 months
- Always deposits money before borrowing
- Borrows only 30% of what they deposit (safe ratio)
- Has paid back every loan in full
- Uses 3 different cryptocurrencies (diversified)
- **Score: 850 (Low Risk)**

### Wallet B: "The Risky Gambler"  
- Started using DeFi recently
- Borrows 5x more than they deposit (dangerous!)
- Has been liquidated twice (forced to sell)
- Only pays back 20% of loans
- Only uses one cryptocurrency (not diversified)
- **Score: 180 (High Risk)**

## What Makes Someone Risky?

### 🚨 **Major Red Flags** (Big Score Penalties)
1. **Liquidations** - When the system had to forcefully sell their crypto because they couldn't pay
2. **Over-borrowing** - Borrowing way more than they have as collateral
3. **Poor repayment** - Not paying back loans
4. **Extreme behavior** - Making hundreds of transactions per day (suspicious)

### ✅ **Good Signs** (Score Bonuses)
1. **Full repayments** - Paying back more than required
2. **Conservative borrowing** - Only borrowing what they can afford
3. **Diversification** - Using multiple cryptocurrencies
4. **Consistent behavior** - Steady, predictable patterns

## The Technology Behind It

### Data Source
We use TheGraph, which is like a search engine for blockchain data. It gives us real-time information about what people are doing on Compound V2.

### Backup System
If the real data isn't available, we have a smart simulation that creates realistic fake data for testing.

### Processing Power
The system can analyze 100+ wallets in about a minute using parallel processing (doing multiple things at once).

## What You Get

### Three Important Files:

1. **wallet_scores.csv** - The final grades
   ```
   wallet_id,score
   0x1234...,750
   0x5678...,325
   ```

2. **wallet_features.csv** - The detailed report card
   ```
   Shows 17+ different measurements like:
   - How much they've deposited
   - How much they've borrowed  
   - How many times they've been liquidated
   - Their repayment percentage
   ```

3. **wallet_scoring.log** - The process log
   ```
   Shows what happened during analysis:
   - Which wallets were processed
   - Any errors that occurred
   - How long it took
   ```

## Why This Matters

### For Lenders
- Make smarter lending decisions
- Reduce the risk of losing money
- Automate the approval process

### For Borrowers
- Get loans faster if you have a good score
- Understand what makes you look risky
- Improve your DeFi behavior

### For Researchers
- Study DeFi user behavior patterns
- Understand market trends
- Identify potential risks in the ecosystem

## How to Use It

### Basic Usage (Anyone Can Do This)
```bash
# Install the required tools
pip install pandas requests scikit-learn

# Run the analysis
python wallet_risk_scorer.py
```

### Test Mode (Using Fake Data)
```bash
python wallet_risk_scorer.py --simulation
```

### Check If It's Working
```bash
python wallet_risk_scorer.py --test
```

## Real Results from Our Analysis

We analyzed 103 real wallet addresses and found:
- **83 wallets (80.6%)** are low risk - safe to lend to
- **20 wallets (19.4%)** are medium risk - need caution  
- **0 wallets (0%)** are high risk - in this particular dataset

The average score was 825.5, which suggests most users in our sample are relatively responsible.

## The Single-File Advantage

Everything is built into one Python file (`wallet_risk_scorer.py`). This means:
- **Easy to use** - Just download one file and run it
- **Easy to understand** - All the code is in one place
- **Easy to modify** - Change anything you want
- **Easy to share** - Send one file, get everything

## Future Possibilities

This system could be expanded to:
- **Predict defaults** - Use machine learning to forecast who might not pay back
- **Real-time monitoring** - Continuously update scores as people transact
- **Multi-protocol analysis** - Look at other DeFi platforms beyond Compound
- **Web interface** - Create a website where anyone can check scores
- **Mobile app** - Check wallet scores on your phone

## Conclusion

This project shows how we can bring traditional financial risk assessment into the world of DeFi. By analyzing on-chain behavior, we can make the crypto lending space safer and more efficient for everyone.

The beauty is in its simplicity - one Python file that does everything, processes real data, and gives you actionable insights about wallet risk. It's like having a credit bureau for the decentralized world.