"""
Bloom Filters for Light Clients
Task 265: Add bloom filters for light clients

Bloom filters provide space-efficient probabilistic data structures
for checking if transactions are relevant to a light client.
"""

from __future__ import annotations

import hashlib
import math
from typing import List, Set, Optional


class BloomFilter:
    """
    Bloom filter implementation for efficient membership testing

    Used by light clients to filter transactions without downloading
    the entire blockchain.
    """

    def __init__(self, size: int = 10000, hash_count: int = 3):
        """
        Initialize bloom filter

        Args:
            size: Size of bit array
            hash_count: Number of hash functions
        """
        self.size = size
        self.hash_count = hash_count
        self.bit_array = [False] * size
        self.element_count = 0

    def add(self, item: str) -> None:
        """
        Add item to bloom filter

        Args:
            item: Item to add (e.g., address, txid)
        """
        for i in range(self.hash_count):
            index = self._hash(item, i) % self.size
            self.bit_array[index] = True

        self.element_count += 1

    def contains(self, item: str) -> bool:
        """
        Check if item might be in the set

        Args:
            item: Item to check

        Returns:
            True if item might be in set (can have false positives)
            False if item is definitely not in set
        """
        for i in range(self.hash_count):
            index = self._hash(item, i) % self.size
            if not self.bit_array[index]:
                return False

        return True

    def _hash(self, item: str, seed: int) -> int:
        """
        Hash function for bloom filter

        Args:
            item: Item to hash
            seed: Seed for hash function

        Returns:
            Hash value
        """
        data = f"{item}{seed}".encode()
        hash_value = int(hashlib.sha256(data).hexdigest(), 16)
        return hash_value

    def get_false_positive_rate(self) -> float:
        """
        Calculate current false positive rate

        Returns:
            Estimated false positive rate
        """
        if self.element_count == 0:
            return 0.0

        # Formula: (1 - e^(-k*n/m))^k
        # k = hash_count, n = element_count, m = size
        k = self.hash_count
        n = self.element_count
        m = self.size

        try:
            rate = (1 - math.exp(-k * n / m)) ** k
            return rate
        except (OverflowError, ValueError):
            return 1.0

    def clear(self) -> None:
        """Clear bloom filter"""
        self.bit_array = [False] * self.size
        self.element_count = 0

    def __len__(self) -> int:
        """Get number of elements added"""
        return self.element_count

    @staticmethod
    def optimal_size(expected_elements: int, false_positive_rate: float) -> int:
        """
        Calculate optimal bloom filter size

        Args:
            expected_elements: Expected number of elements
            false_positive_rate: Desired false positive rate

        Returns:
            Optimal size
        """
        m = -(expected_elements * math.log(false_positive_rate)) / (math.log(2) ** 2)
        return int(math.ceil(m))

    @staticmethod
    def optimal_hash_count(size: int, expected_elements: int) -> int:
        """
        Calculate optimal number of hash functions

        Args:
            size: Bloom filter size
            expected_elements: Expected number of elements

        Returns:
            Optimal hash count
        """
        k = (size / expected_elements) * math.log(2)
        return max(1, int(math.ceil(k)))


class TransactionBloomFilter:
    """
    Bloom filter specifically for transaction filtering

    Light clients can filter transactions by addresses without
    downloading all transaction data.
    """

    def __init__(self, addresses: List[str], false_positive_rate: float = 0.01):
        """
        Initialize transaction bloom filter

        Args:
            addresses: List of addresses to track
            false_positive_rate: Desired false positive rate
        """
        self.addresses = set(addresses)

        # Calculate optimal parameters
        size = BloomFilter.optimal_size(len(addresses), false_positive_rate)
        hash_count = BloomFilter.optimal_hash_count(size, len(addresses))

        self.bloom = BloomFilter(size, hash_count)

        # Add all addresses
        for address in addresses:
            self.bloom.add(address)

    def is_relevant(self, transaction: any) -> bool:
        """
        Check if transaction is relevant to tracked addresses

        Args:
            transaction: Transaction object

        Returns:
            True if transaction might be relevant
        """
        # Check sender
        if self.bloom.contains(transaction.sender):
            return True

        # Check recipient
        if self.bloom.contains(transaction.recipient):
            return True

        return False

    def add_address(self, address: str) -> None:
        """Add address to filter"""
        self.addresses.add(address)
        self.bloom.add(address)

    def get_stats(self) -> dict:
        """Get filter statistics"""
        return {
            "tracked_addresses": len(self.addresses),
            "bloom_size": self.bloom.size,
            "hash_count": self.bloom.hash_count,
            "false_positive_rate": self.bloom.get_false_positive_rate()
        }


