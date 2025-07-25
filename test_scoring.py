#!/usr/bin/env python3
"""
Test script for wallet risk scoring - processes only 5 wallets for verification
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from score_wallets import CompoundWalletScorer
import logging

def test_scoring():
    """Test the scoring system with a small subset"""
    print("="*60)
    print("TESTING WALLET RISK SCORING SYSTEM")
    print("="*60)
    
    scorer = CompoundWalletScorer()
    
    try:
        # Process test wallets
        scores_df = scorer.process_wallets('test_wallets.csv')
        
        # Save results
        scorer.save_results('test_wallet_scores.csv')
        scorer.save_detailed_features('test_wallet_features.csv')
        
        print("\n" + "="*60)
        print("TEST COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"Processed {len(scores_df)} test wallets")
        print("\nTest Results:")
        print(scores_df.to_string(index=False))
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_scoring()
    if success:
        print("\n✅ System is working correctly!")
        print("You can now run the full scoring with: python score_wallets.py")
    else:
        print("\n❌ Please fix the issues before running the full scoring")
