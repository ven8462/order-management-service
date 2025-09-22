# fault_tolerance.py
import random
import requests
from retrying import retry

#  define a retry policy
@retry(wait_exponential_multiplier=1000, wait_exponential_max=10000, stop_max_attempt_number=5)
def call_payment_service():
    """
    Simulates a call to the Payment Service that might fail.
    This function will be retried up to 5 times with exponential backoff.
    """
    print("Attempting to call Payment Service...")
    
    # Simulate a network error or a service being down temporarily
    if random.random() < 0.7:  # 70% chance of failure
        raise requests.exceptions.RequestException("Payment service is temporarily unavailable.")
    
    print("Payment service call succeeded!")
    return {"status": "payment_successful"}

#  Order Service logic
if __name__ == "__main__":
    try:
        print("\nStarting payment processing...")
        result = call_payment_service()
        print(f"Result: {result}")
        print("Payment processed successfully.")
    except Exception as e:
        print(f"Failed after all retries. Order processing cannot continue due to: {e}")