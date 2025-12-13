"""
Comprehensive tests for Address Filter security module.

Tests address whitelisting, blacklisting, filtering logic,
and access control for blockchain addresses.
"""

import pytest
from xai.security.address_filter import AddressFilter


@pytest.mark.security
class TestAddressFilterInitialization:
    """Test address filter initialization"""

    def test_init_default(self):
        """Test initialization with defaults"""
        filter = AddressFilter()
        assert len(filter.whitelist) == 0
        assert len(filter.blacklist) == 0
        assert filter.enable_whitelist is False

    def test_init_with_whitelist_enabled(self):
        """Test initialization with whitelist enabled"""
        filter = AddressFilter(enable_whitelist=True)
        assert filter.enable_whitelist is True

    def test_init_sets_are_empty(self):
        """Test that sets are initialized empty"""
        filter = AddressFilter()
        assert isinstance(filter.whitelist, set)
        assert isinstance(filter.blacklist, set)


@pytest.mark.security
class TestWhitelistManagement:
    """Test whitelist add/remove operations"""

    def test_add_to_whitelist(self):
        """Test adding address to whitelist"""
        filter = AddressFilter()
        filter.add_to_whitelist("0xABCD1234")
        assert "0xABCD1234" in filter.whitelist

    def test_add_to_whitelist_empty_raises_error(self):
        """Test adding empty address raises ValueError"""
        filter = AddressFilter()
        with pytest.raises(ValueError, match="Address cannot be empty"):
            filter.add_to_whitelist("")

    def test_add_multiple_to_whitelist(self):
        """Test adding multiple addresses to whitelist"""
        filter = AddressFilter()
        addresses = ["0xAAA", "0xBBB", "0xCCC"]
        for addr in addresses:
            filter.add_to_whitelist(addr)
        assert len(filter.whitelist) == 3

    def test_add_duplicate_to_whitelist(self):
        """Test adding duplicate doesn't create duplicates"""
        filter = AddressFilter()
        filter.add_to_whitelist("0xABCD")
        filter.add_to_whitelist("0xABCD")
        assert len(filter.whitelist) == 1

    def test_remove_from_whitelist(self):
        """Test removing address from whitelist"""
        filter = AddressFilter()
        filter.add_to_whitelist("0xABCD")
        filter.remove_from_whitelist("0xABCD")
        assert "0xABCD" not in filter.whitelist

    def test_remove_from_whitelist_empty_raises_error(self):
        """Test removing empty address raises ValueError"""
        filter = AddressFilter()
        with pytest.raises(ValueError, match="Address cannot be empty"):
            filter.remove_from_whitelist("")

    def test_remove_nonexistent_from_whitelist(self):
        """Test removing non-existent address"""
        filter = AddressFilter()
        filter.remove_from_whitelist("0xNOTHERE")
        # Should not raise error

    def test_is_whitelisted(self):
        """Test checking if address is whitelisted"""
        filter = AddressFilter()
        filter.add_to_whitelist("0xABCD")
        assert filter.is_whitelisted("0xABCD") is True
        assert filter.is_whitelisted("0xXYZ") is False


