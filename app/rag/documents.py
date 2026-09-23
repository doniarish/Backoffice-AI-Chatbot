"""
app/rag/documents.py
--------------------
Fictional sample documents for the RAG pipeline demo.
These represent generic FAQ content for a recycling pickup platform.

IMPORTANT: All content is entirely fictional.
           Do NOT use real company data, credentials, or proprietary content.
"""

from typing import List, Dict

# Each document has:
#   - id       : unique identifier
#   - question : the typical user query this document answers
#   - answer   : the knowledge base answer
#   - category : topic area for filtering

SAMPLE_DOCUMENTS: List[Dict[str, str]] = [
    {
        "id": "faq-001",
        "question": "How do I schedule a pickup request?",
        "answer": (
            "To schedule a pickup, open the app and tap 'New Request'. "
            "Select your material category (e.g., Aluminium, Plastic, Paper), "
            "enter the estimated weight, and choose a preferred date and time. "
            "A collector will be assigned and you will receive a confirmation notification."
        ),
        "category": "pickup",
    },
    {
        "id": "faq-002",
        "question": "What materials are accepted for recycling?",
        "answer": (
            "We currently accept the following recyclable materials: "
            "Aluminium, Copper, Plastic (PET & HDPE), Paper & Cardboard, "
            "Steel, and Glass. Hazardous materials, batteries, and electronics "
            "are not accepted through standard pickup requests."
        ),
        "category": "materials",
    },
    {
        "id": "faq-003",
        "question": "How do reward points work?",
        "answer": (
            "You earn reward points for every completed pickup. "
            "The points are calculated based on the material type and weight collected. "
            "You can redeem points through partner stores or convert them to cash credits. "
            "Sign-up bonuses and referral bonuses are also credited automatically."
        ),
        "category": "rewards",
    },
    {
        "id": "faq-004",
        "question": "How can I redeem my reward points?",
        "answer": (
            "Visit the 'Rewards' section in the app. "
            "You can redeem points at any partner retail store using the in-app QR voucher, "
            "or request a cash transfer once you reach the minimum threshold of 500 points. "
            "Redemption processing takes 1-3 business days."
        ),
        "category": "rewards",
    },
    {
        "id": "faq-005",
        "question": "What happens if my collector does not show up?",
        "answer": (
            "If your assigned collector has not arrived within 30 minutes of the scheduled time, "
            "you can report a delay through the app. The system will either reassign a new collector "
            "or allow you to reschedule at no penalty. Repeated no-shows by collectors are tracked "
            "for quality assurance."
        ),
        "category": "pickup",
    },
    {
        "id": "faq-006",
        "question": "How do I cancel a scheduled pickup?",
        "answer": (
            "You can cancel a pickup request up to 2 hours before the scheduled time "
            "through the app without any penalty. Cancellations made within 2 hours may "
            "result in a temporary suspension of request privileges for 24 hours. "
            "To cancel, go to 'My Requests' and select 'Cancel Request'."
        ),
        "category": "pickup",
    },
    {
        "id": "faq-007",
        "question": "How are reward points calculated per material?",
        "answer": (
            "Points are awarded per kilogram of material collected: "
            "Aluminium: 20 pts/kg, Copper: 25 pts/kg, Plastic: 10 pts/kg, "
            "Paper: 5 pts/kg, Steel: 15 pts/kg, Glass: 8 pts/kg. "
            "A bonus multiplier of 1.5x applies on weekends and platform promotion events."
        ),
        "category": "rewards",
    },
    {
        "id": "faq-008",
        "question": "Can corporate accounts request bulk pickups?",
        "answer": (
            "Yes. Corporate accounts have access to scheduled bulk pickup contracts. "
            "Contact our operations team to arrange recurring weekly or monthly pickups "
            "for large quantities (above 100 kg per visit). "
            "Bulk pickups receive a dedicated collector and priority scheduling."
        ),
        "category": "corporate",
    },
    {
        "id": "faq-009",
        "question": "Is there a minimum weight for a pickup request?",
        "answer": (
            "Yes, the minimum accepted weight per request is 2 kg. "
            "Requests below this threshold will be flagged for review and may not "
            "be dispatched during peak periods. Combine materials from multiple categories "
            "to meet the minimum requirement."
        ),
        "category": "pickup",
    },
    {
        "id": "faq-010",
        "question": "What is the service coverage area?",
        "answer": (
            "Our platform currently operates in Greenville, Maplewood, and Lakeside districts. "
            "Coverage is expanding quarterly. To check if your specific zone is serviced, "
            "enter your address in the app's coverage checker under 'Settings > Service Area'."
        ),
        "category": "coverage",
    },
    {
        "id": "faq-011",
        "question": "How long does it take to complete a pickup after scheduling?",
        "answer": (
            "Most pickups are completed within 4-6 hours of the scheduled window. "
            "During peak hours (8 AM - 11 AM), expect up to 8 hours. "
            "You will receive real-time status updates via push notifications as the collector "
            "approaches and when the pickup is verified."
        ),
        "category": "pickup",
    },
    {
        "id": "faq-012",
        "question": "How do I track my collector in real time?",
        "answer": (
            "Once a collector accepts your request, a live tracking map appears in the app. "
            "You can see the collector's current location, estimated time of arrival (ETA), "
            "and distance from your pickup point. Tracking is available from acceptance until "
            "pickup confirmation."
        ),
        "category": "pickup",
    },
    {
        "id": "faq-013",
        "question": "What is the referral program?",
        "answer": (
            "Share your unique referral code with friends or businesses. "
            "When a referred user completes their first pickup, you earn 50 referral points "
            "and the new user receives a 100-point welcome bonus. "
            "There is no limit to the number of referrals you can make."
        ),
        "category": "rewards",
    },
    {
        "id": "faq-014",
        "question": "How do I update my account profile?",
        "answer": (
            "Go to 'Profile' in the app menu. You can update your display name, phone number, "
            "and service address. For security reasons, changes to email or national ID require "
            "identity verification through the support channel."
        ),
        "category": "account",
    },
    {
        "id": "faq-015",
        "question": "كيف يمكنني جدولة طلب استلام؟",
        "answer": (
            "لجدولة طلب استلام، افتح التطبيق واضغط على 'طلب جديد'. "
            "اختر فئة المواد (مثل الألومنيوم أو البلاستيك أو الورق)، "
            "أدخل الوزن التقديري، واختر التاريخ والوقت المناسبين. "
            "سيتم تعيين جامع وستتلقى إشعاراً بالتأكيد."
        ),
        "category": "pickup",
    },
    {
        "id": "faq-016",
        "question": "ما هي نقاط المكافآت وكيف أستخدمها؟",
        "answer": (
            "تحصل على نقاط مكافأة مقابل كل عملية استلام مكتملة. "
            "يمكنك استبدال النقاط في المتاجر الشريكة أو تحويلها إلى رصيد نقدي. "
            "يتم احتساب النقاط بناءً على نوع المواد ووزنها."
        ),
        "category": "rewards",
    },
    {
        "id": "faq-017",
        "question": "How do I contact customer support?",
        "answer": (
            "You can reach our support team through the 'Help' section in the app, "
            "which offers live chat (8 AM - 8 PM), email support (response within 24 hours), "
            "and an automated FAQ chatbot available 24/7. "
            "For urgent pickup issues, use the in-app 'Emergency Report' button."
        ),
        "category": "account",
    },
    {
        "id": "faq-018",
        "question": "What is the difference between Domestic and Corporate accounts?",
        "answer": (
            "Domestic accounts are for individual households with occasional recycling needs. "
            "Corporate accounts are for businesses with regular, higher-volume material collection. "
            "Corporate accounts offer bulk scheduling, priority dispatch, and monthly invoice summaries. "
            "You can upgrade from Domestic to Corporate at any time via account settings."
        ),
        "category": "account",
    },
]


def get_all_documents() -> List[Dict[str, str]]:
    """Return all sample FAQ documents."""
    return SAMPLE_DOCUMENTS


def get_documents_by_category(category: str) -> List[Dict[str, str]]:
    """Return documents filtered by category."""
    return [doc for doc in SAMPLE_DOCUMENTS if doc["category"] == category]

