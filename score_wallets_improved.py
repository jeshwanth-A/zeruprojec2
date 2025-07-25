#!/usr/bin/env python3
"""DeFi Wallet Risk Scoring System for Compound V2 Protocol"""

import pandas as pd
import requests
import json
import time
import argparse
from datetime import datetime, timedelta
from sklearn.preprocessing import MinMaxScaler
import logging
import hashlib
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import sys
from web3 import Web3
from retrying import retry
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-GUI backend
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scoring.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

if not HAS_MATPLOTLIB:
    logger.warning("Matplotlib not available - visualization will be skipped")

class CompoundWalletScorer:
    def __init__(self, use_simulation=False, max_workers=5):
        """Initialize the wallet scorer.
        
        Args:
            use_simulation: If True, use simulation data. Default False for real API data.
            max_workers: Number of concurrent threads for API requests.
        """
        self.api_url = "https://api.thegraph.com/subgraphs/name/graphprotocol/compound-v2"
        self.headers = {"Content-Type": "application/json"}
        self.use_simulation = use_simulation
        self.max_workers = max_workers
        self.features_df = None
        self.scores_df = None
        self.scaler = MinMaxScaler()

    def validate_wallet_address(self, wallet_address):
        """Validate if wallet address is a valid Ethereum address."""
        try:
            return Web3.is_address(wallet_address)
        except:
            # Fallback validation if Web3 is not available
            return len(wallet_address) == 42 and wallet_address.startswith('0x')

    @retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
    def _fetch_from_thegraph(self, wallet_address):
        """Fetch wallet data from TheGraph API with retry logic."""
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
        try:
            response = requests.post(
                self.api_url, 
                json={"query": query, "variables": {"wallet": wallet_address}}, 
                headers=self.headers, 
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                logger.error(f"API errors for {wallet_address}: {data['errors']}")
                raise Exception(f"GraphQL errors: {data['errors']}")
                
            return data.get("data")
            
        except Exception as e:
            logger.warning(f"API request failed for {wallet_address}: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Full response: {e.response.text}")
            raise

    def _simulate_wallet_data(self, wallet_address):
        """Generate realistic simulation data for wallet."""
        seed = int(hashlib.md5(wallet_address.encode()).hexdigest()[:8], 16)
        random.seed(seed)

        # Use current time with random offsets instead of hardcoded dates
        current_time = int(datetime.now().timestamp())
        base_time = current_time - random.randint(86400 * 30, 86400 * 365)  # 30 days to 1 year ago

        wallet_type = seed % 5
        tokens = ['cUSDC', 'cDAI', 'cUSDT', 'cWBTC', 'cETH']

        if wallet_type == 0:  # Conservative user
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

        elif wallet_type == 1:  # Risky borrower
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

        elif wallet_type == 2:  # High frequency trader
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

        elif wallet_type == 3:  # Defaulted user
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

        else:  # Diversified user
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

        return {
            'account': {
                'tokens': [
                    {
                        'symbol': token, 
                        'supplyBalanceUnderlying': str(random.uniform(0, 10000)), 
                        'borrowBalanceUnderlying': str(random.uniform(0, 5000))
                    } for token in set([event['cTokenSymbol'] for event in mint_events + borrow_events])
                ],
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
        """Fetch wallet data with API priority and simulation fallback."""
        wallet_address = wallet_address.lower()
        
        if not self.validate_wallet_address(wallet_address):
            logger.error(f"Invalid wallet address: {wallet_address}")
            return None

        if not self.use_simulation:
            try:
                data = self._fetch_from_thegraph(wallet_address)
                if data:
                    logger.info(f"✓ Real data fetched for {wallet_address}")
                    return data
            except Exception as e:
                logger.warning(f"Falling back to simulation for {wallet_address}: {e}")

        logger.info(f"📊 Using simulation for {wallet_address}")
        return self._simulate_wallet_data(wallet_address)

    def process_wallet_features(self, wallet_data, wallet_address):
        """Extract and process features from wallet data."""
        if not wallet_data:
            return self._get_default_features()

        try:
            # Extract basic account info
            account = wallet_data.get('account', {})
            tokens = account.get('tokens', []) if account else []
            
            # Calculate current balances
            total_supply = sum(float(token.get('supplyBalanceUnderlying', 0)) for token in tokens)
            total_borrow = sum(float(token.get('borrowBalanceUnderlying', 0)) for token in tokens)
            
            # Process transaction events
            mint_events = wallet_data.get('mintEvents', [])
            borrow_events = wallet_data.get('borrowEvents', [])
            repay_events = wallet_data.get('repayEvents', [])
            redeem_events = wallet_data.get('redeemEvents', [])
            liquidation_events = wallet_data.get('liquidationEvents', [])

            # Calculate transaction volumes
            total_deposits = sum(float(event.get('underlyingAmount', 0)) for event in mint_events)
            total_borrows = sum(float(event.get('underlyingAmount', 0)) for event in borrow_events)
            total_repays = sum(float(event.get('underlyingAmount', 0)) for event in repay_events)
            total_redeems = sum(float(event.get('underlyingAmount', 0)) for event in redeem_events)

            # Calculate transaction frequencies
            deposit_count = len(mint_events)
            borrow_count = len(borrow_events)
            repay_count = len(repay_events)
            redeem_count = len(redeem_events)
            liquidation_count = len(liquidation_events)

            # Calculate ratios with safer division
            borrow_to_deposit_ratio = min(total_borrows / max(total_deposits, 1), 10)  # Cap at 10
            repay_rate = total_repays / max(total_borrows, 1)
            
            # Health factor approximation
            health_factor = total_supply / max(total_borrow, 1) if total_borrow > 0 else float('inf')
            health_factor = min(health_factor, 100)  # Cap at 100 for practical purposes

            # Token diversity
            unique_tokens_used = len(set(
                [event.get('cTokenSymbol', '') for event in mint_events + borrow_events + repay_events + redeem_events]
            ))

            # Time-based features
            all_events = mint_events + borrow_events + repay_events + redeem_events + liquidation_events
            if all_events:
                timestamps = [int(event.get('blockTime', 0)) for event in all_events if event.get('blockTime')]
                if timestamps:
                    activity_duration = (max(timestamps) - min(timestamps)) / 86400  # days
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
        """Return default features for failed processing."""
        return {
            'wallet_id': wallet_address,
            'total_deposits': 0, 'total_borrows': 0, 'total_repays': 0, 'total_redeems': 0,
            'current_supply': 0, 'current_borrow': 0,
            'deposit_count': 0, 'borrow_count': 0, 'repay_count': 0, 'redeem_count': 0,
            'liquidation_count': 0, 'borrow_to_deposit_ratio': 0, 'repay_rate': 0,
            'health_factor': float('inf'), 'unique_tokens_used': 0,
            'activity_duration_days': 0, 'activity_frequency': 0
        }

    def calculate_risk_score(self, features):
        """Calculate risk score using normalized features."""
        try:
            # Start with base score
            score = 1000
            
            # Get normalized values (assuming features_df is available with all wallets)
            normalized_features = self._get_normalized_features(features)
            
            # Proportional deductions based on risk factors
            score -= min(normalized_features['liquidation_count'] * 50, 300)  # Max 300 point deduction
            score -= min(normalized_features['borrow_to_deposit_ratio'] * 100, 200)  # Max 200 point deduction
            
            # Repay behavior (using normalized threshold)
            if normalized_features['repay_rate'] < 0.3:
                score -= 150
            elif normalized_features['repay_rate'] < 0.7:
                score -= 75
                
            # Activity patterns
            if normalized_features['activity_frequency'] > 0.8:  # Very high frequency
                score -= 100
            elif normalized_features['activity_frequency'] < 0.1:  # Very low activity
                score -= 50
                
            # Health factor consideration
            if normalized_features['health_factor'] < 0.2:  # Poor health
                score -= 200
            elif normalized_features['health_factor'] < 0.5:
                score -= 100
                
            # Bonuses for good behavior
            if normalized_features['unique_tokens_used'] > 1:  # Diversification bonus
                score += 50
                
            if normalized_features['repay_rate'] > 0.9:  # Excellent repayment
                score += 25
                
            # Ensure score is within bounds
            return max(min(score, 1000), 0)
            
        except Exception as e:
            logger.error(f"Error calculating score for {features.get('wallet_id', 'unknown')}: {e}")
            return 500  # Default middle score for errors

    def _get_normalized_features(self, features):
        """Get normalized feature values for scoring."""
        if self.features_df is None:
            # If we don't have the full dataset yet, use rough estimates
            return {
                'liquidation_count': min(features['liquidation_count'] / 5, 1),
                'borrow_to_deposit_ratio': min(features['borrow_to_deposit_ratio'] / 10, 1),
                'repay_rate': min(features['repay_rate'], 1),
                'activity_frequency': min(features['activity_frequency'] / 10, 1),
                'health_factor': min(features['health_factor'] / 100, 1),
                'unique_tokens_used': min(features['unique_tokens_used'] / 5, 1)
            }
        
        # Use proper normalization if we have the full dataset
        feature_cols = ['liquidation_count', 'borrow_to_deposit_ratio', 'repay_rate', 
                       'activity_frequency', 'health_factor', 'unique_tokens_used']
        
        normalized_values = {}
        for col in feature_cols:
            col_values = self.features_df[col].values
            min_val, max_val = col_values.min(), col_values.max()
            if max_val > min_val:
                normalized_values[col] = (features[col] - min_val) / (max_val - min_val)
            else:
                normalized_values[col] = 0
                
        return normalized_values

    def process_wallets(self, wallets_file='wallets.csv'):
        """Process all wallets with parallel execution."""
        # Input validation
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

        # Parallel data fetching
        features_list = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all wallet fetching tasks
            future_to_wallet = {
                executor.submit(self._process_single_wallet, wallet): wallet 
                for wallet in wallet_addresses
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_wallet):
                wallet = future_to_wallet[future]
                try:
                    features = future.result()
                    if features:
                        features_list.append(features)
                        logger.info(f"Processed {len(features_list)}/{len(wallet_addresses)} wallets")
                except Exception as e:
                    logger.error(f"Error processing wallet {wallet}: {e}")
                    # Add default features for failed wallets
                    features_list.append(self._get_default_features(wallet))

        # Create features DataFrame
        self.features_df = pd.DataFrame(features_list)
        
        # Calculate scores after we have all features (for proper normalization)
        scores_list = []
        for _, features in self.features_df.iterrows():
            score = self.calculate_risk_score(features.to_dict())
            scores_list.append({
                'wallet_id': features['wallet_id'],
                'score': score
            })
        
        self.scores_df = pd.DataFrame(scores_list)
        
        # Sort by wallet_id for consistency
        self.scores_df = self.scores_df.sort_values('wallet_id').reset_index(drop=True)
        
        logger.info(f"✅ Successfully processed {len(self.scores_df)} wallets")
        return self.scores_df

    def _process_single_wallet(self, wallet_address):
        """Process a single wallet - fetch data and extract features."""
        try:
            data = self.fetch_wallet_data(wallet_address)
            features = self.process_wallet_features(data, wallet_address)
            return features
        except Exception as e:
            logger.error(f"Failed to process wallet {wallet_address}: {e}")
            return self._get_default_features(wallet_address)

    def save_results(self, features_file='wallet_features.csv', scores_file='wallet_scores.csv'):
        """Save results to CSV files with headers."""
        if self.features_df is not None:
            # Add header comment
            with open(features_file, 'w') as f:
                f.write(f"# Wallet features extracted on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Total wallets processed: {len(self.features_df)}\n")
            self.features_df.to_csv(features_file, mode='a', index=False)
            logger.info(f"Features saved to {features_file}")

        if self.scores_df is not None:
            # Add header comment
            with open(scores_file, 'w') as f:
                f.write(f"# Wallet risk scores (0-1000) generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Total wallets scored: {len(self.scores_df)}\n")
            self.scores_df.to_csv(scores_file, mode='a', index=False)
            logger.info(f"Scores saved to {scores_file}")

    def generate_score_distribution_plot(self, output_file='score_distribution.png'):
        """Generate and save score distribution histogram."""
        if not HAS_MATPLOTLIB:
            logger.warning("Matplotlib not available - skipping visualization")
            return False
            
        if self.scores_df is None:
            logger.warning("No scores available for plotting")
            return False

        plt.figure(figsize=(10, 6))
        plt.hist(self.scores_df['score'], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        plt.title('Wallet Risk Score Distribution', fontsize=16, fontweight='bold')
        plt.xlabel('Risk Score (0-1000)', fontsize=12)
        plt.ylabel('Number of Wallets', fontsize=12)
        plt.grid(True, alpha=0.3)
        
        # Add statistics text
        mean_score = self.scores_df['score'].mean()
        median_score = self.scores_df['score'].median()
        plt.axvline(mean_score, color='red', linestyle='--', label=f'Mean: {mean_score:.1f}')
        plt.axvline(median_score, color='green', linestyle='--', label=f'Median: {median_score:.1f}')
        plt.legend()
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        logger.info(f"Score distribution plot saved to {output_file}")
        return True


def main():
    """Main execution function with command line arguments."""
    parser = argparse.ArgumentParser(description='DeFi Wallet Risk Scoring System')
    parser.add_argument('--simulation', action='store_true', 
                       help='Use simulation mode instead of real API data')
    parser.add_argument('--wallets-file', default='wallets.csv',
                       help='Input CSV file with wallet addresses')
    parser.add_argument('--workers', type=int, default=5,
                       help='Number of concurrent workers for API requests')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress info-level logging')
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    print("🏦 DeFi Wallet Risk Scoring System for Compound V2")
    print("=" * 50)
    
    try:
        # Initialize scorer
        scorer = CompoundWalletScorer(
            use_simulation=args.simulation, 
            max_workers=args.workers
        )
        
        # Process wallets
        start_time = time.time()
        scores_df = scorer.process_wallets(args.wallets_file)
        processing_time = time.time() - start_time
        
        # Save results
        scorer.save_results()
        
        # Generate visualization
        plot_created = scorer.generate_score_distribution_plot()
        
        # Print summary
        print(f"\n📊 Processing Summary:")
        print(f"Total wallets processed: {len(scores_df)}")
        print(f"Processing time: {processing_time:.1f} seconds")
        print(f"Average score: {scores_df['score'].mean():.1f}")
        print(f"Score range: {scores_df['score'].min():.0f} - {scores_df['score'].max():.0f}")
        print(f"Mode: {'Simulation' if args.simulation else 'Real API with simulation fallback'}")
        
        print(f"\n📁 Output files:")
        print(f"✓ wallet_scores.csv - Risk scores for all wallets")
        print(f"✓ wallet_features.csv - Detailed features for analysis") 
        if plot_created:
            print(f"✓ score_distribution.png - Score distribution visualization")
        else:
            print(f"⚠ score_distribution.png - Skipped (matplotlib not available)")
        print(f"✓ scoring.log - Processing logs")
        
        return 0
        
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
