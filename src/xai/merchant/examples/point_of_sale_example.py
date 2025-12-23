#!/usr/bin/env python3
"""
Point of Sale (POS) Example

Demonstrates a complete point-of-sale integration using XAI payments.
This example shows how to:
- Create payment requests
- Generate QR codes for display
- Monitor payment status
- Handle payment confirmations
- Process receipts

Run: python3 point_of_sale_example.py
"""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from xai.merchant import MerchantPaymentProcessor, WebhookEvent
from xai.mobile.qr_transactions import QRCODE_AVAILABLE, TransactionQRGenerator

if QRCODE_AVAILABLE:
    from io import BytesIO

    from PIL import Image


def display_qr_code(qr_bytes: bytes):
    """Display QR code (or save to file in production)."""
    if not QRCODE_AVAILABLE:
        print("QR code library not available")
        return

    img = Image.open(BytesIO(qr_bytes))

    # In production, display on POS terminal screen
    # For demo, save to file
    filename = "/tmp/xai_payment_qr.png"
    img.save(filename)
    print(f"QR code saved to: {filename}")

    # Uncomment to display (requires X11/display):
    # img.show()


def print_receipt(payment_request, items):
    """Print receipt for completed payment."""
    print("\n" + "=" * 40)
    print("         RECEIPT")
    print("=" * 40)
    print(f"Payment ID: {payment_request.request_id[:8]}...")
    print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 40)

    for item_name, item_price in items:
        print(f"{item_name:<30} ${item_price:>6.2f}")

    print("-" * 40)
    print(f"{'TOTAL':<30} ${payment_request.amount:>6.2f}")
    print("-" * 40)
    print(f"Paid with: XAI")
    print(f"TX: {payment_request.paid_txid}")
    print(f"Confirmations: {payment_request.confirmations}")
    print("=" * 40)
    print("      Thank you for your purchase!")
    print("=" * 40 + "\n")


def process_sale(processor, items, merchant_address):
    """
    Process a sale with QR code payment.

    Args:
        processor: MerchantPaymentProcessor instance
        items: List of (item_name, price) tuples
        merchant_address: XAI address to receive payment

    Returns:
        True if sale completed, False if cancelled/expired
    """
    # Calculate total
    total = sum(price for _, price in items)

    print("\n" + "=" * 50)
    print("NEW SALE")
    print("=" * 50)

    for item_name, item_price in items:
        print(f"  {item_name}: ${item_price:.2f}")

    print("-" * 50)
    print(f"  TOTAL: ${total:.2f}")
    print("=" * 50 + "\n")

    # Create payment request
    item_list = ", ".join(name for name, _ in items)
    payment = processor.create_payment_request(
        address=merchant_address,
        amount=total,
        memo=f"Purchase: {item_list}",
        expiry_minutes=5  # 5 minute timeout
    )

    print(f"Payment request created: {payment.request_id}")
    print(f"Amount: {payment.amount} XAI")
    print(f"Expires in: 5 minutes\n")

    # Generate QR code
    if QRCODE_AVAILABLE:
        qr_bytes = TransactionQRGenerator.generate_payment_request_qr(
            address=payment.address,
            amount=payment.amount,
            message=payment.memo,
            return_format="bytes"
        )

        print("Displaying QR code for customer to scan...")
        display_qr_code(qr_bytes)
    else:
        print("QR code generation not available (install qrcode[pil])")
        print(f"Payment address: {payment.address}")
        print(f"Amount: {payment.amount} XAI")

    print("\nWaiting for payment...")
    print("(In production, monitor blockchain for incoming transaction)\n")

    # Monitor payment status
    # In production, this would be triggered by blockchain events
    # For demo, we show the polling approach
    start_time = time.time()
    last_status = None

    while time.time() - start_time < 300:  # 5 minutes
        updated = processor.get_payment_request(payment.request_id)

        # Check if status changed
        if updated.status != last_status:
            last_status = updated.status

            if updated.status.value == "paid":
                print(f"\n✓ Payment received!")
                print(f"  Transaction ID: {updated.paid_txid}")
                print(f"  Confirmations: {updated.confirmations}/{updated.required_confirmations}")

                # Wait for confirmations
                print("\nWaiting for confirmations...")
                while not updated.is_confirmed():
                    time.sleep(5)
                    updated = processor.get_payment_request(payment.request_id)
                    print(f"  Confirmations: {updated.confirmations}/{updated.required_confirmations}")

                print("\n✓ Payment fully confirmed!")
                print_receipt(updated, items)
                return True

            elif updated.status.value == "expired":
                print("\n✗ Payment request expired")
                return False

        # Show timeout countdown
        remaining = 300 - int(time.time() - start_time)
        if remaining % 30 == 0:  # Update every 30 seconds
            print(f"  Time remaining: {remaining}s")

        time.sleep(2)

    # Timeout
    print("\n✗ Payment timeout - cancelling request")
    processor.cancel_payment_request(payment.request_id)
    return False


def main():
    """Main POS application."""
    print("\n" + "=" * 50)
    print("XAI POINT OF SALE SYSTEM")
    print("=" * 50 + "\n")

    # Initialize payment processor
    processor = MerchantPaymentProcessor(
        merchant_id="DEMO_STORE_001",
        default_expiry_minutes=15,
        required_confirmations=6
    )

    # Set up event handlers
    def on_payment_confirmed(payment_request):
        print(f"\n[EVENT] Payment confirmed: {payment_request.request_id}")

    processor.on_event(WebhookEvent.PAYMENT_CONFIRMED, on_payment_confirmed)

    # Merchant's XAI address (in production, load from config)
    merchant_address = "XAI1234567890abcdef1234567890abcdef12345678"

    # Demo: Process a few sales
    sales = [
        [("Cappuccino", 4.50), ("Croissant", 3.00)],
        [("Latte", 4.00), ("Muffin", 2.50), ("Cookie", 1.50)],
        [("Espresso", 3.00)],
    ]

    print("Welcome to the XAI POS Demo!")
    print("This demo will simulate several sales.\n")
    print("Note: Since this is a demo without a live blockchain,")
    print("payments will timeout. In production, payments would")
    print("be detected automatically via blockchain monitoring.\n")

    input("Press Enter to start demo sales...")

    completed = 0
    for i, items in enumerate(sales, 1):
        print(f"\n\n{'='*50}")
        print(f"SALE {i} OF {len(sales)}")
        print(f"{'='*50}")

        # In production, you would wait for the payment to actually arrive
        # For this demo, we show the workflow but timeout occurs
        success = process_sale(processor, items, merchant_address)

        if success:
            completed += 1
            print(f"\n✓ Sale {i} completed successfully")
        else:
            print(f"\n✗ Sale {i} cancelled")

        if i < len(sales):
            input("\nPress Enter for next sale...")

    # Show statistics
    print("\n\n" + "=" * 50)
    print("SESSION SUMMARY")
    print("=" * 50)

    stats = processor.get_statistics()
    print(f"Total sales: {stats['payment_requests']['total']}")
    print(f"Completed: {stats['payment_requests']['paid']}")
    print(f"Cancelled: {stats['payment_requests']['cancelled']}")
    print(f"Expired: {stats['payment_requests']['expired']}")
    print("=" * 50 + "\n")

    print("\nDemo complete!")
    print("\nIn production, you would:")
    print("  1. Monitor blockchain for incoming transactions")
    print("  2. Use processor.update_payment_status() when transactions arrive")
    print("  3. Set up webhook notifications for payment events")
    print("  4. Implement proper receipt printing")
    print("  5. Integrate with your POS/inventory system")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(0)
