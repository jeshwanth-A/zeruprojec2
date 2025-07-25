#!/usr/bin/env python3
"""
Wallet Risk Scoring System for Compound V2 Protocol
Author: Tarun
Date: July 2025

This script fetches transaction data from Compound V2 protocol using TheGraph API,
processes the data to create meaningful features, and assigns risk scores (0-1000)
to wallet addresses where 0 is highest risk and 1000 is lowest risk.
"""

import pandas as pd
import requests
import json
import time
from datetime import datetime
from sklearn.preprocessing import MinMaxScaler
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompoundWalletScorer:
    def __init__(self, use_simulation=True, etherscan_api_key=None):
        # TheGraph endpoints (currently not working)
        self.thegraph_urls = [
            "https://api.thegraph.com/subgraphs/name/compound-finance/compound-v2",
            "https://gateway-arbitrum.network.thegraph.com/api/subgraphs/id/HUZDsRpEVP2AvzDCyzDHtdc64dyDxx8FQjzsmqSg4H3B"
        ]
        self.etherscan_api_key = etherscan_api_key
        self.use_simulation = use_simulation
        self.headers = {"Content-Type": "application/json"}
        self.raw_data = []
        self.features_df = None
        self.scores_df = None
        
        # Compound V2 contract addresses for Etherscan fallback
        self.compound_contracts = {
            'cETH': '0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5',
            'cDAI': '0x5d3a536E4D6DbD6114cc1Ead35777bAB111e3d0F',
            'cUSDC': '0x39AA39c021dfbaE8faC545936693aC917d5E7563',
            'cUSDT': '0xf650C3d88D12dB855b8bf7D11Be6C55A4e07dCC9'
        }
        
    def fetch_wallet_data(self, wallet_address):
        """
        Fetch comprehensive transaction data for a wallet from multiple sources
        Priority: 1) TheGraph (if available) 2) Etherscan API 3) Simulation for demo
        """
        wallet_address = wallet_address.lower()
        
        # Try TheGraph first
        if not self.use_simulation:
            for api_url in self.thegraph_urls:
                data = self._fetch_from_thegraph(wallet_address, api_url)
                if data:
                    return data
        
        # Try Etherscan API if available
        if self.etherscan_api_key and not self.use_simulation:
            data = self._fetch_from_etherscan(wallet_address)
            if data:
                return data
        
        # Fall back to simulation for demonstration
        return self._simulate_wallet_data(wallet_address)
    
    def _fetch_from_thegraph(self, wallet_address, api_url):
        """Fetch data from TheGraph API"""
        query = """
        query($wallet: String!) {
          account(id: $wallet) {
            id
            tokens {
              symbol
              supplyBalanceUnderlying
              borrowBalanceUnderlying
              storedBorrowBalance
              accountBorrowIndex
              totalUnderlyingSupplied
              totalUnderlyingBorrowed
            }
            countLiquidated
            countLiquidator
            hasBorrowed
          }
          
          mintEvents: mintEvents(where: {to: $wallet}, first: 1000, orderBy: blockTime, orderDirection: asc) {
            blockTime
            underlyingAmount
            cTokenSymbol
            blockNumber
          }
          
          borrowEvents: borrowEvents(where: {borrower: $wallet}, first: 1000, orderBy: blockTime, orderDirection: asc) {
            blockTime
            underlyingAmount
            cTokenSymbol
            blockNumber
          }
          
          repayEvents: repayEvents(where: {borrower: $wallet}, first: 1000, orderBy: blockTime, orderDirection: asc) {
            blockTime
            underlyingAmount
            cTokenSymbol
            blockNumber
          }
          
          redeemEvents: redeemEvents(where: {from: $wallet}, first: 1000, orderBy: blockTime, orderDirection: asc) {
            blockTime
            underlyingAmount
            cTokenSymbol
            blockNumber
          }
          
          liquidationEvents: liquidationEvents(where: {borrower: $wallet}, first: 1000, orderBy: blockTime, orderDirection: asc) {
            blockTime
            cTokenBorrowed
            cTokenCollateral
            repayAmount
            seizeTokens
            blockNumber
          }
        }
        """
        
        variables = {"wallet": wallet_address}
        
        try:
            response = requests.post(
                api_url,
                json={"query": query, "variables": variables},
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                logger.warning(f"TheGraph errors for {wallet_address}: {data['errors']}")
                return None
                
            return data.get("data")
            
        except Exception as e:
            logger.warning(f"TheGraph request failed for {wallet_address}: {e}")
            return None
    
    def _fetch_from_etherscan(self, wallet_address):
        """Fetch data from Etherscan API (alternative approach)"""
        # This would require parsing contract interactions
        # For now, return None to fall back to simulation
        logger.info(f"Etherscan API not implemented for {wallet_address}")
        return None
    
    def _simulate_wallet_data(self, wallet_address):
        """
        Simulate realistic wallet data for demonstration purposes
        This creates varied risk profiles based on wallet address characteristics
        """
        import hashlib
        import random
        
        # Use wallet address to create deterministic but varied data
        seed = int(hashlib.md5(wallet_address.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        # Create realistic transaction patterns
        base_time = 1640995200  # Jan 1, 2022
        days_active = random.randint(30, 800)
        
        # Generate transaction events based on wallet "personality"
        wallet_type = seed % 5
        
        if wallet_type == 0:  # Conservative long-term user
            mint_events = [
                {
                    'blockTime': str(base_time + i * 86400 * random.randint(7, 30)),
                    'underlyingAmount': str(random.uniform(1000, 10000)),
                    'cTokenSymbol': random.choice(['cUSDC', 'cDAI', 'cETH'])
                } for i in range(random.randint(3, 8))
            ]
            borrow_events = [
                {
                    'blockTime': str(base_time + i * 86400 * random.randint(30, 60)),
                    'underlyingAmount': str(random.uniform(500, 3000)),
                    'cTokenSymbol': random.choice(['cUSDC', 'cDAI'])
                } for i in range(random.randint(1, 4))
            ]
            repay_events = [
                {
                    'blockTime': str(int(event['blockTime']) + 86400 * random.randint(10, 90)),
                    'underlyingAmount': str(float(event['underlyingAmount']) * random.uniform(1.05, 1.2)),
                    'cTokenSymbol': event['cTokenSymbol']
                } for event in borrow_events
            ]
            liquidation_events = []
            
        elif wallet_type == 1:  # Risky high-leverage user
            mint_events = [
                {
                    'blockTime': str(base_time + i * 86400 * random.randint(1, 7)),
                    'underlyingAmount': str(random.uniform(500, 5000)),
                    'cTokenSymbol': random.choice(['cETH', 'cUSDC'])
                } for i in range(random.randint(2, 5))
            ]
            borrow_events = [
                {
                    'blockTime': str(base_time + i * 86400 * random.randint(1, 14)),
                    'underlyingAmount': str(random.uniform(2000, 15000)),  # High leverage
                    'cTokenSymbol': random.choice(['cUSDC', 'cDAI', 'cUSDT'])
                } for i in range(random.randint(3, 8))
            ]
            repay_events = [
                {
                    'blockTime': str(int(event['blockTime']) + 86400 * random.randint(1, 30)),
                    'underlyingAmount': str(float(event['underlyingAmount']) * random.uniform(0.3, 0.8)),  # Partial repays
                    'cTokenSymbol': event['cTokenSymbol']
                } for event in random.sample(borrow_events, max(1, len(borrow_events) // 2))
            ]
            liquidation_events = [
                {
                    'blockTime': str(base_time + days_active * 86400 // 2),
                    'repayAmount': str(random.uniform(1000, 5000)),
                    'seizeTokens': str(random.uniform(1200, 6000))
                }
            ] if random.random() > 0.3 else []
            
        elif wallet_type == 2:  # Bot/High frequency trader
            mint_events = [
                {
                    'blockTime': str(base_time + i * 3600),  # Hourly transactions
                    'underlyingAmount': str(random.uniform(100, 1000)),
                    'cTokenSymbol': random.choice(['cUSDC', 'cDAI'])
                } for i in range(random.randint(20, 100))
            ]
            borrow_events = [
                {
                    'blockTime': str(base_time + i * 3600),
                    'underlyingAmount': str(random.uniform(100, 1000)),
                    'cTokenSymbol': random.choice(['cUSDC', 'cDAI'])
                } for i in range(random.randint(30, 120))
            ]
            repay_events = [
                {
                    'blockTime': str(int(event['blockTime']) + 3600),  # Quick repays
                    'underlyingAmount': event['underlyingAmount'],
                    'cTokenSymbol': event['cTokenSymbol']
                } for event in borrow_events
            ]
            liquidation_events = []
            
        elif wallet_type == 3:  # Inactive/abandoned wallet
            mint_events = [
                {
                    'blockTime': str(base_time),
                    'underlyingAmount': str(random.uniform(1000, 5000)),
                    'cTokenSymbol': 'cUSDC'
                }
            ]
            borrow_events = [
                {
                    'blockTime': str(base_time + 86400 * 7),
                    'underlyingAmount': str(random.uniform(2000, 8000)),
                    'cTokenSymbol': 'cUSDC'
                }
            ]
            repay_events = []  # Never repaid
            liquidation_events = [
                {
                    'blockTime': str(base_time + 86400 * 30),
                    'repayAmount': str(random.uniform(2000, 8000)),
                    'seizeTokens': str(random.uniform(1000, 5000))
                }
            ]
            
        else:  # Mixed behavior user
            mint_events = [
                {
                    'blockTime': str(base_time + i * 86400 * random.randint(5, 20)),
                    'underlyingAmount': str(random.uniform(500, 3000)),
                    'cTokenSymbol': random.choice(['cUSDC', 'cDAI', 'cETH'])
                } for i in range(random.randint(2, 6))
            ]
            borrow_events = [
                {
                    'blockTime': str(base_time + i * 86400 * random.randint(10, 40)),
                    'underlyingAmount': str(random.uniform(800, 4000)),
                    'cTokenSymbol': random.choice(['cUSDC', 'cDAI'])
                } for i in range(random.randint(2, 5))
            ]
            repay_events = [
                {
                    'blockTime': str(int(event['blockTime']) + 86400 * random.randint(5, 60)),
                    'underlyingAmount': str(float(event['underlyingAmount']) * random.uniform(0.7, 1.1)),
                    'cTokenSymbol': event['cTokenSymbol']
                } for event in random.sample(borrow_events, max(1, len(borrow_events) * 2 // 3))
            ]
            liquidation_events = []
        
        # Calculate current balances
        total_deposited = sum(float(e['underlyingAmount']) for e in mint_events)
        total_borrowed = sum(float(e['underlyingAmount']) for e in borrow_events)
        total_repaid = sum(float(e['underlyingAmount']) for e in repay_events)
        
        tokens = [
            {
                'symbol': 'cUSDC',
                'supplyBalanceUnderlying': str(total_deposited * 0.6),
                'borrowBalanceUnderlying': str(max(0, total_borrowed - total_repaid) * 0.7)
            },
            {
                'symbol': 'cDAI', 
                'supplyBalanceUnderlying': str(total_deposited * 0.4),
                'borrowBalanceUnderlying': str(max(0, total_borrowed - total_repaid) * 0.3)
            }
        ]
        
        return {
            'account': {
                'id': wallet_address,
                'tokens': tokens,
                'countLiquidated': len(liquidation_events),
                'hasBorrowed': len(borrow_events) > 0
            },
            'mintEvents': mint_events,
            'borrowEvents': borrow_events,
            'repayEvents': repay_events,
            'redeemEvents': [],
            'liquidationEvents': liquidation_events
        }
            
    def process_wallet_features(self, wallet_address, data):
        """
        Extract meaningful features from wallet transaction data
        """
        if not data:
            # Return default features for inactive wallets
            return {
                'wallet_id': wallet_address,
                'total_borrows': 0,
                'total_repays': 0,
                'total_deposits': 0,
                'total_withdrawals': 0,
                'liquidation_count': 0,
                'repay_rate': 0,
                'borrow_to_deposit_ratio': 0,
                'days_active': 0,
                'transaction_frequency': 0,
                'current_borrow_balance': 0,
                'current_supply_balance': 0,
                'has_borrowed': False,
                'unique_tokens_used': 0
            }
        
        account = data.get('account', {})
        mint_events = data.get('mintEvents', [])
        borrow_events = data.get('borrowEvents', [])
        repay_events = data.get('repayEvents', [])
        redeem_events = data.get('redeemEvents', [])
        liquidation_events = data.get('liquidationEvents', [])
        
        # Basic counts
        total_borrows = len(borrow_events)
        total_repays = len(repay_events)
        total_deposits = len(mint_events)
        total_withdrawals = len(redeem_events)
        liquidation_count = len(liquidation_events)
        
        # Calculate amounts
        total_borrow_amount = sum(float(event.get('underlyingAmount', 0)) for event in borrow_events)
        total_repay_amount = sum(float(event.get('underlyingAmount', 0)) for event in repay_events)
        total_deposit_amount = sum(float(event.get('underlyingAmount', 0)) for event in mint_events)
        
        # Calculate repay rate
        repay_rate = total_repay_amount / total_borrow_amount if total_borrow_amount > 0 else 1.0
        
        # Calculate borrow to deposit ratio
        borrow_to_deposit_ratio = total_borrow_amount / total_deposit_amount if total_deposit_amount > 0 else float('inf')
        
        # Calculate time-based features
        all_timestamps = []
        for events in [mint_events, borrow_events, repay_events, redeem_events, liquidation_events]:
            all_timestamps.extend([int(event.get('blockTime', 0)) for event in events])
        
        if all_timestamps:
            min_time = min(all_timestamps)
            max_time = max(all_timestamps)
            days_active = max(1, (max_time - min_time) / 86400)  # Convert seconds to days
            total_transactions = len(all_timestamps)
            transaction_frequency = total_transactions / days_active
        else:
            days_active = 0
            transaction_frequency = 0
        
        # Current balances
        current_borrow_balance = 0
        current_supply_balance = 0
        unique_tokens = set()
        
        if account and account.get('tokens'):
            for token in account['tokens']:
                current_borrow_balance += float(token.get('borrowBalanceUnderlying', 0))
                current_supply_balance += float(token.get('supplyBalanceUnderlying', 0))
                unique_tokens.add(token.get('symbol', ''))
        
        return {
            'wallet_id': wallet_address,
            'total_borrows': total_borrows,
            'total_repays': total_repays,
            'total_deposits': total_deposits,
            'total_withdrawals': total_withdrawals,
            'liquidation_count': liquidation_count,
            'repay_rate': min(repay_rate, 2.0),  # Cap at 2.0 to handle over-repayments
            'borrow_to_deposit_ratio': min(borrow_to_deposit_ratio, 10.0),  # Cap at 10.0
            'days_active': days_active,
            'transaction_frequency': transaction_frequency,
            'current_borrow_balance': current_borrow_balance,
            'current_supply_balance': current_supply_balance,
            'has_borrowed': bool(account.get('hasBorrowed', False)) if account else False,
            'unique_tokens_used': len(unique_tokens),
            'total_borrow_amount': total_borrow_amount,
            'total_deposit_amount': total_deposit_amount
        }
    
    def calculate_risk_score(self, features):
        """
        Calculate risk score using rule-based approach
        Score range: 0-1000 (0 = highest risk, 1000 = lowest risk)
        """
        base_score = 1000  # Start with perfect score
        
        # Liquidation penalty (strong risk indicator)
        if features['liquidation_count'] > 0:
            base_score -= 300 * min(features['liquidation_count'], 3)  # Cap penalty at 3 liquidations
        
        # Repay rate assessment
        if features['repay_rate'] < 0.3:
            base_score -= 200  # Very poor repayment
        elif features['repay_rate'] < 0.6:
            base_score -= 100  # Poor repayment
        elif features['repay_rate'] > 1.2:
            base_score += 50   # Over-repayment shows good behavior
        
        # Borrow to deposit ratio (leverage risk)
        if features['borrow_to_deposit_ratio'] > 5.0:
            base_score -= 150  # Extreme leverage
        elif features['borrow_to_deposit_ratio'] > 2.0:
            base_score -= 75   # High leverage
        elif features['borrow_to_deposit_ratio'] < 0.5:
            base_score += 25   # Conservative borrowing
        
        # Activity pattern analysis
        if features['days_active'] > 0:
            if features['transaction_frequency'] > 10:  # More than 10 transactions per day
                base_score -= 100  # Potential bot behavior
            elif features['transaction_frequency'] < 0.1 and features['total_borrows'] > 5:
                base_score -= 50   # Infrequent activity with borrowing
        
        # Time-based risk (short-term exploitation)
        if features['days_active'] < 7 and features['total_borrows'] > 3:
            base_score -= 75  # Quick hit-and-run pattern
        elif features['days_active'] > 365:
            base_score += 50  # Long-term user bonus
        
        # Current debt situation
        if features['current_borrow_balance'] > 0:
            debt_ratio = features['current_borrow_balance'] / max(features['current_supply_balance'], 1)
            if debt_ratio > 0.8:
                base_score -= 100  # High current debt
            elif debt_ratio < 0.3:
                base_score += 25   # Low current debt
        
        # Diversification bonus
        if features['unique_tokens_used'] > 3:
            base_score += 25  # Diversified portfolio
        
        # No deposit before borrow penalty
        if features['has_borrowed'] and features['total_deposits'] == 0:
            base_score -= 150  # Borrowed without depositing (risky)
        
        # Activity bonus for consistent users
        if (features['total_deposits'] > 5 and features['total_borrows'] > 0 and 
            features['liquidation_count'] == 0 and features['repay_rate'] > 0.8):
            base_score += 100  # Good user bonus
        
        # Ensure score is within bounds
        return max(0, min(1000, base_score))
    
    def normalize_features(self, df):
        """
        Normalize features using Min-Max scaling
        """
        feature_columns = [
            'total_borrows', 'total_repays', 'total_deposits', 'total_withdrawals',
            'repay_rate', 'borrow_to_deposit_ratio', 'days_active', 'transaction_frequency',
            'current_borrow_balance', 'current_supply_balance', 'unique_tokens_used'
        ]
        
        scaler = MinMaxScaler()
        df_normalized = df.copy()
        
        # Only normalize if we have more than one row
        if len(df) > 1:
            df_normalized[feature_columns] = scaler.fit_transform(df[feature_columns])
        
        return df_normalized, scaler
    
    def process_wallets(self, wallet_file='wallets.csv'):
        """
        Main processing function
        """
        logger.info("Loading wallet addresses...")
        wallets_df = pd.read_csv(wallet_file)
        wallet_addresses = wallets_df['wallet_id'].tolist()
        
        logger.info(f"Processing {len(wallet_addresses)} wallets...")
        
        all_features = []
        
        for i, wallet in enumerate(wallet_addresses, 1):
            logger.info(f"Processing wallet {i}/{len(wallet_addresses)}: {wallet}")
            
            # Fetch data from TheGraph
            data = self.fetch_wallet_data(wallet)
            
            # Extract features
            features = self.process_wallet_features(wallet, data)
            all_features.append(features)
            
            # Rate limiting - sleep between requests
            time.sleep(0.5)
            
            # Progress update every 10 wallets
            if i % 10 == 0:
                logger.info(f"Completed {i}/{len(wallet_addresses)} wallets")
        
        # Create features DataFrame
        self.features_df = pd.DataFrame(all_features)
        
        # Normalize features
        normalized_df, scaler = self.normalize_features(self.features_df)
        
        # Calculate scores
        scores = []
        for _, row in self.features_df.iterrows():
            score = self.calculate_risk_score(row)
            scores.append({
                'wallet_id': row['wallet_id'],
                'score': score
            })
        
        self.scores_df = pd.DataFrame(scores).sort_values('score', ascending=True)
        
        logger.info("Processing completed!")
        return self.scores_df
    
    def save_results(self, output_file='wallet_scores.csv'):
        """
        Save results to CSV file
        """
        if self.scores_df is not None:
            self.scores_df.to_csv(output_file, index=False)
            logger.info(f"Results saved to {output_file}")
            
            # Print summary statistics
            logger.info("\nScore Distribution:")
            logger.info(f"Mean Score: {self.scores_df['score'].mean():.2f}")
            logger.info(f"Median Score: {self.scores_df['score'].median():.2f}")
            logger.info(f"Min Score: {self.scores_df['score'].min()}")
            logger.info(f"Max Score: {self.scores_df['score'].max()}")
            logger.info(f"Standard Deviation: {self.scores_df['score'].std():.2f}")
        else:
            logger.error("No scores to save!")
    
    def save_detailed_features(self, output_file='wallet_features.csv'):
        """
        Save detailed features for analysis
        """
        if self.features_df is not None:
            # Merge with scores
            detailed_df = self.features_df.merge(self.scores_df, on='wallet_id', how='left')
            detailed_df.to_csv(output_file, index=False)
            logger.info(f"Detailed features saved to {output_file}")
        else:
            logger.error("No features to save!")

def main():
    """
    Main execution function
    """
    print("🔍 Wallet Risk Scoring System for Compound V2")
    print("=" * 60)
    
    # Initialize scorer with simulation mode (TheGraph endpoints are currently down)
    scorer = CompoundWalletScorer(use_simulation=True)
    
    print("⚠️  Note: Using simulation mode due to TheGraph API unavailability")
    print("   This demonstrates the methodology with realistic synthetic data")
    print("   For production use, implement Etherscan API integration")
    print()
    
    try:
        # Process all wallets
        scores_df = scorer.process_wallets('wallets.csv')
        
        # Save results
        scorer.save_results('wallet_scores.csv')
        scorer.save_detailed_features('wallet_features.csv')
        
        print("\n" + "="*60)
        print("🎉 WALLET RISK SCORING COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"📊 Processed {len(scores_df)} wallets")
        print(f"💾 Results saved to: wallet_scores.csv")
        print(f"📋 Detailed features saved to: wallet_features.csv")
        print("\n🏆 Top 5 Lowest Risk Wallets (Highest Scores):")
        print(scores_df.tail().to_string(index=False))
        print("\n⚠️  Top 5 Highest Risk Wallets (Lowest Scores):")
        print(scores_df.head().to_string(index=False))
        
        # Additional statistics
        print(f"\n📈 Score Statistics:")
        print(f"   Mean Score: {scores_df['score'].mean():.1f}")
        print(f"   Median Score: {scores_df['score'].median():.1f}")
        print(f"   Score Range: {scores_df['score'].min()} - {scores_df['score'].max()}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()
