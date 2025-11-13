"""
XAI Blockchain - UTXO Manager

Manages the Unspent Transaction Output (UTXO) set for the blockchain.
Ensures that transactions spend only available UTXOs and prevents double-spending.
"""

from typing import Dict, List, Any, Optional, TYPE_CHECKING
from collections import defaultdict
from aixn.core.structured_logger import StructuredLogger, get_structured_logger

if TYPE_CHECKING:
    from aixn.core.blockchain import Transaction


class UTXOManager:
    """
    Manages the UTXO set, providing functionality to add, remove, and query UTXOs.
    """

    def __init__(self, logger: Optional[StructuredLogger] = None):
        # utxo_set: {address: [{txid, vout, amount, script_pubkey}, ...]}
        self.utxo_set: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.logger = logger or get_structured_logger()
        self.total_utxos = 0
        self.total_value = 0.0

    def add_utxo(self, address: str, txid: str, vout: int, amount: float, script_pubkey: str):
        """
        Adds a new UTXO to the set.

        Args:
            address: The address to which the UTXO belongs.
            txid: The transaction ID that created this UTXO.
            vout: The output index within the transaction.
            amount: The amount of the UTXO.
            script_pubkey: The script public key (or similar locking script).
        """
        utxo = {
            'txid': txid,
            'vout': vout,
            'amount': amount,
            'script_pubkey': script_pubkey,
            'spent': False  # Track if this UTXO has been spent
        }
        self.utxo_set[address].append(utxo)
        self.total_utxos += 1
        self.total_value += amount
        self.logger.debug(f"Added UTXO: {txid}:{vout} for {address} with {amount} XAI",
                          address=address, txid=txid, vout=vout, amount=amount)

    def mark_utxo_spent(self, address: str, txid: str, vout: int) -> bool:
        """
        Marks a specific UTXO as spent.

        Args:
            address: The address that owned the UTXO.
            txid: The transaction ID of the UTXO to mark as spent.
            vout: The output index of the UTXO to mark as spent.

        Returns:
            True if the UTXO was found and marked as spent, False otherwise.
        """
        if address in self.utxo_set:
            for utxo in self.utxo_set[address]:
                if utxo['txid'] == txid and utxo['vout'] == vout and not utxo['spent']:
                    utxo['spent'] = True
                    self.total_value -= utxo['amount']
                    self.logger.debug(f"Marked UTXO: {txid}:{vout} for {address} as spent",
                                      address=address, txid=txid, vout=vout)
                    return True
        self.logger.warn(f"Attempted to mark non-existent or already spent UTXO: {txid}:{vout} for {address}",
                         address=address, txid=txid, vout=vout)
        return False

    def get_utxos_for_address(self, address: str) -> List[Dict[str, Any]]:
        """
        Retrieves all unspent UTXOs for a given address.

        Args:
            address: The address to query.

        Returns:
            A list of unspent UTXO dictionaries.
        """
        return [utxo for utxo in self.utxo_set[address] if not utxo['spent']]

    def get_balance(self, address: str) -> float:
        """
        Calculates the total balance for a given address from its UTXOs.

        Args:
            address: The address to calculate the balance for.

        Returns:
            The total balance as a float.
        """
        return sum(utxo['amount'] for utxo in self.get_utxos_for_address(address))

    def process_transaction_outputs(self, transaction: 'Transaction'):
        """
        Adds new UTXOs created by a transaction's outputs.
        Each output in the transaction creates a new UTXO.

        Args:
            transaction: The transaction whose outputs are to be added as UTXOs.
        """
        for vout, output in enumerate(transaction.outputs):
            self.add_utxo(output['address'], transaction.txid, vout, output['amount'], f"P2PKH {output['address']}")
        self.logger.info(f"Processed outputs for transaction {transaction.txid[:10]}...", txid=transaction.txid)

    def process_transaction_inputs(self, transaction: 'Transaction') -> bool:
        """
        Marks UTXOs consumed by a transaction's inputs as spent.

        Args:
            transaction: The transaction whose inputs are to be marked as spent.

        Returns:
            True if all inputs were successfully marked as spent, False otherwise.
        """
        if transaction.sender == "COINBASE": # Coinbase transactions don't spend inputs
            return True

        for input_utxo_ref in transaction.inputs:
            txid = input_utxo_ref['txid']
            vout = input_utxo_ref['vout']
            if not self.mark_utxo_spent(transaction.sender, txid, vout):
                self.logger.error(f"Failed to mark UTXO {txid}:{vout} as spent for sender {transaction.sender}.",
                                  txid=txid, vout=vout, sender=transaction.sender)
                return False
        self.logger.info(f"Processed inputs for transaction {transaction.txid[:10]}...", txid=transaction.txid)
        return True

    def get_unspent_output(self, txid: str, vout: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific unspent UTXO by its transaction ID and output index.

        Args:
            txid: The transaction ID of the UTXO.
            vout: The output index of the UTXO within the transaction.

        Returns:
            The UTXO dictionary if found and unspent, otherwise None.
        """
        for address_utxos in self.utxo_set.values():
            for utxo in address_utxos:
                if utxo['txid'] == txid and utxo['vout'] == vout and not utxo['spent']:
                    return utxo
        return None

    def find_spendable_utxos(self, address: str, amount: float) -> List[Dict[str, Any]]:
        """
        Finds a set of unspent UTXOs for an address that sum up to at least the required amount.

        Args:
            address: The address to find UTXOs for.
            amount: The minimum amount required.

        Returns:
            A list of UTXO dictionaries that can be spent.
        """
        spendable_utxos = []
        current_sum = 0.0
        for utxo in self.get_utxos_for_address(address):
            spendable_utxos.append(utxo)
            current_sum += utxo['amount']
            if current_sum >= amount:
                break
        
        if current_sum < amount:
            return [] # Not enough spendable UTXOs

        return spendable_utxos

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the UTXO set to a dictionary for serialization.
        """
        # Filter out spent UTXOs for a cleaner representation if desired,
        # or keep them and rely on the 'spent' flag.
        # For now, we'll serialize the full internal state.
        serializable_utxo_set = {}
        for address, utxos in self.utxo_set.items():
            serializable_utxo_set[address] = [
                {k: v for k, v in utxo.items()} # Copy to avoid modifying original
                for utxo in utxos
            ]
        return serializable_utxo_set

    def load_utxo_set(self, utxo_set_data: Dict[str, Any]):
        """
        Loads the UTXO set from a dictionary.
        """
        self.utxo_set = defaultdict(list)
        self.total_utxos = 0
        self.total_value = 0.0
        for address, utxos in utxo_set_data.items():
            for utxo in utxos:
                # Re-add UTXOs to correctly update total_utxos and total_value
                # This assumes utxo['spent'] is correctly loaded
                if not utxo.get('spent', False):
                    self.add_utxo(address, utxo['txid'], utxo['vout'], utxo['amount'], utxo['script_pubkey'])
                else:
                    # If spent, just add to the list without affecting totals
                    self.utxo_set[address].append(utxo)
        self.logger.info("UTXO set loaded.")

    def get_total_unspent_value(self) -> float:
        """
        Returns the total value of all unspent UTXOs in the system.
        """
        return self.total_value

    def get_unique_addresses_count(self) -> int:
        """
        Returns the count of unique addresses that have unspent UTXOs.
        """
        return len([addr for addr, utxos in self.utxo_set.items() if self.get_balance(addr) > 0])

    def get_stats(self) -> Dict[str, Any]:
        """
        Returns statistics about the current UTXO set.
        """
        return {
            'total_utxos': self.total_utxos,
            'total_unspent_value': self.total_value,
            'unique_addresses_with_utxos': len(self.utxo_set)
        }

    def reset(self):
        """
        Resets the UTXO manager to its initial state.
        """
        self.utxo_set = defaultdict(list)
        self.total_utxos = 0
        self.total_value = 0.0
        self.logger.info("UTXO Manager reset.")

# Global instance for convenience
_global_utxo_manager = None

def get_utxo_manager(logger: Optional[StructuredLogger] = None) -> UTXOManager:
    """
    Get global UTXO manager instance.
    """
    global _global_utxo_manager
    if _global_utxo_manager is None:
        _global_utxo_manager = UTXOManager(logger)
    return _global_utxo_manager
