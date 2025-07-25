#!/usr/bin/env python3
"""Unit tests for the DeFi Wallet Risk Scoring System"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import sys
import os

# Add the current directory to the path to import our module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from score_wallets_improved import CompoundWalletScorer
except ImportError:
    # Fallback to original if improved version not available
    from score_wallets import CompoundWalletScorer


class TestCompoundWalletScorer(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.scorer = CompoundWalletScorer(use_simulation=True)
        self.sample_wallet = "0x1234567890123456789012345678901234567890"
        
    def test_wallet_address_validation(self):
        """Test wallet address validation."""
        # Valid addresses
        self.assertTrue(self.scorer.validate_wallet_address("0x1234567890123456789012345678901234567890"))
        self.assertTrue(self.scorer.validate_wallet_address("0xabcdefABCDEF1234567890123456789012345678"))
        
        # Invalid addresses
        self.assertFalse(self.scorer.validate_wallet_address("invalid"))
        self.assertFalse(self.scorer.validate_wallet_address("0x123"))  # Too short
        self.assertFalse(self.scorer.validate_wallet_address("1234567890123456789012345678901234567890"))  # No 0x prefix

    def test_simulation_data_generation(self):
        """Test that simulation generates consistent data for the same wallet."""
        data1 = self.scorer._simulate_wallet_data(self.sample_wallet)
        data2 = self.scorer._simulate_wallet_data(self.sample_wallet)
        
        # Should generate the same data for the same wallet (deterministic)
        self.assertEqual(len(data1['mintEvents']), len(data2['mintEvents']))
        self.assertEqual(len(data1['borrowEvents']), len(data2['borrowEvents']))
        self.assertEqual(data1['account']['countLiquidated'], data2['account']['countLiquidated'])

    def test_feature_extraction_with_simulation_data(self):
        """Test feature extraction with simulated data."""
        data = self.scorer._simulate_wallet_data(self.sample_wallet)
        features = self.scorer.process_wallet_features(data, self.sample_wallet)
        
        # Check that all required features are present
        expected_features = [
            'wallet_id', 'total_deposits', 'total_borrows', 'total_repays', 'total_redeems',
            'current_supply', 'current_borrow', 'deposit_count', 'borrow_count', 
            'repay_count', 'redeem_count', 'liquidation_count', 'borrow_to_deposit_ratio',
            'repay_rate', 'health_factor', 'unique_tokens_used', 'activity_duration_days',
            'activity_frequency'
        ]
        
        for feature in expected_features:
            self.assertIn(feature, features)
            
        # Check feature types and ranges
        self.assertEqual(features['wallet_id'], self.sample_wallet)
        self.assertGreaterEqual(features['total_deposits'], 0)
        self.assertGreaterEqual(features['borrow_to_deposit_ratio'], 0)
        self.assertLessEqual(features['borrow_to_deposit_ratio'], 10)  # Should be capped
        self.assertGreaterEqual(features['repay_rate'], 0)

    def test_risk_score_calculation(self):
        """Test risk score calculation."""
        # Test with different feature sets
        safe_features = {
            'wallet_id': self.sample_wallet,
            'liquidation_count': 0,
            'borrow_to_deposit_ratio': 0.2,
            'repay_rate': 0.95,
            'activity_frequency': 0.5,
            'health_factor': 5.0,
            'unique_tokens_used': 3
        }
        
        risky_features = {
            'wallet_id': self.sample_wallet,
            'liquidation_count': 2,
            'borrow_to_deposit_ratio': 8.0,
            'repay_rate': 0.1,
            'activity_frequency': 10.0,
            'health_factor': 0.1,
            'unique_tokens_used': 1
        }
        
        safe_score = self.scorer.calculate_risk_score(safe_features)
        risky_score = self.scorer.calculate_risk_score(risky_features)
        
        # Safe wallet should have higher score than risky wallet
        self.assertGreater(safe_score, risky_score)
        
        # Scores should be within valid range
        self.assertGreaterEqual(safe_score, 0)
        self.assertLessEqual(safe_score, 1000)
        self.assertGreaterEqual(risky_score, 0)
        self.assertLessEqual(risky_score, 1000)

    def test_default_features_for_failed_processing(self):
        """Test that default features are returned when processing fails."""
        features = self.scorer._get_default_features(self.sample_wallet)
        
        self.assertEqual(features['wallet_id'], self.sample_wallet)
        self.assertEqual(features['total_deposits'], 0)
        self.assertEqual(features['liquidation_count'], 0)
        self.assertEqual(features['health_factor'], float('inf'))

    @patch('pandas.read_csv')
    def test_process_wallets_input_validation(self, mock_read_csv):
        """Test input validation for process_wallets method."""
        # Test missing file
        with self.assertRaises(FileNotFoundError):
            self.scorer.process_wallets('nonexistent.csv')
        
        # Test missing wallet_id column
        mock_read_csv.return_value = pd.DataFrame({'address': ['0x123']})
        with self.assertRaises(ValueError):
            self.scorer.process_wallets('test.csv')

    def test_feature_extraction_with_empty_data(self):
        """Test feature extraction with empty/null data."""
        empty_data = {
            'account': None,
            'mintEvents': [],
            'borrowEvents': [],
            'repayEvents': [],
            'redeemEvents': [],
            'liquidationEvents': []
        }
        
        features = self.scorer.process_wallet_features(empty_data, self.sample_wallet)
        
        # Should return default values without crashing
        self.assertEqual(features['wallet_id'], self.sample_wallet)
        self.assertEqual(features['total_deposits'], 0)
        self.assertEqual(features['deposit_count'], 0)

    def test_borrow_to_deposit_ratio_capping(self):
        """Test that borrow_to_deposit_ratio is properly capped at 10."""
        high_borrow_data = {
            'account': {
                'tokens': [{'symbol': 'cUSDC', 'supplyBalanceUnderlying': '1000', 'borrowBalanceUnderlying': '0'}],
                'countLiquidated': 0,
                'hasBorrowed': True
            },
            'mintEvents': [{'underlyingAmount': '100', 'blockTime': '1640995200', 'cTokenSymbol': 'cUSDC'}],
            'borrowEvents': [{'underlyingAmount': '10000', 'blockTime': '1640995300', 'cTokenSymbol': 'cUSDC'}],
            'repayEvents': [],
            'redeemEvents': [],
            'liquidationEvents': []
        }
        
        features = self.scorer.process_wallet_features(high_borrow_data, self.sample_wallet)
        self.assertLessEqual(features['borrow_to_deposit_ratio'], 10)

    def test_health_factor_calculation(self):
        """Test health factor calculation and capping."""
        data_with_balances = {
            'account': {
                'tokens': [
                    {'symbol': 'cUSDC', 'supplyBalanceUnderlying': '10000', 'borrowBalanceUnderlying': '1000'},
                    {'symbol': 'cDAI', 'supplyBalanceUnderlying': '5000', 'borrowBalanceUnderlying': '0'}
                ],
                'countLiquidated': 0,
                'hasBorrowed': True
            },
            'mintEvents': [],
            'borrowEvents': [],
            'repayEvents': [],
            'redeemEvents': [],
            'liquidationEvents': []
        }
        
        features = self.scorer.process_wallet_features(data_with_balances, self.sample_wallet)
        
        # Health factor should be total_supply / total_borrow = 15000 / 1000 = 15
        self.assertEqual(features['health_factor'], 15.0)
        
        # Test with no borrows (should be infinity, capped at 100)
        data_with_balances['account']['tokens'][0]['borrowBalanceUnderlying'] = '0'
        features = self.scorer.process_wallet_features(data_with_balances, self.sample_wallet)
        self.assertEqual(features['health_factor'], 100)  # Capped at 100


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system."""
    
    def setUp(self):
        self.scorer = CompoundWalletScorer(use_simulation=True, max_workers=2)
        
        # Create a temporary test CSV
        self.test_wallets = pd.DataFrame({
            'wallet_id': [
                '0x1234567890123456789012345678901234567890',
                '0xabcdefabcdefabcdefabcdefabcdefabcdefabcd',
                '0x9876543210987654321098765432109876543210'
            ]
        })
        self.test_file = 'test_wallets_temp.csv'
        self.test_wallets.to_csv(self.test_file, index=False)

    def tearDown(self):
        # Clean up test file
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_end_to_end_processing(self):
        """Test the complete processing pipeline."""
        scores_df = self.scorer.process_wallets(self.test_file)
        
        # Check that we got scores for all wallets
        self.assertEqual(len(scores_df), 3)
        
        # Check that all scores are in valid range
        for _, row in scores_df.iterrows():
            self.assertGreaterEqual(row['score'], 0)
            self.assertLessEqual(row['score'], 1000)
            self.assertIn(row['wallet_id'], self.test_wallets['wallet_id'].values)


if __name__ == '__main__':
    print("🧪 Running DeFi Wallet Risk Scoring System Tests")
    print("=" * 50)
    
    # Create a test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestCompoundWalletScorer))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("✅ All tests passed!")
        exit(0)
    else:
        print("❌ Some tests failed!")
        exit(1)
