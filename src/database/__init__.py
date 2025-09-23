def get_order_details(order_id: str):
    """Simulates retrieving order details from a database."""
    # Placeholder implementation
    # This is a mock function for the test, normally this would connect to a real database
    if order_id == "abc123":
        return {
            "orderId": "abc123",
            "status": "SHIPPED",
            "totalAmount": 120.00
        }
    return None

def save_order_to_db(order_data: dict, transaction_id: str):
    """Simulates saving the order to the database."""
    # Placeholder implementation
    # This function is currently a mock for the tests
    print(f"Saving order {order_data} with transaction ID {transaction_id}")
    return {"orderId": "mock-order-123", "status": "CONFIRMED"}