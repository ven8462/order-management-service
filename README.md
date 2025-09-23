# Order-Management-Service
Order Management Service for E-commerce Platform

### Set up steps

1. Clone the repo
2. Install Dependencies by running `poetry install`
3. To add new dependencies run `poetry add (name of dependency)`
4. To run tests run `poetry run pytest`
5. When committing changes please use the github UI so that ruff works


This is the Order Management Service for the E-commerce Platform System Design Workshop. Its core responsibility is to manage the entire lifecycle of an order, from creation to confirmation or failure.

This service is built with Python, FastAPI, and PostgreSQL. It communicates asynchronously with other services via Kafka, using a **Choreographic Saga pattern** to ensure data consistency across the distributed system.

## Table of Contents

1.  [Architecture](#architecture)
2.  [Key Design Patterns Implemented](#key-design-patterns-implemented)
3.  [Prerequisites](#prerequisites)
4.  [Getting Started](#getting-started)
5.  [API Endpoints](#api-endpoints)
6.  [Service Contracts (Kafka Topics)](#service-contracts-kafka-topics)
7.  [Monitoring & Health](#monitoring--health)
8.  [Environment Variables](#environment-variables)

## Architecture

This service is a central component of an event-driven microservices architecture. It does **not** make synchronous REST API calls to other services. Instead, it publishes events to Kafka and listens for events from other services.

This design choice ensures high resilience and loose coupling. If a downstream service (like Payments) is temporarily unavailable, this service can still accept new orders, which will be processed once the other service comes back online.

### Order Creation Saga Flow

The order lifecycle is managed by a **Choreographic Saga**, where each service reacts to events from others.

**Success Flow:**
1.  **Order Service**: `POST /orders` endpoint is called. The order is created in the database with `PENDING` status.
2.  **Order Service**: Publishes `process_payment_request` event to Kafka.
3.  **Payment Service**: Consumes the event, processes the payment, and publishes a `payment_successful` event.
4.  **Order Service**: Consumes `payment_successful`, updates the order status to `INVENTORY_RESERVING`, and publishes a `reserve_inventory_request` event.
5.  **Inventory Service**: Consumes the event, reserves stock, and publishes an `inventory_reserved` event.
6.  **Order Service**: Consumes `inventory_reserved`, updates the order status to `CONFIRMED`, and publishes an `order_confirmed` event.

**Failure & Compensation Flow (Example):**
1.  ...Steps 1-4 happen...
2.  **Inventory Service**: Consumes `reserve_inventory_request`, finds no stock, and publishes an `inventory_reservation_failed` event.
3.  **Order Service**: Consumes `inventory_reservation_failed`, updates the order status to `FAILED`, and publishes a `refund_payment_request` **compensation event**.
4.  **Payment Service**: Consumes the compensation event and refunds the user's payment.

## Key Design Patterns Implemented

This service explicitly implements several key patterns required by the workshop.

*   **Fault Tolerance:**
    *   **Saga Pattern**: Manages distributed transactions as described above.
    *   **Circuit Breaker**: The Kafka producer (`producer.py`) is wrapped in a `pybreaker` circuit breaker. If Kafka is unavailable, the breaker will trip, allowing API calls to fail instantly instead of blocking, which preserves system resources.
    *   **Dead-Letter Queue (DLQ)**: The Kafka consumer (`consumer.py`) will move messages that repeatedly cause processing errors to a `{topic}_dlq` topic. This prevents a "poison pill" message from blocking the entire consumer.

*   **Scalability:**
    *   **Asynchronous Processing**: All inter-service communication is asynchronous via Kafka, allowing the API to remain fast and responsive under load.
    *   **CQRS (Command and Query Responsibility Segregation)**: The service code separates "Commands" (creating/updating data, e.g., `crud.create_order`) from "Queries" (reading data, e.g., `crud.get_order`). This structure makes it easy to later introduce read replicas for query-heavy endpoints.
    *   **Sharding Strategy**: The data models consistently use `user_id`, making a `user_id`-based database sharding strategy viable for future horizontal scaling.

## Prerequisites

*   **Docker Desktop** (or Docker Engine + Docker Compose for Linux)