class BlockBloomFilter:
    """
    Bloom filter for entire blocks

    Allows light clients to quickly determine if a block contains
    relevant transactions.
    """

    def __init__(self, size: int = 10000, hash_count: int = 3):
        self.bloom = BloomFilter(size, hash_count)
        self.transaction_count = 0

    def add_block(self, block: any) -> None:
        """
        Add block's transactions to bloom filter

        Args:
            block: Block object
        """
        for tx in block.transactions:
            # Add transaction ID
            self.bloom.add(tx.txid)

            # Add sender and recipient
            self.bloom.add(tx.sender)
            self.bloom.add(tx.recipient)

            self.transaction_count += 1

    def might_contain_address(self, address: str) -> bool:
        """
        Check if block might contain transactions for address

        Args:
            address: Address to check

        Returns:
            True if block might contain relevant transactions
        """
        return self.bloom.contains(address)

    def might_contain_transaction(self, txid: str) -> bool:
        """
        Check if block might contain transaction

        Args:
            txid: Transaction ID

        Returns:
            True if block might contain transaction
        """
        return self.bloom.contains(txid)


class MultiBloomFilter:
    """
    Multiple bloom filters for different data types

    Separates filters for addresses, transactions, etc.
    for better accuracy.
    """

    def __init__(
        self,
        address_filter_size: int = 10000,
        tx_filter_size: int = 50000
    ):
        self.address_bloom = BloomFilter(address_filter_size, 3)
        self.tx_bloom = BloomFilter(tx_filter_size, 3)

    def add_address(self, address: str) -> None:
        """Add address to filter"""
        self.address_bloom.add(address)

    def add_transaction(self, txid: str) -> None:
        """Add transaction to filter"""
        self.tx_bloom.add(txid)

    def contains_address(self, address: str) -> bool:
        """Check if address is in filter"""
        return self.address_bloom.contains(address)

    def contains_transaction(self, txid: str) -> bool:
        """Check if transaction is in filter"""
        return self.tx_bloom.contains(txid)

    def get_stats(self) -> dict:
        """Get statistics for all filters"""
        return {
            "address_filter": {
                "size": self.address_bloom.size,
                "elements": len(self.address_bloom),
                "false_positive_rate": self.address_bloom.get_false_positive_rate()
            },
            "tx_filter": {
                "size": self.tx_bloom.size,
                "elements": len(self.tx_bloom),
                "false_positive_rate": self.tx_bloom.get_false_positive_rate()
            }
        }


class LightClientFilter:
    """
    Complete bloom filter solution for light clients

    Combines multiple filters for efficient transaction filtering
    """

    def __init__(self, tracked_addresses: List[str]):
        """
        Initialize light client filter

        Args:
            tracked_addresses: Addresses to track
        """
        self.tracked_addresses = set(tracked_addresses)

        # Create bloom filter
        size = BloomFilter.optimal_size(len(tracked_addresses) * 2, 0.01)
        hash_count = BloomFilter.optimal_hash_count(size, len(tracked_addresses) * 2)

        self.bloom = BloomFilter(size, hash_count)

        # Add addresses
        for address in tracked_addresses:
            self.bloom.add(address)

        self.relevant_transactions: List[str] = []

    def filter_block(self, block: any) -> List[any]:
        """
        Filter block for relevant transactions

        Args:
            block: Block to filter

        Returns:
            List of relevant transactions
        """
        relevant = []

        for tx in block.transactions:
            if self._is_relevant(tx):
                relevant.append(tx)
                self.relevant_transactions.append(tx.txid)

        return relevant

    def _is_relevant(self, transaction: any) -> bool:
        """Check if transaction is relevant"""
        # Use bloom filter for quick check
        if self.bloom.contains(transaction.sender):
            # Verify against actual set (bloom filter may have false positives)
            if transaction.sender in self.tracked_addresses:
                return True

        if self.bloom.contains(transaction.recipient):
            if transaction.recipient in self.tracked_addresses:
                return True

        return False

    def add_address(self, address: str) -> None:
        """Add new address to track"""
        self.tracked_addresses.add(address)
        self.bloom.add(address)

    def get_stats(self) -> dict:
        """Get filter statistics"""
        return {
            "tracked_addresses": len(self.tracked_addresses),
            "relevant_transactions": len(self.relevant_transactions),
            "bloom_filter": {
                "size": self.bloom.size,
                "hash_count": self.bloom.hash_count,
                "false_positive_rate": self.bloom.get_false_positive_rate()
            }
        }
