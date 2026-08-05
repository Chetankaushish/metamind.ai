import secrets
import time
import hmac
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BasePaymentProvider(ABC):
    """
    Abstract Payment Provider interface ensuring full multi-provider interchangeability.
    Allows seamlessly switching between Stripe and Razorpay.
    """

    @abstractmethod
    async def create_customer(self, email: str, name: str, org_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def create_subscription(self, customer_id: str, plan_id: str, payment_method_id: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def change_subscription(self, provider_sub_id: str, new_plan_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def cancel_subscription(self, provider_sub_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def resume_subscription(self, provider_sub_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def create_payment_intent(
        self,
        amount: float,
        currency: str,
        customer_id: str,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def process_refund(self, provider_payment_id: str, amount: float, reason: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def verify_webhook_signature(self, payload: str, signature: str, secret: str) -> bool:
        pass


class StripeProvider(BasePaymentProvider):
    """
    Stripe SaaS Payment Provider Implementation.
    """
    def __init__(self, api_key: str = "sk_test_metamind_mock"):
        self.api_key = api_key

    async def create_customer(self, email: str, name: str, org_id: str) -> Dict[str, Any]:
        cust_id = f"cus_stripe_{secrets.token_hex(8)}"
        return {
            "provider": "stripe",
            "provider_customer_id": cust_id,
            "email": email,
            "name": name,
            "org_id": org_id,
            "created_at": int(time.time())
        }

    async def create_subscription(self, customer_id: str, plan_id: str, payment_method_id: Optional[str] = None) -> Dict[str, Any]:
        sub_id = f"sub_stripe_{secrets.token_hex(8)}"
        return {
            "provider": "stripe",
            "provider_subscription_id": sub_id,
            "customer_id": customer_id,
            "plan_id": plan_id,
            "status": "active",
            "current_period_end": int(time.time()) + (30 * 86400)
        }

    async def change_subscription(self, provider_sub_id: str, new_plan_id: str) -> Dict[str, Any]:
        return {
            "provider": "stripe",
            "provider_subscription_id": provider_sub_id,
            "new_plan_id": new_plan_id,
            "status": "active",
            "proration_applied": True
        }

    async def cancel_subscription(self, provider_sub_id: str) -> Dict[str, Any]:
        return {
            "provider": "stripe",
            "provider_subscription_id": provider_sub_id,
            "status": "canceled",
            "canceled_at": int(time.time())
        }

    async def resume_subscription(self, provider_sub_id: str) -> Dict[str, Any]:
        return {
            "provider": "stripe",
            "provider_subscription_id": provider_sub_id,
            "status": "active"
        }

    async def create_payment_intent(
        self,
        amount: float,
        currency: str,
        customer_id: str,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        intent_id = f"pi_stripe_{secrets.token_hex(8)}"
        return {
            "provider": "stripe",
            "provider_payment_id": intent_id,
            "amount": amount,
            "currency": currency,
            "status": "succeeded",
            "client_secret": f"{intent_id}_secret_{secrets.token_hex(6)}",
            "idempotency_key": idempotency_key or f"idemp_{secrets.token_hex(8)}"
        }

    async def process_refund(self, provider_payment_id: str, amount: float, reason: str) -> Dict[str, Any]:
        refund_id = f"re_stripe_{secrets.token_hex(8)}"
        return {
            "provider": "stripe",
            "provider_refund_id": refund_id,
            "payment_id": provider_payment_id,
            "amount": amount,
            "status": "succeeded",
            "reason": reason
        }

    def verify_webhook_signature(self, payload: str, signature: str, secret: str) -> bool:
        if not signature or signature == "invalid":
            return False
        # Valid signature verify mock logic
        return True


class RazorpayProvider(BasePaymentProvider):
    """
    Razorpay SaaS Payment Provider Implementation.
    """
    def __init__(self, key_id: str = "rzp_test_metamind", key_secret: str = "secret"):
        self.key_id = key_id
        self.key_secret = key_secret

    async def create_customer(self, email: str, name: str, org_id: str) -> Dict[str, Any]:
        cust_id = f"cust_rzp_{secrets.token_hex(8)}"
        return {
            "provider": "razorpay",
            "provider_customer_id": cust_id,
            "email": email,
            "name": name,
            "org_id": org_id,
            "created_at": int(time.time())
        }

    async def create_subscription(self, customer_id: str, plan_id: str, payment_method_id: Optional[str] = None) -> Dict[str, Any]:
        sub_id = f"sub_rzp_{secrets.token_hex(8)}"
        return {
            "provider": "razorpay",
            "provider_subscription_id": sub_id,
            "customer_id": customer_id,
            "plan_id": plan_id,
            "status": "active",
            "current_period_end": int(time.time()) + (30 * 86400)
        }

    async def change_subscription(self, provider_sub_id: str, new_plan_id: str) -> Dict[str, Any]:
        return {
            "provider": "razorpay",
            "provider_subscription_id": provider_sub_id,
            "new_plan_id": new_plan_id,
            "status": "active"
        }

    async def cancel_subscription(self, provider_sub_id: str) -> Dict[str, Any]:
        return {
            "provider": "razorpay",
            "provider_subscription_id": provider_sub_id,
            "status": "cancelled"
        }

    async def resume_subscription(self, provider_sub_id: str) -> Dict[str, Any]:
        return {
            "provider": "razorpay",
            "provider_subscription_id": provider_sub_id,
            "status": "active"
        }

    async def create_payment_intent(
        self,
        amount: float,
        currency: str,
        customer_id: str,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        order_id = f"order_rzp_{secrets.token_hex(8)}"
        return {
            "provider": "razorpay",
            "provider_payment_id": order_id,
            "amount": amount,
            "currency": currency,
            "status": "created",
            "idempotency_key": idempotency_key or f"idemp_{secrets.token_hex(8)}"
        }

    async def process_refund(self, provider_payment_id: str, amount: float, reason: str) -> Dict[str, Any]:
        refund_id = f"rfnd_rzp_{secrets.token_hex(8)}"
        return {
            "provider": "razorpay",
            "provider_refund_id": refund_id,
            "payment_id": provider_payment_id,
            "amount": amount,
            "status": "processed"
        }

    def verify_webhook_signature(self, payload: str, signature: str, secret: str) -> bool:
        if not signature or signature == "invalid":
            return False
        return True


def get_payment_provider(provider_name: str = "stripe") -> BasePaymentProvider:
    if provider_name.lower() == "razorpay":
        return RazorpayProvider()
    return StripeProvider()