@pytest.mark.security
class TestBlacklistManagement:
    """Test blacklist add/remove operations"""

    def test_add_to_blacklist(self):
        """Test adding address to blacklist"""
        filter = AddressFilter()
        filter.add_to_blacklist("0xBADADDR")
        assert "0xBADADDR" in filter.blacklist

    def test_add_to_blacklist_empty_raises_error(self):
        """Test adding empty address raises ValueError"""
        filter = AddressFilter()
        with pytest.raises(ValueError, match="Address cannot be empty"):
            filter.add_to_blacklist("")

    def test_add_multiple_to_blacklist(self):
        """Test adding multiple addresses to blacklist"""
        filter = AddressFilter()
        bad_addresses = ["0xSCAM1", "0xSCAM2", "0xSCAM3"]
        for addr in bad_addresses:
            filter.add_to_blacklist(addr)
        assert len(filter.blacklist) == 3

    def test_add_duplicate_to_blacklist(self):
        """Test adding duplicate doesn't create duplicates"""
        filter = AddressFilter()
        filter.add_to_blacklist("0xBAD")
        filter.add_to_blacklist("0xBAD")
        assert len(filter.blacklist) == 1

    def test_remove_from_blacklist(self):
        """Test removing address from blacklist"""
        filter = AddressFilter()
        filter.add_to_blacklist("0xBAD")
        filter.remove_from_blacklist("0xBAD")
        assert "0xBAD" not in filter.blacklist

    def test_remove_from_blacklist_empty_raises_error(self):
        """Test removing empty address raises ValueError"""
        filter = AddressFilter()
        with pytest.raises(ValueError, match="Address cannot be empty"):
            filter.remove_from_blacklist("")

    def test_remove_nonexistent_from_blacklist(self):
        """Test removing non-existent address"""
        filter = AddressFilter()
        filter.remove_from_blacklist("0xNOTHERE")
        # Should not raise error

    def test_is_blacklisted(self):
        """Test checking if address is blacklisted"""
        filter = AddressFilter()
        filter.add_to_blacklist("0xBAD")
        assert filter.is_blacklisted("0xBAD") is True
        assert filter.is_blacklisted("0xGOOD") is False


@pytest.mark.security
class TestAddressCheckingBlacklistOnly:
    """Test check_address with blacklist only (whitelist disabled)"""

    def test_check_address_not_blacklisted_allowed(self):
        """Test non-blacklisted address is allowed"""
        filter = AddressFilter(enable_whitelist=False)
        filter.add_to_blacklist("0xBAD")
        assert filter.check_address("0xGOOD") is True

    def test_check_address_blacklisted_denied(self):
        """Test blacklisted address is denied"""
        filter = AddressFilter(enable_whitelist=False)
        filter.add_to_blacklist("0xBAD")
        assert filter.check_address("0xBAD") is False

    def test_check_address_empty_denied(self):
        """Test empty address is denied"""
        filter = AddressFilter(enable_whitelist=False)
        assert filter.check_address("") is False

    def test_check_address_no_lists_allows_all(self):
        """Test all addresses allowed when no blacklist"""
        filter = AddressFilter(enable_whitelist=False)
        assert filter.check_address("0xANYADDR") is True


@pytest.mark.security
class TestAddressCheckingWhitelistEnabled:
    """Test check_address with whitelist enabled"""

    def test_check_address_whitelisted_allowed(self):
        """Test whitelisted address is allowed"""
        filter = AddressFilter(enable_whitelist=True)
        filter.add_to_whitelist("0xGOOD")
        assert filter.check_address("0xGOOD") is True

    def test_check_address_not_whitelisted_denied(self):
        """Test non-whitelisted address is denied"""
        filter = AddressFilter(enable_whitelist=True)
        filter.add_to_whitelist("0xGOOD")
        assert filter.check_address("0xOTHER") is False

    def test_check_address_whitelisted_but_blacklisted_denied(self):
        """Test blacklist takes precedence over whitelist"""
        filter = AddressFilter(enable_whitelist=True)
        filter.add_to_whitelist("0xADDR")
        filter.add_to_blacklist("0xADDR")
        assert filter.check_address("0xADDR") is False

    def test_check_address_empty_denied_with_whitelist(self):
        """Test empty address denied even with whitelist"""
        filter = AddressFilter(enable_whitelist=True)
        assert filter.check_address("") is False


