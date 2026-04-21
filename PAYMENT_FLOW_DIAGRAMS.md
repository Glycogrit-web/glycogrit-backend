# Payment Integration - Visual Flow Diagrams

This document contains Mermaid diagrams to visualize the payment integration architecture and flows.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Payment Flow - Physical Rewards](#payment-flow---physical-rewards)
3. [Payment Flow - E-Certificate](#payment-flow---e-certificate)
4. [Refund Flow](#refund-flow)
5. [Gateway Abstraction Layer](#gateway-abstraction-layer)
6. [Database Schema](#database-schema)

---

## Architecture Overview

```mermaid
graph TB
    subgraph "Frontend"
        UI[User Interface]
        RZP[Razorpay Checkout]
    end

    subgraph "API Layer"
        API1[POST /order/create]
        API2[POST /verify]
        API3[POST /refund]
    end

    subgraph "Service Layer"
        PS[Payment Service]
        RS[Registration Service]
    end

    subgraph "Gateway Abstraction"
        Factory[Payment Gateway Factory]
        Interface[PaymentGatewayInterface]
        RazorpayGW[Razorpay Gateway]
        StripeGW[Stripe Gateway - Future]
        PayPalGW[PayPal Gateway - Future]
    end

    subgraph "External Services"
        RazorpayAPI[Razorpay API]
        StripeAPI[Stripe API - Future]
    end

    subgraph "Database"
        EventsDB[(Events Table)]
        PaymentsDB[(Payments Table)]
        RegistrationsDB[(Registrations Table)]
    end

    UI --> API1
    UI --> API2
    UI --> API3

    API1 --> PS
    API2 --> PS
    API3 --> PS

    PS --> Factory
    PS --> RS

    Factory --> Interface
    Interface --> RazorpayGW
    Interface --> StripeGW
    Interface --> PayPalGW

    RazorpayGW --> RazorpayAPI
    StripeGW --> StripeAPI

    PS --> PaymentsDB
    RS --> RegistrationsDB
    RS --> EventsDB

    RZP --> UI

    style Interface fill:#f9f,stroke:#333,stroke-width:4px
    style Factory fill:#bbf,stroke:#333,stroke-width:2px
    style RazorpayGW fill:#bfb,stroke:#333,stroke-width:2px
    style StripeGW fill:#fbb,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style PayPalGW fill:#fbb,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
```

---

## Payment Flow - Physical Rewards

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant PaymentService
    participant Gateway as Payment Gateway<br/>(Razorpay/Stripe)
    participant RegistrationService
    participant Database

    User->>Frontend: Register for Event
    Frontend->>API: POST /events/{id}/register
    API->>RegistrationService: create_registration()

    RegistrationService->>Database: Check event.certificate_type
    Database-->>RegistrationService: certificate_type='physical'

    RegistrationService->>Database: Create Registration<br/>status='pending'
    Database-->>RegistrationService: Registration Created
    RegistrationService-->>API: Registration (pending)
    API-->>Frontend: {registration_id, status: 'pending'}

    Note over Frontend: User needs to pay

    Frontend->>API: POST /payments/order/create<br/>{registration_id, gateway: 'razorpay'}
    API->>PaymentService: create_payment_order()

    PaymentService->>Gateway: create_order(amount, currency)
    Gateway-->>PaymentService: {order_id, amount, currency}

    PaymentService->>Database: Create Payment<br/>status='pending'
    Database-->>PaymentService: Payment Created

    PaymentService-->>API: {order_id, amount, gateway, payment}
    API-->>Frontend: Order Details

    Frontend->>User: Show Payment Gateway UI
    User->>Gateway: Complete Payment
    Gateway-->>User: Payment Success

    Gateway-->>Frontend: {order_id, payment_id, signature}

    Frontend->>API: POST /payments/verify<br/>{order_id, payment_id, signature}
    API->>PaymentService: verify_payment()

    PaymentService->>Gateway: verify_signature()
    Gateway-->>PaymentService: Signature Valid ✓

    PaymentService->>Database: Update Payment<br/>status='completed'
    PaymentService->>Database: Update Registration<br/>status='confirmed'

    Database-->>PaymentService: Updated
    PaymentService-->>API: Payment Verified
    API-->>Frontend: Success
    Frontend->>User: Registration Confirmed! 🎉

    Note over User,Database: Registration Complete with Payment
```

---

## Payment Flow - E-Certificate

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant RegistrationService
    participant Database

    User->>Frontend: Register for Event
    Frontend->>API: POST /events/{id}/register
    API->>RegistrationService: create_registration()

    RegistrationService->>Database: Check event.certificate_type
    Database-->>RegistrationService: certificate_type='e-certificate'

    Note over RegistrationService: No payment required!

    RegistrationService->>Database: Create Registration<br/>status='confirmed'
    Database-->>RegistrationService: Registration Created

    RegistrationService-->>API: Registration (confirmed)
    API-->>Frontend: {registration_id, status: 'confirmed'}
    Frontend->>User: Registration Confirmed! 🎉

    Note over User,Database: Instant confirmation - No payment needed
```

---

## Refund Flow

```mermaid
sequenceDiagram
    participant User/Admin
    participant Frontend
    participant API
    participant PaymentService
    participant Gateway as Payment Gateway
    participant Database

    User/Admin->>Frontend: Request Refund
    Frontend->>API: POST /payments/{id}/refund<br/>{amount, reason}
    API->>PaymentService: create_refund()

    PaymentService->>Database: Get Payment Details
    Database-->>PaymentService: Payment (status='completed')

    PaymentService->>PaymentService: Validate refund eligibility

    PaymentService->>Gateway: create_refund(payment_id, amount)
    Gateway-->>PaymentService: {refund_id, amount, status}

    PaymentService->>Database: Update Payment<br/>status='refunded'<br/>refund_id, refund_amount

    PaymentService->>Database: Update Registration<br/>status='cancelled'

    Database-->>PaymentService: Updated
    PaymentService-->>API: Refund Processed
    API-->>Frontend: Success
    Frontend->>User/Admin: Refund Initiated ✓

    Note over Gateway: Refund will be processed<br/>within 5-7 business days
```

---

## Gateway Abstraction Layer

```mermaid
classDiagram
    class PaymentGatewayInterface {
        <<interface>>
        +create_order(amount, currency, receipt, notes)
        +verify_payment_signature(order_id, payment_id, signature)
        +verify_webhook_signature(payload, signature)
        +fetch_payment(payment_id)
        +create_refund(payment_id, amount, notes)
        +fetch_refund(payment_id, refund_id)
        +get_gateway_name()
        +normalize_order_response(gateway_response)
        +normalize_refund_response(gateway_response)
    }

    class RazorpayGateway {
        -client: razorpay.Client
        +__init__()
        +get_gateway_name() "razorpay"
        +create_order()
        +verify_payment_signature()
        +verify_webhook_signature()
        +fetch_payment()
        +create_refund()
        +fetch_refund()
        +normalize_order_response()
        +normalize_refund_response()
    }

    class StripeGateway {
        -client: stripe.Client
        +__init__()
        +get_gateway_name() "stripe"
        +create_order()
        +verify_payment_signature()
        +verify_webhook_signature()
        +fetch_payment()
        +create_refund()
        +fetch_refund()
        +normalize_order_response()
        +normalize_refund_response()
    }

    class PaymentGatewayFactory {
        -_instances: Dict
        +create_gateway(provider) Gateway
        +get_available_providers() List
        +clear_cache()
    }

    class PaymentService {
        -repository: PaymentRepository
        -registration_repository: RegistrationRepository
        +create_payment_order(registration_id, user_id, gateway)
        +verify_payment(order_id, payment_id, signature, gateway)
        +create_refund(payment_id, amount, reason)
    }

    PaymentGatewayInterface <|.. RazorpayGateway : implements
    PaymentGatewayInterface <|.. StripeGateway : implements
    PaymentGatewayFactory --> PaymentGatewayInterface : creates
    PaymentService --> PaymentGatewayFactory : uses
    PaymentService --> RazorpayGateway : via factory
    PaymentService --> StripeGateway : via factory

    style PaymentGatewayInterface fill:#f9f,stroke:#333,stroke-width:4px
    style PaymentGatewayFactory fill:#bbf,stroke:#333,stroke-width:2px
    style RazorpayGateway fill:#bfb,stroke:#333,stroke-width:2px
    style StripeGateway fill:#fbb,stroke:#333,stroke-width:2px
```

---

## Database Schema

```mermaid
erDiagram
    EVENTS ||--o{ REGISTRATIONS : "has many"
    EVENTS ||--o{ EVENT_CATEGORIES : "has many"
    USERS ||--o{ REGISTRATIONS : "creates"
    USERS ||--o{ PAYMENTS : "makes"
    REGISTRATIONS ||--o{ PAYMENTS : "has"
    EVENT_CATEGORIES ||--o{ REGISTRATIONS : "selected for"

    EVENTS {
        int id PK
        string name
        string slug
        decimal registration_fee
        string certificate_type "e-certificate | physical"
        boolean requires_payment
        jsonb rewards
        string status
        timestamp created_at
    }

    REGISTRATIONS {
        int id PK
        int user_id FK
        int event_id FK
        int event_category_id FK
        string registration_number
        string status "pending | confirmed | cancelled"
        timestamp registered_at
        timestamp confirmed_at
    }

    PAYMENTS {
        int id PK
        int user_id FK
        int registration_id FK
        decimal amount
        string currency
        string status "pending | completed | failed | refunded"
        string gateway_name "razorpay | stripe | paypal"
        string gateway_order_id
        string gateway_payment_id
        string gateway_signature
        string razorpay_order_id "backward compatibility"
        string razorpay_payment_id "backward compatibility"
        string refund_id
        decimal refund_amount
        string refund_status
        timestamp initiated_at
        timestamp completed_at
        timestamp refunded_at
    }

    USERS {
        int id PK
        string email
        string name
        timestamp created_at
    }

    EVENT_CATEGORIES {
        int id PK
        int event_id FK
        string name
        decimal registration_fee
        int max_participants
    }
```

---

## Decision Flow - Payment Required?

```mermaid
flowchart TD
    Start([User Registers for Event]) --> GetEvent[Get Event Details]
    GetEvent --> CheckType{Event certificate_type?}

    CheckType -->|physical| RequirePayment[Payment Required ✓]
    CheckType -->|e-certificate| CheckFlag{requires_payment flag?}

    CheckFlag -->|true| RequirePayment
    CheckFlag -->|false| NoPayment[No Payment Required ✗]

    RequirePayment --> CreatePending[Create Registration<br/>status='pending']
    NoPayment --> CreateConfirmed[Create Registration<br/>status='confirmed']

    CreatePending --> ShowPayment[Show Payment UI]
    ShowPayment --> CreateOrder[Create Payment Order]
    CreateOrder --> GatewayCheckout[Open Gateway Checkout]
    GatewayCheckout --> UserPays{User Completes Payment?}

    UserPays -->|Yes| VerifySignature[Verify Payment Signature]
    UserPays -->|No| PaymentFailed[Payment Failed]

    VerifySignature --> SignatureValid{Signature Valid?}
    SignatureValid -->|Yes| UpdatePayment[Update Payment<br/>status='completed']
    SignatureValid -->|No| PaymentFailed

    UpdatePayment --> UpdateReg[Update Registration<br/>status='confirmed']
    UpdateReg --> Success([Registration Confirmed! 🎉])

    CreateConfirmed --> Success
    PaymentFailed --> Failed([Registration Failed ❌])

    style RequirePayment fill:#ffb,stroke:#333,stroke-width:2px
    style NoPayment fill:#bfb,stroke:#333,stroke-width:2px
    style Success fill:#bfb,stroke:#333,stroke-width:3px
    style Failed fill:#fbb,stroke:#333,stroke-width:3px
```

---

## API Endpoint Flow

```mermaid
graph LR
    subgraph "Payment Endpoints"
        A[POST /order/create] -->|Creates Order| B[Payment Service]
        C[POST /verify] -->|Verifies Payment| B
        D[POST /refund] -->|Processes Refund| B
    end

    subgraph "Gateway Selection"
        B --> E{Gateway Factory}
        E -->|gateway='razorpay'| F[Razorpay Gateway]
        E -->|gateway='stripe'| G[Stripe Gateway]
        E -->|default| F
    end

    subgraph "Gateway Operations"
        F --> H[Razorpay API]
        G --> I[Stripe API]
    end

    subgraph "Database Updates"
        B --> J[(Payments Table)]
        B --> K[(Registrations Table)]
    end

    style E fill:#bbf,stroke:#333,stroke-width:2px
    style F fill:#bfb,stroke:#333,stroke-width:2px
    style G fill:#fbb,stroke:#333,stroke-width:2px
```

---

## State Diagram - Registration & Payment

```mermaid
stateDiagram-v2
    [*] --> Draft: Event Created
    Draft --> Published: Admin Publishes

    Published --> RegistrationPending: User Registers<br/>(Payment Required)
    Published --> RegistrationConfirmed: User Registers<br/>(No Payment Required)

    RegistrationPending --> PaymentInitiated: Create Payment Order
    PaymentInitiated --> PaymentCompleted: Payment Success
    PaymentInitiated --> PaymentFailed: Payment Failure

    PaymentCompleted --> RegistrationConfirmed: Auto-confirm
    PaymentFailed --> RegistrationCancelled: Timeout/Cancel

    RegistrationConfirmed --> RefundRequested: User/Admin Requests
    RefundRequested --> RefundProcessed: Refund Success
    RefundProcessed --> RegistrationCancelled: Final State

    RegistrationCancelled --> [*]
    RegistrationConfirmed --> [*]: Event Complete

    note right of RegistrationPending
        Status: pending
        Waiting for payment
    end note

    note right of RegistrationConfirmed
        Status: confirmed
        User can participate
    end note

    note right of PaymentCompleted
        Payment: completed
        Registration: confirmed
    end note
```

---

## How to Use These Diagrams

### View on Mermaid Live Editor
1. Copy any diagram code block
2. Visit [Mermaid Live Editor](https://mermaid.live)
3. Paste the code
4. View and export the diagram

### View in GitHub/GitLab
These diagrams render automatically in:
- GitHub README.md files
- GitLab documentation
- VS Code with Mermaid extension

### Export Options
From Mermaid Live Editor, you can export as:
- PNG
- SVG
- PDF
- Markdown with embedded SVG

---

## Key Insights from Diagrams

1. **Modular Architecture**: Payment gateway is abstracted, making it easy to add new providers
2. **Smart Flow**: System automatically decides if payment is needed based on event configuration
3. **State Management**: Clear state transitions for registrations and payments
4. **Provider Agnostic**: Same flow works for Razorpay, Stripe, or any future gateway
5. **Backward Compatible**: Old Razorpay-specific fields maintained alongside generic fields

---

**Generated:** April 21, 2026
**For:** GlycoGrit Backend Payment Integration
**Version:** 1.0.0
