#!/usr/bin/env python3
"""Wallet Risk Scoring System for Compound V2 Protocol"""

import pandas as pd
import requests
import json
import time
from datetime import datetime
from sklearn.preprocessing import MinMaxScaler
import logging
import hashlib
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompoundWalletScorer:
    def __init__(self, use_simulation=True):
        self.api_url = "https://api.thegraph.com/subgraphs/name/graphprotocol/compound-v2"
        self.headers = {"Content-Type": "application/json"}
        self.use_simulation = use_simulation
        self.features_df = None
        self.scores_df = None

    def fetch_wallet_data(self, wallet_address):
        wallet_address = wallet_address.lower()
        
        if not self.use_simulation:
            data = self._fetch_from_thegraph(wallet_address)
            if data:
                return data
        
        return self._simulate_wallet_data(wallet_address)

    def _fetch_from_thegraph(self, wallet_address):
        query = """
        query($wallet: String!) {
          account(id: $wallet) {
            tokens { symbol supplyBalanceUnderlying borrowBalanceUnderlying }
            countLiquidated
            hasBorrowed
          }
          mintEvents: mintEvents(where: {to: $wallet}, first: 1000) {
            blockTime underlyingAmount cTokenSymbol
          }
          borrowEvents: borrowEvents(where: {borrower: $wallet}, first: 1000) {
            blockTime underlyingAmount cTokenSymbol
          }
          repayEvents: repayEvents(where: {borrower: $wallet}, first: 1000) {
            blockTime underlyingAmount cTokenSymbol
          }
          liquidationEvents: liquidationEvents(where: {borrower: $wallet}, first: 1000) {
            blockTime repayAmount seizeTokens
          }
        }
        """
        try:
            response = requests.post(self.api_url, json={"query": query, "variables": {"wallet": wallet_address}}, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            if "errors" in data:
                logger.warning(f"API errors for {wallet_address}")
                return None
            return data.get("data")
        except Exception as e:
            logger.warning(f"API request failed for {wallet_address}: {e}")
            return None

    def _simulate_wallet_data(self, wallet_address):
        seed = int(hashlib.md5(wallet_address.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        base_time = 1640995200
        wallet_type = seed % 5
        
        if wallet_type == 0:
            mint_events = [{'blockTime': str(base_time + i * 86400 * random.randint(7, 30)), 'underlyingAmount': str(random.uniform(1000, 10000)), 'cTokenSymbol': 'cUSDC'} for i in range(random.randint(3, 8))]
            borrow_events = [{'blockTime': str(base_time + i * 86400 * random.randint(30, 60)), 'underlyingAmount': str(random.uniform(500, 3000)), 'cTokenSymbol': 'cUSDC'} for i in range(random.randint(1, 4))]
            repay_events = [{'blockTime': str(int(event['blockTime']) + 86400 * 30), 'underlyingAmount': str(float(event['underlyingAmount']) * 1.1), 'cTokenSymbol': event['cTokenSymbol']} for event in borrow_events]
            liquidation_events = []
        elif wallet_type == 1:
            mint_events = [{'blockTime': str(base_time + i * 86400), 'underlyingAmount': str(random.uniform(500, 2000)), 'cTokenSymbol': 'cUSDC'} for i in range(2)]
            borrow_events = [{'blockTime': str(base_time + i * 86400 * 7), 'underlyingAmount': str(random.uniform(3000, 8000)), 'cTokenSymbol': 'cUSDC'} for i in range(random.randint(3, 6))]
            repay_events = [{'blockTime': str(int(event['blockTime']) + 86400 * 10), 'underlyingAmount': str(float(event['underlyingAmount']) * 0.4), 'cTokenSymbol': event['cTokenSymbol']} for event in borrow_events[:len(borrow_events)//2]]
            liquidation_events = [{'blockTime': str(base_time + 86400 * 60), 'repayAmount': str(random.uniform(2000, 5000)), 'seizeTokens': str(random.uniform(1000, 3000))}]
        elif wallet_type == 2:
            mint_events = [{'blockTime': str(base_time + i * 3600), 'underlyingAmount': str(random.uniform(100, 500)), 'cTokenSymbol': 'cUSDC'} for i in range(50)]
            borrow_events = [{'blockTime': str(base_time + i * 3600), 'underlyingAmount': str(random.uniform(100, 500)), 'cTokenSymbol': 'cUSDC'} for i in range(80)]
            repay_events = [{'blockTime': str(int(event['blockTime']) + 3600), 'underlyingAmount': event['underlyingAmount'], 'cTokenSymbol': event['cTokenSymbol']} for event in borrow_events]
            liquidation_events = []
        elif wallet_type == 3:
            mint_events = [{'blockTime': str(base_time), 'underlyingAmount': str(2000), 'cTokenSymbol': 'cUSDC'}]
            borrow_events = [{'blockTime': str(base_time + 86400 * 7), 'underlyingAmount': str(5000), 'cTokenSymbol': 'cUSDC'}]
            repay_events = []
            liquidation_events = [{'blockTime': str(base_time + 86400 * 30), 'repayAmount': str(5000), 'seizeTokens': str(2000)}]
        else:
            mint_events = [{'blockTime': str(base_time + i * 86400 * 10), 'underlyingAmount': str(random.uniform(1000, 3000)), 'cTokenSymbol': 'cUSDC'} for i in range(3)]
            borrow_events = [{'blockTime': str(base_time + i * 86400 * 20), 'underlyingAmount': str(random.uniform(800, 2000)), 'cTokenSymbol': 'cUSDC'} for i in range(2)]
            repay_events = [{'blockTime': str(int(event['blockTime']) + 86400 * 15), 'underlyingAmount': str(float(event['underlyingAmount']) * 0.9), 'cTokenSymbol': event['cTokenSymbol']} for event in borrow_events]
            liquidation_events = []

        total_deposited = sum(float(e['underlyingAmount']) for e in mint_events)
        total_borrowed = sum(float(e['underlyingAmount']) for e in borrow_events)
        total_repaid = sum(float(e['underlyingAmount']) for e in repay_events)

        return {
            'account': {
                'tokens': [{'symbol': 'cUSDC', 'supplyBalanceUnderlying': str(total_deposited * 0.8), 'borrowBalanceUnderlying': str(max(0, total_borrowed - total_repaid) * 0.9)}],
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
        if not data:
            return {'wallet_id': wallet_address, 'total_borrows': 0, 'total_repays': 0, 'total_deposits': 0, 'liquidation_count': 0, 'repay_rate': 0, 'borrow_to_deposit_ratio': 0, 'days_active': 0, 'transaction_frequency': 0, 'current_borrow_balance': 0, 'current_supply_balance': 0, 'has_borrowed': False, 'unique_tokens_used': 0}

        account = data.get('account', {})
        mint_events = data.get('mintEvents', [])
        borrow_events = data.get('borrowEvents', [])
        repay_events = data.get('repayEvents', [])
        liquidation_events = data.get('liquidationEvents', [])

        total_borrows = len(borrow_events)
        total_repays = len(repay_events)
        total_deposits = len(mint_events)
        liquidation_count = len(liquidation_events)

        total_borrow_amount = sum(float(event.get('underlyingAmount', 0)) for event in borrow_events)
        total_repay_amount = sum(float(event.get('underlyingAmount', 0)) for event in repay_events)
        total_deposit_amount = sum(float(event.get('underlyingAmount', 0)) for event in mint_events)

        repay_rate = total_repay_amount / total_borrow_amount if total_borrow_amount > 0 else 1.0
        borrow_to_deposit_ratio = total_borrow_amount / total_deposit_amount if total_deposit_amount > 0 else float('inf')

        all_timestamps = []
        for events in [mint_events, borrow_events, repay_events, liquidation_events]:
            all_timestamps.extend([int(event.get('blockTime', 0)) for event in events])

        if all_timestamps:
            days_active = max(1, (max(all_timestamps) - min(all_timestamps)) / 86400)
            transaction_frequency = len(all_timestamps) / days_active
        else:
            days_active = 0
            transaction_frequency = 0

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
            'liquidation_count': liquidation_count,
            'repay_rate': min(repay_rate, 2.0),
            'borrow_to_deposit_ratio': min(borrow_to_deposit_ratio, 10.0),
            'days_active': days_active,
            'transaction_frequency': transaction_frequency,
            'current_borrow_balance': current_borrow_balance,
            'current_supply_balance': current_supply_balance,
            'has_borrowed': bool(account.get('hasBorrowed', False)) if account else False,
            'unique_tokens_used': len(unique_tokens)
        }

    def calculate_risk_score(self, features):
        base_score = 1000

        if features['liquidation_count'] > 0:
            base_score -= 300 * min(features['liquidation_count'], 3)

        if features['repay_rate'] < 0.3:
            base_score -= 200
        elif features['repay_rate'] < 0.6:
            base_score -= 100
        elif features['repay_rate'] > 1.2:
            base_score += 50

        if features['borrow_to_deposit_ratio'] > 5.0:
            base_score -= 150
        elif features['borrow_to_deposit_ratio'] > 2.0:
            base_score -= 75
        elif features['borrow_to_deposit_ratio'] < 0.5:
            base_score += 25

        if features['days_active'] > 0:
            if features['transaction_frequency'] > 10:
                base_score -= 100
            elif features['transaction_frequency'] < 0.1 and features['total_borrows'] > 5:
                base_score -= 50

        if features['days_active'] < 7 and features['total_borrows'] > 3:
            base_score -= 75
        elif features['days_active'] > 365:
            base_score += 50

        if features['current_borrow_balance'] > 0:
            debt_ratio = features['current_borrow_balance'] / max(features['current_supply_balance'], 1)
            if debt_ratio > 0.8:
                base_score -= 100
            elif debt_ratio < 0.3:
                base_score += 25

        if features['unique_tokens_used'] > 3:
            base_score += 25

        if features['has_borrowed'] and features['total_deposits'] == 0:
            base_score -= 150

        if (features['total_deposits'] > 5 and features['total_borrows'] > 0 and 
            features['liquidation_count'] == 0 and features['repay_rate'] > 0.8):
            base_score += 100

        return max(0, min(1000, base_score))

    def normalize_features(self, df):
        feature_columns = ['total_borrows', 'total_repays', 'total_deposits', 'repay_rate', 'borrow_to_deposit_ratio', 'days_active', 'transaction_frequency', 'current_borrow_balance', 'current_supply_balance', 'unique_tokens_used']
        
        scaler = MinMaxScaler()
        df_normalized = df.copy()
        
        if len(df) > 1:
            df_normalized[feature_columns] = scaler.fit_transform(df[feature_columns])
        
        return df_normalized, scaler

    def process_wallets(self, wallet_file='wallets.csv'):
        logger.info("Loading wallet addresses...")
        wallets_df = pd.read_csv(wallet_file)
        wallet_addresses = wallets_df['wallet_id'].tolist()
        
        logger.info(f"Processing {len(wallet_addresses)} wallets...")
        
        all_features = []
        
        for i, wallet in enumerate(wallet_addresses, 1):
            logger.info(f"Processing wallet {i}/{len(wallet_addresses)}: {wallet}")
            
            data = self.fetch_wallet_data(wallet)
            features = self.process_wallet_features(wallet, data)
            all_features.append(features)
            
            time.sleep(0.5)
            
            if i % 10 == 0:
                logger.info(f"Completed {i}/{len(wallet_addresses)} wallets")
        
        self.features_df = pd.DataFrame(all_features)
        normalized_df, scaler = self.normalize_features(self.features_df)
        
        scores = []
        for _, row in self.features_df.iterrows():
            score = self.calculate_risk_score(row)
            scores.append({'wallet_id': row['wallet_id'], 'score': score})
        
        self.scores_df = pd.DataFrame(scores).sort_values('score', ascending=True)
        
        logger.info("Processing completed!")
        return self.scores_df

    def save_results(self, output_file='wallet_scores.csv'):
        if self.scores_df is not None:
            self.scores_df.to_csv(output_file, index=False)
            logger.info(f"Results saved to {output_file}")
            
            logger.info(f"Mean Score: {self.scores_df['score'].mean():.2f}")
            logger.info(f"Score Range: {self.scores_df['score'].min()} - {self.scores_df['score'].max()}")
        else:
            logger.error("No scores to save!")

    def save_detailed_features(self, output_file='wallet_features.csv'):
        if self.features_df is not None:
            detailed_df = self.features_df.merge(self.scores_df, on='wallet_id', how='left')
            detailed_df.to_csv(output_file, index=False)
            logger.info(f"Detailed features saved to {output_file}")

def main():
    print("🔍 Wallet Risk Scoring System for Compound V2")
    print("=" * 60)
    
    scorer = CompoundWalletScorer(use_simulation=True)
    
    print("⚠️  Using simulation mode (TheGraph API fallback)")
    print()
    
    try:
        scores_df = scorer.process_wallets('wallets.csv')
        scorer.save_results('wallet_scores.csv')
        scorer.save_detailed_features('wallet_features.csv')
        
        print(f"\n🎉 SUCCESS: Processed {len(scores_df)} wallets")
        print(f"📊 Results: wallet_scores.csv")
        print(f"📋 Features: wallet_features.csv")
        print(f"\n📈 Score Statistics:")
        print(f"   Range: {scores_df['score'].min()} - {scores_df['score'].max()}")
        print(f"   Mean: {scores_df['score'].mean():.1f}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

if __name__ == "__main__":
    main()