@pytest.mark.security
class TestBlacklistPrecedence:
    """Test that blacklist always takes precedence"""

    def test_blacklist_overrides_whitelist(self):
        """Test blacklist overrides whitelist"""
        filter = AddressFilter(enable_whitelist=True)
        filter.add_to_whitelist("0xCOMPROMISED")
        filter.add_to_blacklist("0xCOMPROMISED")
        assert filter.check_address("0xCOMPROMISED") is False

    def test_remove_from_blacklist_restores_whitelist_access(self):
        """Test removing from blacklist restores whitelist access"""
        filter = AddressFilter(enable_whitelist=True)
        filter.add_to_whitelist("0xADDR")
        filter.add_to_blacklist("0xADDR")
        assert filter.check_address("0xADDR") is False

        filter.remove_from_blacklist("0xADDR")
        assert filter.check_address("0xADDR") is True


@pytest.mark.security
class TestDynamicConfiguration:
    """Test dynamic configuration changes"""

    def test_enable_whitelist_dynamically(self):
        """Test enabling whitelist after initialization"""
        filter = AddressFilter(enable_whitelist=False)
        assert filter.check_address("0xANY") is True

        filter.enable_whitelist = True
        assert filter.check_address("0xANY") is False

    def test_disable_whitelist_dynamically(self):
        """Test disabling whitelist after initialization"""
        filter = AddressFilter(enable_whitelist=True)
        filter.add_to_whitelist("0xGOOD")
        assert filter.check_address("0xOTHER") is False

        filter.enable_whitelist = False
        assert filter.check_address("0xOTHER") is True

    def test_modify_blacklist_while_running(self):
        """Test modifying blacklist dynamically"""
        filter = AddressFilter()
        assert filter.check_address("0xADDR") is True

        filter.add_to_blacklist("0xADDR")
        assert filter.check_address("0xADDR") is False

        filter.remove_from_blacklist("0xADDR")
        assert filter.check_address("0xADDR") is True


@pytest.mark.security
class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_case_sensitive_addresses(self):
        """Test that addresses are case-sensitive"""
        filter = AddressFilter()
        filter.add_to_whitelist("0xABCD")
        # Sets are case-sensitive by default
        assert "0xABCD" in filter.whitelist
        assert "0xabcd" not in filter.whitelist

    def test_unicode_addresses(self):
        """Test handling unicode in addresses"""
        filter = AddressFilter()
        filter.add_to_whitelist("0x测试")
        assert "0x测试" in filter.whitelist

    def test_very_long_address(self):
        """Test very long address"""
        filter = AddressFilter()
        long_addr = "0x" + "A" * 1000
        filter.add_to_whitelist(long_addr)
        assert filter.is_whitelisted(long_addr)

    def test_special_characters_in_address(self):
        """Test special characters in address"""
        filter = AddressFilter()
        filter.add_to_whitelist("0xAB$CD")
        assert filter.check_address("0xAB$CD") is True

    def test_large_blacklist(self):
        """Test with large blacklist"""
        filter = AddressFilter()
        for i in range(1000):
            filter.add_to_blacklist(f"0xBAD{i}")

        assert len(filter.blacklist) == 1000
        assert filter.check_address("0xBAD500") is False
        assert filter.check_address("0xGOOD") is True


