#!/usr/bin/env python3

import pandas as pd
import requests
import json
import time
import sys
import os
import argparse
import logging
import hashlib
import random
import unittest
from datetime import datetime, timedelta
from sklearn.preprocessing import MinMaxScaler
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wallet_scoring.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class CompoundWalletScorer:
    
    def __init__(self, use_simulation=False, max_workers=5):
        self.api_url = "https://api.thegraph.com/subgraphs/name/graphprotocol/compound-v2"
        self.headers = {"Content-Type": "application/json"}
        self.use_simulation = use_simulation
        self.max_workers = max_workers
        self.features_df = None
        self.scores_df = None
        
        logger.info(f"Initialized DeFi Wallet Risk Scorer - Mode: {'Simulation' if use_simulation else 'Real API'}")

    def validate_wallet_address(self, wallet_address):
        if not isinstance(wallet_address, str) or len(wallet_address) != 42 or not wallet_address.startswith('0x'):
            return False
        try:
            int(wallet_address[2:], 16)
            return True
        except:
            return False

    def _fetch_from_thegraph(self, wallet_address, retries=3):
        for attempt in range(retries):
            try:
                query = """
                query($wallet: String!) {
                  account(id: $wallet) {
                    tokens { 
                      symbol 
                      supplyBalanceUnderlying 
                      borrowBalanceUnderlying 
                    }
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
                  redeemEvents: redeemEvents(where: {from: $wallet}, first: 1000) {
                    blockTime underlyingAmount cTokenSymbol
                  }
                  liquidationEvents: liquidationEvents(where: {borrower: $wallet}, first: 1000) {
                    blockTime repayAmount seizeTokens
                  }
                }
                """
                
                response = requests.post(
                    self.api_url, 
                    json={"query": query, "variables": {"wallet": wallet_address}}, 
                    headers=self.headers, 
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                if "errors" in data:
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return None
                    
                return data.get("data")
                
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                
        return None

    def _simulate_wallet_data(self, wallet_address):
        seed = int(hashlib.md5(wallet_address.encode()).hexdigest()[:8], 16)
        random.seed(seed)

        current_time = int(datetime.now().timestamp())
        base_time = current_time - random.randint(86400 * 30, 86400 * 365)

        wallet_type = seed % 5
        tokens = ['cUSDC', 'cDAI', 'cUSDT', 'cWBTC', 'cETH']

        if wallet_type == 0:  # Conservative
            mint_events = [
                {
                    'blockTime': str(base_time + i * 86400 * random.randint(7, 30)), 
                    'underlyingAmount': str(random.uniform(1000, 10000)), 
                    'cTokenSymbol': random.choice(tokens[:3])
                } for i in range(random.randint(3, 8))
            ]
            borrow_events = [
                {
                    'blockTime': str(base_time + i * 86400 * random.randint(30, 60)), 
                    'underlyingAmount': str(random.uniform(500, 3000)), 
                    'cTokenSymbol': random.choice(tokens[:2])
                } for i in range(random.randint(1, 4))
            ]
            repay_events = [
                {
                    'blockTime': str(int(event['blockTime']) + 86400 * 30), 
                    'underlyingAmount': str(float(event['underlyingAmount']) * 1.1), 
                    'cTokenSymbol': event['cTokenSymbol']
                } for event in borrow_events
            ]
            redeem_events = [
                {
                    'blockTime': str(int(event['blockTime']) + 86400 * 60), 
                    'underlyingAmount': str(float(event['underlyingAmount']) * 0.5), 
                    'cTokenSymbol': event['cTokenSymbol']
                } for event in mint_events[:2]
            ]
            liquidation_events = []

        elif wallet_type == 1:  # Risky
            mint_events = [
                {
                    'blockTime': str(base_time + i * 86400), 
                    'underlyingAmount': str(random.uniform(500, 2000)), 
                    'cTokenSymbol': random.choice(tokens)
                } for i in range(2)
            ]
            borrow_events = [
                {
                    'blockTime': str(base_time + i * 86400 * 7), 
                    'underlyingAmount': str(random.uniform(3000, 8000)), 
                    'cTokenSymbol': random.choice(tokens[:3])
                } for i in range(random.randint(3, 6))
            ]
            repay_events = [
                {
                    'blockTime': str(int(event['blockTime']) + 86400 * 10), 
                    'underlyingAmount': str(float(event['underlyingAmount']) * 0.4), 
                    'cTokenSymbol': event['cTokenSymbol']
                } for event in borrow_events[:len(borrow_events)//2]
            ]
            redeem_events = []
            liquidation_events = [
                {
                    'blockTime': str(base_time + 86400 * 60), 
                    'repayAmount': str(random.uniform(2000, 5000)), 
                    'seizeTokens': str(random.uniform(1000, 3000))
                }
            ]

        elif wallet_type == 2:  # High frequency
            mint_events = [
                {
                    'blockTime': str(base_time + i * 3600), 
                    'underlyingAmount': str(random.uniform(100, 500)), 
                    'cTokenSymbol': random.choice(tokens)
                } for i in range(50)
            ]
            borrow_events = [
                {
                    'blockTime': str(base_time + i * 3600), 
                    'underlyingAmount': str(random.uniform(100, 500)), 
                    'cTokenSymbol': random.choice(tokens)
                } for i in range(80)
            ]
            repay_events = [
                {
                    'blockTime': str(int(event['blockTime']) + 3600), 
                    'underlyingAmount': event['underlyingAmount'], 
                    'cTokenSymbol': event['cTokenSymbol']
                } for event in borrow_events
            ]
            redeem_events = [
                {
                    'blockTime': str(int(event['blockTime']) + 3600 * 2), 
                    'underlyingAmount': str(float(event['underlyingAmount']) * 0.8), 
                    'cTokenSymbol': event['cTokenSymbol']
                } for event in mint_events[:20]
            ]
            liquidation_events = []

        elif wallet_type == 3:  # Defaulted
            mint_events = [
                {
                    'blockTime': str(base_time), 
                    'underlyingAmount': str(2000), 
                    'cTokenSymbol': 'cUSDC'
                }
            ]
            borrow_events = [
                {
                    'blockTime': str(base_time + 86400 * 7), 
                    'underlyingAmount': str(5000), 
                    'cTokenSymbol': 'cUSDC'
                }
            ]
            repay_events = []
            redeem_events = []
            liquidation_events = [
                {
                    'blockTime': str(base_time + 86400 * 30), 
                    'repayAmount': str(5000), 
                    'seizeTokens': str(2000)
                }
            ]

        else:  # Diversified
            mint_events = [
                {
                    'blockTime': str(base_time + i * 86400 * 10), 
                    'underlyingAmount': str(random.uniform(1000, 3000)), 
                    'cTokenSymbol': random.choice(tokens)
                } for i in range(5)
            ]
            borrow_events = [
                {
                    'blockTime': str(base_time + i * 86400 * 20), 
                    'underlyingAmount': str(random.uniform(800, 2000)), 
                    'cTokenSymbol': random.choice(tokens[:3])
                } for i in range(3)
            ]
            repay_events = [
                {
                    'blockTime': str(int(event['blockTime']) + 86400 * 15), 
                    'underlyingAmount': str(float(event['underlyingAmount']) * 0.9), 
                    'cTokenSymbol': event['cTokenSymbol']
                } for event in borrow_events
            ]
            redeem_events = [
                {
                    'blockTime': str(int(event['blockTime']) + 86400 * 45), 
                    'underlyingAmount': str(float(event['underlyingAmount']) * 0.3), 
                    'cTokenSymbol': event['cTokenSymbol']
                } for event in mint_events[:2]
            ]
            liquidation_events = []

        unique_tokens = set([event['cTokenSymbol'] for event in mint_events + borrow_events])
        account_tokens = []
        for token in unique_tokens:
            account_tokens.append({
                'symbol': token,
                'supplyBalanceUnderlying': str(random.uniform(0, 10000)),
                'borrowBalanceUnderlying': str(random.uniform(0, 5000))
            })

        return {
            'account': {
                'tokens': account_tokens,
                'countLiquidated': len(liquidation_events),
                'hasBorrowed': len(borrow_events) > 0
            },
            'mintEvents': mint_events,
            'borrowEvents': borrow_events,
            'repayEvents': repay_events,
            'redeemEvents': redeem_events,
            'liquidationEvents': liquidation_events
        }

    def fetch_wallet_data(self, wallet_address):
        wallet_address = wallet_address.lower()
        
        if not self.validate_wallet_address(wallet_address):
            logger.error(f"Invalid wallet address: {wallet_address}")
            return None

        if not self.use_simulation:
            try:
                data = self._fetch_from_thegraph(wallet_address)
                if data:
                    return data
            except Exception as e:
                logger.warning(f"Falling back to simulation for {wallet_address}: {e}")

        return self._simulate_wallet_data(wallet_address)

    def process_wallet_features(self, data, wallet_address):
        if not data:
            return self._get_default_features(wallet_address)

        try:
            account = data.get('account', {})
            tokens = account.get('tokens', []) if account else []
            
            total_supply = sum(float(token.get('supplyBalanceUnderlying', 0)) for token in tokens)
            total_borrow = sum(float(token.get('borrowBalanceUnderlying', 0)) for token in tokens)
            
            mint_events = data.get('mintEvents', [])
            borrow_events = data.get('borrowEvents', [])
            repay_events = data.get('repayEvents', [])
            redeem_events = data.get('redeemEvents', [])
            liquidation_events = data.get('liquidationEvents', [])

            total_deposits = sum(float(event.get('underlyingAmount', 0)) for event in mint_events)
            total_borrows = sum(float(event.get('underlyingAmount', 0)) for event in borrow_events)
            total_repays = sum(float(event.get('underlyingAmount', 0)) for event in repay_events)
            total_redeems = sum(float(event.get('underlyingAmount', 0)) for event in redeem_events)

            deposit_count = len(mint_events)
            borrow_count = len(borrow_events)
            repay_count = len(repay_events)
            redeem_count = len(redeem_events)
            liquidation_count = len(liquidation_events)

            borrow_to_deposit_ratio = min(total_borrows / max(total_deposits, 1), 10)
            repay_rate = total_repays / max(total_borrows, 1)
            health_factor = total_supply / max(total_borrow, 1) if total_borrow > 0 else 100

            unique_tokens_used = len(set(
                [event.get('cTokenSymbol', '') for event in 
                 mint_events + borrow_events + repay_events + redeem_events]
            ))

            all_events = mint_events + borrow_events + repay_events + redeem_events + liquidation_events
            if all_events:
                timestamps = [int(event.get('blockTime', 0)) for event in all_events if event.get('blockTime')]
                if timestamps:
                    activity_duration = (max(timestamps) - min(timestamps)) / 86400
                    activity_frequency = len(timestamps) / max(activity_duration, 1)
                else:
                    activity_duration = 0
                    activity_frequency = 0
            else:
                activity_duration = 0
                activity_frequency = 0

            return {
                'wallet_id': wallet_address,
                'total_deposits': total_deposits,
                'total_borrows': total_borrows,
                'total_repays': total_repays,
                'total_redeems': total_redeems,
                'current_supply': total_supply,
                'current_borrow': total_borrow,
                'deposit_count': deposit_count,
                'borrow_count': borrow_count,
                'repay_count': repay_count,
                'redeem_count': redeem_count,
                'liquidation_count': liquidation_count,
                'borrow_to_deposit_ratio': borrow_to_deposit_ratio,
                'repay_rate': repay_rate,
                'health_factor': health_factor,
                'unique_tokens_used': unique_tokens_used,
                'activity_duration_days': activity_duration,
                'activity_frequency': activity_frequency
            }

        except Exception as e:
            logger.error(f"Error processing features for {wallet_address}: {e}")
            return self._get_default_features(wallet_address)

    def _get_default_features(self, wallet_address="unknown"):
        return {
            'wallet_id': wallet_address,
            'total_deposits': 0, 'total_borrows': 0, 'total_repays': 0, 'total_redeems': 0,
            'current_supply': 0, 'current_borrow': 0,
            'deposit_count': 0, 'borrow_count': 0, 'repay_count': 0, 'redeem_count': 0,
            'liquidation_count': 0, 'borrow_to_deposit_ratio': 0, 'repay_rate': 0,
            'health_factor': 100, 'unique_tokens_used': 0,
            'activity_duration_days': 0, 'activity_frequency': 0
        }

    def calculate_risk_score(self, features):
        try:
            score = 1000
            
            liquidation_penalty = min(features['liquidation_count'] * 50, 300)
            score -= liquidation_penalty
            
            if features['borrow_to_deposit_ratio'] > 5:
                score -= 200
            elif features['borrow_to_deposit_ratio'] > 2:
                score -= 100
            elif features['borrow_to_deposit_ratio'] > 1:
                score -= 50
                
            if features['repay_rate'] < 0.3:
                score -= 150
            elif features['repay_rate'] < 0.7:
                score -= 75
            elif features['repay_rate'] > 1.2:
                score += 25
                
            if features['activity_frequency'] > 50:
                score -= 100
            elif features['activity_frequency'] < 0.01:
                score -= 50
                
            if features['health_factor'] < 1.1:
                score -= 200
            elif features['health_factor'] < 1.5:
                score -= 100
            elif features['health_factor'] > 10:
                score += 25
                
            if features['unique_tokens_used'] > 3:
                score += 50
            elif features['unique_tokens_used'] > 1:
                score += 25
                
            if features['total_borrows'] > 0 and features['total_deposits'] == 0:
                score -= 100
                
            return max(min(score, 1000), 0)
            
        except Exception as e:
            logger.error(f"Error calculating score for {features.get('wallet_id', 'unknown')}: {e}")
            return 500

    def process_wallets(self, wallets_file='wallets.csv'):
        if not os.path.exists(wallets_file):
            raise FileNotFoundError(f"Wallets file not found: {wallets_file}")
            
        try:
            wallets_df = pd.read_csv(wallets_file)
        except Exception as e:
            raise ValueError(f"Error reading wallets file: {e}")
            
        if 'wallet_id' not in wallets_df.columns:
            raise ValueError("Wallets file must contain 'wallet_id' column")

        wallet_addresses = wallets_df['wallet_id'].tolist()
        logger.info(f"Processing {len(wallet_addresses)} wallets...")

        features_list = []
        for i, wallet in enumerate(wallet_addresses, 1):
            try:
                data = self.fetch_wallet_data(wallet)
                features = self.process_wallet_features(data, wallet)
                if features:
                    features_list.append(features)
                    
                if i % 10 == 0:
                    logger.info(f"Completed {i}/{len(wallet_addresses)} wallets")
                    
            except Exception as e:
                logger.error(f"Error processing wallet {wallet}: {e}")
                features_list.append(self._get_default_features(wallet))

        self.features_df = pd.DataFrame(features_list)
        
        scores_list = []
        for _, features in self.features_df.iterrows():
            score = self.calculate_risk_score(features.to_dict())
            scores_list.append({
                'wallet_id': features['wallet_id'],
                'score': score
            })
        
        self.scores_df = pd.DataFrame(scores_list)
        self.scores_df = self.scores_df.sort_values('wallet_id').reset_index(drop=True)
        
        logger.info(f"Successfully processed {len(self.scores_df)} wallets")
        return self.scores_df

    def save_results(self, features_file='wallet_features.csv', scores_file='wallet_scores.csv'):
        if self.features_df is not None:
            self.features_df.to_csv(features_file, index=False)
            logger.info(f"Features saved to {features_file}")

        if self.scores_df is not None:
            self.scores_df.to_csv(scores_file, index=False)
            logger.info(f"Scores saved to {scores_file}")

    def get_summary(self):
        if self.scores_df is None:
            return "No results available"
            
        stats = {
            'total_wallets': len(self.scores_df),
            'mean_score': self.scores_df['score'].mean(),
            'median_score': self.scores_df['score'].median(),
            'min_score': self.scores_df['score'].min(),
            'max_score': self.scores_df['score'].max(),
            'std_score': self.scores_df['score'].std()
        }
        
        return stats

class TestCompoundWalletScorer(unittest.TestCase):
    
    def setUp(self):
        self.scorer = CompoundWalletScorer(use_simulation=True)
        self.sample_wallet = "0x1234567890123456789012345678901234567890"
        
    def test_wallet_address_validation(self):
        self.assertTrue(self.scorer.validate_wallet_address("0x1234567890123456789012345678901234567890"))
        self.assertTrue(self.scorer.validate_wallet_address("0xabcdefABCDEF1234567890123456789012345678"))
        self.assertFalse(self.scorer.validate_wallet_address("invalid"))
        self.assertFalse(self.scorer.validate_wallet_address("0x123"))

    def test_simulation_data_generation(self):
        data1 = self.scorer._simulate_wallet_data(self.sample_wallet)
        data2 = self.scorer._simulate_wallet_data(self.sample_wallet)
        self.assertEqual(len(data1['mintEvents']), len(data2['mintEvents']))
        self.assertEqual(data1['account']['countLiquidated'], data2['account']['countLiquidated'])

    def test_feature_extraction(self):
        data = self.scorer._simulate_wallet_data(self.sample_wallet)
        features = self.scorer.process_wallet_features(data, self.sample_wallet)
        
        required_features = [
            'wallet_id', 'total_deposits', 'total_borrows', 'liquidation_count',
            'borrow_to_deposit_ratio', 'repay_rate', 'health_factor'
        ]
        
        for feature in required_features:
            self.assertIn(feature, features)
            
        self.assertEqual(features['wallet_id'], self.sample_wallet)
        self.assertGreaterEqual(features['total_deposits'], 0)
        self.assertLessEqual(features['borrow_to_deposit_ratio'], 10)

    def test_risk_score_calculation(self):
        safe_features = {
            'wallet_id': self.sample_wallet,
            'liquidation_count': 0,
            'borrow_to_deposit_ratio': 0.5,
            'repay_rate': 0.95,
            'activity_frequency': 2.0,
            'health_factor': 5.0,
            'unique_tokens_used': 3,
            'total_borrows': 1000,
            'total_deposits': 2000
        }
        
        risky_features = {
            'wallet_id': self.sample_wallet,
            'liquidation_count': 2,
            'borrow_to_deposit_ratio': 8.0,
            'repay_rate': 0.1,
            'activity_frequency': 100.0,
            'health_factor': 0.5,
            'unique_tokens_used': 1,
            'total_borrows': 8000,
            'total_deposits': 1000
        }
        
        safe_score = self.scorer.calculate_risk_score(safe_features)
        risky_score = self.scorer.calculate_risk_score(risky_features)
        
        self.assertGreater(safe_score, risky_score)
        self.assertGreaterEqual(safe_score, 0)
        self.assertLessEqual(safe_score, 1000)

def run_tests():
    print("Running DeFi Wallet Risk Scoring System Tests")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestCompoundWalletScorer)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("All tests passed!")
        return True
    else:
        print("Some tests failed!")
        return False

def main():
    parser = argparse.ArgumentParser(description='DeFi Wallet Risk Scoring System for Compound V2 Protocol')
    
    parser.add_argument('--simulation', action='store_true', help='Use simulation mode')
    parser.add_argument('--wallets-file', default='wallets.csv', help='Input CSV file with wallet addresses')
    parser.add_argument('--workers', type=int, default=5, help='Number of concurrent workers')
    parser.add_argument('--quiet', action='store_true', help='Suppress info-level logging')
    parser.add_argument('--test', action='store_true', help='Run unit tests and exit')
    
    args = parser.parse_args()
    
    if args.test:
        success = run_tests()
        sys.exit(0 if success else 1)
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    print("DeFi Wallet Risk Scoring System for Compound V2")
    print("=" * 60)
    print(f"Mode: {'Simulation' if args.simulation else 'Real API with simulation fallback'}")
    print(f"Input: {args.wallets_file}")
    print(f"Workers: {args.workers}")
    print()
    
    try:
        scorer = CompoundWalletScorer(use_simulation=args.simulation, max_workers=args.workers)
        
        start_time = time.time()
        scores_df = scorer.process_wallets(args.wallets_file)
        processing_time = time.time() - start_time
        
        scorer.save_results()
        stats = scorer.get_summary()
        
        print(f"\nProcessing Summary:")
        print(f"   Total wallets processed: {stats['total_wallets']}")
        print(f"   Processing time: {processing_time:.1f} seconds")
        print(f"   Average score: {stats['mean_score']:.1f}")
        print(f"   Score range: {stats['min_score']:.0f} - {stats['max_score']:.0f}")
        
        print(f"\nOutput files:")
        print(f"   wallet_scores.csv - Risk scores for all wallets")
        print(f"   wallet_features.csv - Detailed features for analysis")
        print(f"   wallet_scoring.log - Processing logs")
        
        high_risk = len(scores_df[scores_df['score'] < 400])
        medium_risk = len(scores_df[(scores_df['score'] >= 400) & (scores_df['score'] < 700)])
        low_risk = len(scores_df[scores_df['score'] >= 700])
        
        print(f"\nRisk Distribution:")
        print(f"   High Risk (0-400): {high_risk} wallets")
        print(f"   Medium Risk (400-700): {medium_risk} wallets")
        print(f"   Low Risk (700-1000): {low_risk} wallets")
        
        print(f"\nProcessing completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        print(f"\nProcessing interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        print(f"\nError: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
