"""
XAI Blockchain Launch Sequence
Initialize and launch the XAI blockchain with all components
"""
import os
import sys
import json
import time
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.chain import Blockchain
from blockchain.consensus import ProofOfIntelligence
from contracts.aixn_token import XAIToken
from wallet.wallet import WalletManager, XAIWallet
from ai.agents.momentum_trader import MomentumTrader
from ai.api_rotator import AIAPIRotator


class XAILauncher:
    """Main launcher for XAI blockchain"""

    def __init__(self, mode="local"):
        self.mode = mode  # local, testnet, mainnet
        self.blockchain = None
        self.token_contract = None
        self.consensus = None
        self.wallet_manager = None
        self.ai_rotator = None
        self.ai_traders = []
        self.founder_wallet = None

    def initialize_components(self):
        """Initialize all blockchain components"""
        print("\n" + "="*50)
        print("XAI BLOCKCHAIN LAUNCH SEQUENCE")
        print("="*50)
        print(f"Mode: {self.mode.upper()}")
        print(f"Launch Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50 + "\n")

        # Step 1: Initialize blockchain
        print("[1/8] Initializing blockchain...")
        self.blockchain = Blockchain()
        print(f"✓ Blockchain initialized with genesis block")
        print(f"  - Difficulty: {self.blockchain.difficulty}")
        print(f"  - Total Supply: {self.blockchain.total_supply:,} XAI")

        # Step 2: Initialize token contract
        print("\n[2/8] Deploying XAI token contract...")
        self.token_contract = XAIToken()
        metrics = self.token_contract.get_token_metrics()
        print(f"✓ Token contract deployed")
        print(f"  - Symbol: {metrics['symbol']}")
        print(f"  - Initial Price: ${metrics['price_usd']}")
        print(f"  - Burn Rate: {metrics['burn_rate']*100}%")

        # Step 3: Initialize consensus mechanism
        print("\n[3/8] Setting up Proof of Intelligence consensus...")
        self.consensus = ProofOfIntelligence()
        print(f"✓ Consensus mechanism initialized")
        print(f"  - Minimum Accuracy: {self.consensus.min_accuracy*100}%")

        # Step 4: Create wallet
        print("\n[4/8] Creating wallet...")
        self.wallet_manager = WalletManager()
        self.founder_wallet = self.wallet_manager.create_wallet("founder")
        wallet_info = self.founder_wallet.get_wallet_info()
        print(f"✓ Wallet created")
        print(f"  - Address: {wallet_info['address']}")
        print(f"  - Seed phrase saved to: wallets/founder.json")

        # Step 5: Initialize AI components
        print("\n[5/8] Initializing AI systems...")
        self.ai_rotator = AIAPIRotator()
        stats = self.ai_rotator.get_usage_stats()
        print(f"✓ AI API rotator initialized")
        print(f"  - Available requests: {stats['available_requests']:,}")

        # Step 6: Create AI trading agents
        print("\n[6/8] Deploying AI trading agents...")
        trader = MomentumTrader()
        self.ai_traders.append(trader)
        print(f"✓ Momentum trader deployed")
        print(f"  - Risk per trade: {trader.config['risk_per_trade']*100}%")
        print(f"  - Min confidence: {trader.config['min_confidence']*100}%")

        # Step 7: Allocate tokens
        print("\n[7/8] Allocating tokens...")
        self._allocate_founder_tokens()

        # Step 8: Prepare for launch
        print("\n[8/8] Finalizing launch preparations...")
        self._save_launch_config()
        print("✓ Launch configuration saved")

        print("\n" + "="*50)
        print("LAUNCH SEQUENCE COMPLETE!")
        print("="*50)

    def _allocate_founder_tokens(self):
        """Allocate initial tokens to founder"""
        # Create vesting schedule for founder (100M tokens over 4 years)
        vesting_amount = 100_000_000
        start_time = time.time()
        cliff_duration = 365 * 24 * 3600  # 1 year cliff
        vesting_duration = 4 * 365 * 24 * 3600  # 4 years total

        success = self.token_contract.create_vesting_schedule(
            beneficiary=self.founder_wallet.address,
            total_amount=vesting_amount,
            start_time=start_time,
            cliff_duration=cliff_duration,
            vesting_duration=vesting_duration
        )

        if success:
            print(f"✓ Vesting schedule created")
            print(f"  - Amount: {vesting_amount:,} XAI")
            print(f"  - Cliff: 1 year")
            print(f"  - Vesting: 4 years")

        # Allocate initial liquidity tokens (for founder to provide liquidity)
        liquidity_amount = 10_000_000
        self.token_contract.balances[self.founder_wallet.address] = liquidity_amount
        self.founder_wallet.update_balance(liquidity_amount)
        print(f"✓ Initial liquidity allocated: {liquidity_amount:,} XAI")

    def _save_launch_config(self):
        """Save launch configuration"""
        config = {
            'launch_time': time.time(),
            'mode': self.mode,
            'blockchain': {
                'height': len(self.blockchain.chain),
                'difficulty': self.blockchain.difficulty,
                'total_supply': self.blockchain.total_supply
            },
            'token': {
                'circulating_supply': self.token_contract.circulating_supply,
                'burn_rate': self.token_contract.burn_rate,
                'initial_price': 0.001
            },
            'founder': {
                'address': self.founder_wallet.address,
                'vested_tokens': 100_000_000,
                'liquid_tokens': 10_000_000
            },
            'ai_agents': len(self.ai_traders)
        }

        with open('launch_config.json', 'w') as f:
            json.dump(config, f, indent=2)

    def start_mining(self):
        """Start mining blocks"""
        print("\n" + "="*50)
        print("STARTING MINING OPERATIONS")
        print("="*50)

        miner_address = self.founder_wallet.address
        blocks_mined = 0
        total_rewards = 0

        print(f"\nMiner Address: {miner_address}")
        print("Press Ctrl+C to stop mining\n")

        try:
            while True:
                # Generate AI task for consensus
                task = self.consensus.generate_ai_task(difficulty=1)
                print(f"\n[Block {blocks_mined + 1}] AI Task: {task.task_type}")

                # Simulate AI computation
                proof = self.consensus.simulate_ai_computation(task, miner_address)
                is_valid, score = self.consensus.validate_proof(proof, task)

                if is_valid:
                    print(f"✓ AI Proof Valid (Score: {score:.2f})")

                    # Mine block
                    new_block = self.blockchain.mine_block(miner_address)
                    blocks_mined += 1
                    reward = self.blockchain.mining_reward

                    # Mint rewards
                    self.token_contract.mint(miner_address, reward, "mining_reward")
                    total_rewards += reward

                    print(f"✓ Block mined: {new_block.hash[:16]}...")
                    print(f"  - Height: {new_block.index}")
                    print(f"  - Reward: {reward} XAI")
                    print(f"  - Total mined: {total_rewards:,} XAI")

                    # Update wallet balance
                    new_balance = self.token_contract.get_balance(miner_address)
                    self.founder_wallet.update_balance(new_balance)

                else:
                    print(f"✗ AI Proof Invalid (Score: {score:.2f})")

                # Wait before next block
                time.sleep(2)  # 2-second block time

        except KeyboardInterrupt:
            print("\n\nMining stopped by user")
            print(f"Total blocks mined: {blocks_mined}")
            print(f"Total rewards earned: {total_rewards:,} XAI")

    def run_ai_trading_simulation(self):
        """Run AI trading simulation"""
        print("\n" + "="*50)
        print("AI TRADING SIMULATION")
        print("="*50)

        trader = self.ai_traders[0]

        # Generate mock market data
        market_data = []
        base_price = 0.001  # Starting at $0.001

        print("\nGenerating market data...")
        for i in range(100):
            price = base_price * (1 + (i/1000) + random.uniform(-0.05, 0.05))
            volume = 100000 * random.uniform(0.5, 2.0)

            market_data.append(MarketData(
                symbol="XAI/USDC",
                price=price,
                volume=volume,
                change_24h=random.uniform(-10, 10),
                high_24h=price * 1.1,
                low_24h=price * 0.9,
                timestamp=time.time() + i * 60
            ))

        print(f"✓ Generated {len(market_data)} data points")

        # Analyze market
        print("\nAnalyzing market conditions...")
        analysis = trader.analyze_market(market_data)

        print(f"\nMarket Analysis:")
        print(f"  - Signal: {analysis['signal'].value}")
        print(f"  - Confidence: {analysis['confidence']*100:.1f}%")

        indicators = analysis['indicators']
        print(f"\nTechnical Indicators:")
        print(f"  - MA Short: ${indicators['ma_short']:.6f}")
        print(f"  - MA Long: ${indicators['ma_long']:.6f}")
        print(f"  - RSI: {indicators['rsi']:.1f}")
        print(f"  - Volume Ratio: {indicators['volume_ratio']:.2f}x")
        print(f"  - Momentum: {indicators['momentum_score']*100:.1f}%")

        # Make trading decision
        decision = trader.make_trading_decision(analysis)

        if decision:
            print(f"\nTrading Decision:")
            print(f"  - Action: {decision.action.value}")
            print(f"  - Amount: {decision.amount:.2f} USDC")
            print(f"  - Entry: ${decision.entry_price:.6f}")
            print(f"  - Stop Loss: ${decision.stop_loss:.6f}")
            print(f"  - Take Profit: ${decision.take_profit:.6f}")
            print(f"\nReasoning: {decision.reasoning}")

            # Execute trade
            result = trader.execute_trade(decision)
            print(f"\n{result['message']}")
        else:
            print("\n✗ No trading action (confidence below threshold)")

        # Show performance
        performance = trader.get_performance_report()
        print(f"\nTrader Performance:")
        print(f"  - Portfolio Value: ${performance['total_value']:.2f}")
        print(f"  - Open Positions: {performance['open_positions']}")

    def show_dashboard(self):
        """Display blockchain dashboard"""
        print("\n" + "="*50)
        print("XAI BLOCKCHAIN DASHBOARD")
        print("="*50)

        # Blockchain stats
        chain_stats = self.blockchain.get_chain_stats()
        print(f"\nBlockchain Status:")
        print(f"  - Height: {chain_stats['height']}")
        print(f"  - Difficulty: {chain_stats['difficulty']}")
        print(f"  - Pending Transactions: {chain_stats['pending_transactions']}")

        # Token metrics
        token_metrics = self.token_contract.get_token_metrics()
        print(f"\nToken Metrics:")
        print(f"  - Total Supply: {token_metrics['total_supply']:,} XAI")
        print(f"  - Circulating: {token_metrics['circulating_supply']:,} XAI")
        print(f"  - Burned: {token_metrics['total_burned']:,} XAI")
        print(f"  - Staked: {token_metrics['total_staked']:,} XAI")
        print(f"  - Price: ${token_metrics['price_usd']}")
        print(f"  - Market Cap: ${token_metrics['market_cap']:,.2f}")

        # AI status
        ai_stats = self.ai_rotator.get_usage_stats()
        print(f"\nAI System Status:")
        print(f"  - Requests Today: {ai_stats['total_requests_today']}")
        print(f"  - Available: {ai_stats['available_requests']:,}")
        print(f"  - Success Rate: {ai_stats['success_rate']*100:.1f}%")

        # Wallet
        wallet_info = self.founder_wallet.get_wallet_info()
        print(f"\nWallet:")
        print(f"  - Address: {wallet_info['address'][:16]}...")
        print(f"  - Balance: {wallet_info['balance']:,} XAI")
        print(f"  - AI Agents: {wallet_info['ai_agents']}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='XAI Blockchain Launch Sequence')
    parser.add_argument('--mode', choices=['local', 'testnet', 'mainnet'],
                       default='local', help='Launch mode')
    parser.add_argument('--mine', action='store_true',
                       help='Start mining after launch')
    parser.add_argument('--trade', action='store_true',
                       help='Run AI trading simulation')
    parser.add_argument('--dashboard', action='store_true',
                       help='Show dashboard only')

    args = parser.parse_args()

    # Create launcher
    launcher = XAILauncher(mode=args.mode)

    # Initialize components
    launcher.initialize_components()

    # Show dashboard
    launcher.show_dashboard()

    # Optional: start mining
    if args.mine:
        launcher.start_mining()

    # Optional: run trading simulation
    if args.trade:
        import random
        from ai.agents.momentum_trader import MarketData
        launcher.run_ai_trading_simulation()

    print("\n" + "="*50)
    print("XAI Blockchain is ready!")
    print("Next steps:")
    print("  1. Run 'python launch_sequence.py --mine' to start mining")
    print("  2. Run 'python launch_sequence.py --trade' for AI trading demo")
    print("  3. Check wallets/ directory for your founder wallet")
    print("="*50)


if __name__ == "__main__":
    main()