@pytest.mark.security
class TestRealWorldScenarios:
    """Test real-world usage scenarios"""

    def test_exchange_address_filtering(self):
        """Test exchange address filtering scenario"""
        filter = AddressFilter(enable_whitelist=False)

        # Blacklist known scam addresses
        scam_addresses = ["0xSCAM1", "0xSCAM2", "0xSCAM3"]
        for addr in scam_addresses:
            filter.add_to_blacklist(addr)

        # Normal addresses allowed
        assert filter.check_address("0xUSER123") is True

        # Scam addresses blocked
        assert filter.check_address("0xSCAM1") is False

    def test_corporate_wallet_whitelist(self):
        """Test corporate wallet whitelist scenario"""
        filter = AddressFilter(enable_whitelist=True)

        # Only approved wallets can transact
        approved_wallets = ["0xCORPWALLET1", "0xCORPWALLET2"]
        for wallet in approved_wallets:
            filter.add_to_whitelist(wallet)

        # Approved wallets allowed
        assert filter.check_address("0xCORPWALLET1") is True

        # Non-approved wallets denied
        assert filter.check_address("0xEMPLOYEEWALLET") is False

    def test_aml_compliance_scenario(self):
        """Test AML compliance scenario"""
        filter = AddressFilter(enable_whitelist=False)

        # Blacklist sanctioned addresses
        sanctioned = ["0xSANCTIONED1", "0xSANCTIONED2"]
        for addr in sanctioned:
            filter.add_to_blacklist(addr)

        # Regular addresses pass compliance
        assert filter.check_address("0xREGULARUSER") is True

        # Sanctioned addresses fail compliance
        assert filter.check_address("0xSANCTIONED1") is False

    def test_bridge_relay_scenario(self):
        """Test bridge relay whitelist scenario"""
        filter = AddressFilter(enable_whitelist=True)

        # Only approved relayers can bridge
        relayers = ["0xRELAYER_A", "0xRELAYER_B", "0xRELAYER_C"]
        for relayer in relayers:
            filter.add_to_whitelist(relayer)

        # Approved relayers can bridge
        assert filter.check_address("0xRELAYER_A") is True

        # Random addresses cannot bridge
        assert filter.check_address("0xRANDOM") is False

    def test_emergency_blacklist_update(self):
        """Test emergency blacklist update scenario"""
        filter = AddressFilter(enable_whitelist=False)

        # Compromised address discovered
        compromised = "0xCOMPROMISED"

        # Initially allowed
        assert filter.check_address(compromised) is True

        # Emergency blacklist
        filter.add_to_blacklist(compromised)

        # Now blocked
        assert filter.check_address(compromised) is False

    def test_temporary_blacklist(self):
        """Test temporary blacklist scenario"""
        filter = AddressFilter()

        # Temporarily block suspicious address
        suspicious = "0xSUSPICIOUS"
        filter.add_to_blacklist(suspicious)
        assert filter.check_address(suspicious) is False

        # After investigation, remove from blacklist
        filter.remove_from_blacklist(suspicious)
        assert filter.check_address(suspicious) is True

    def test_migration_scenario(self):
        """Test migration from blacklist-only to whitelist mode"""
        filter = AddressFilter(enable_whitelist=False)

        # Initially blacklist-only
        filter.add_to_blacklist("0xBAD")
        assert filter.check_address("0xGOOD") is True

        # Migrate to whitelist mode
        filter.enable_whitelist = True
        approved_addresses = ["0xGOOD1", "0xGOOD2"]
        for addr in approved_addresses:
            filter.add_to_whitelist(addr)

        # Now only whitelisted addresses allowed
        assert filter.check_address("0xGOOD1") is True
        assert filter.check_address("0xGOOD") is False
        assert filter.check_address("0xBAD") is False


@pytest.mark.security
class TestMultipleFilters:
    """Test scenarios with multiple address filters"""

    def test_separate_filters_independent(self):
        """Test that separate filters are independent"""
        filter1 = AddressFilter()
        filter2 = AddressFilter()

        filter1.add_to_blacklist("0xBAD")
        assert "0xBAD" in filter1.blacklist
        assert "0xBAD" not in filter2.blacklist

    def test_layered_filtering(self):
        """Test layered filtering approach"""
        # First layer: blacklist
        blacklist_filter = AddressFilter(enable_whitelist=False)
        blacklist_filter.add_to_blacklist("0xBAD")

        # Second layer: whitelist
        whitelist_filter = AddressFilter(enable_whitelist=True)
        whitelist_filter.add_to_whitelist("0xGOOD")

        address = "0xGOOD"

        # Must pass both layers
        passes_blacklist = blacklist_filter.check_address(address)
        passes_whitelist = whitelist_filter.check_address(address)

        assert passes_blacklist and passes_whitelist
