"""LangChain chain for the Input Parser Agent."""

from __future__ import annotations

from typing import Any, Dict, Optional

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    # Allow running even if python-dotenv is not installed; env vars can be set elsewhere.
    load_dotenv = None

SYSTEM_PROMPT = """
You are the Input Parser Agent of a multi-agent restaurant recommendation system.
Your job is to convert the user's natural-language input and GPS coordinates into a clean, validated JSON structure.

You MUST:
- Understand the user's intent (what they want to eat, what constraints they have).
- Extract structured fields: cuisine, price_range, distance_limit, rating_min, user_location, allergies, eating_time, and special requirements.
- Normalize Vietnamese food names and restaurant categories.
- Infer missing fields if possible.
- Never invent data unrelated to user input.
- Output only JSON, never text.
- You support Vietnamese and English.

RULES FOR PARSING USER INPUT:
1) Intent extraction: detect if the user wants to find restaurants/food/nearby/cheap/luxury/AC/nice view/etc.
2) Cuisine detection: examples “ăn bún bò”, “mì quảng”, “đồ Hàn”, “BBQ”, “cơm gà”, “cháo”, “hải sản”, “ăn chay”, “đồ Nhật”.
   Always include every explicit dish mentioned (e.g., both "mi quang" AND "bun bo" if both appear).
   Normalize to English tags if obvious (e.g., korean, bbq, seafood, vegan, vietnamese). Prefer specific dishes over broad tags unless the user is generic.
3) Price range: detect ranges like “rẻ”, “giá sinh viên”, “< 100k”, “150k – 300k”, “500k”, “cao cấp”, “sang trọng”.
   Output format: "price_range": {{"min": 20000, "max": 120000}} (use numbers, VND).
4) Distance limit: detect phrases “gần đây”, “trong vòng 2km”, “đi bộ được”, “gần biển/chợ đêm”.
   Output example: "distance_limit_km": 2.0. If unspecified, use null.
5) Rating requirement: detect “rating cao”, “ít nhất 4 sao”, “đánh giá tốt”. Example: "rating_min": 4.2.
6) Special constraints: “không cay”, “không gluten”, “ăn chay”, “healthy”, “ít dầu mỡ”, “có điều hòa”, “mang đi”, “phù hợp đi theo nhóm”, etc.
7) Allergies: capture explicit allergy info (e.g., “dị ứng hải sản” -> ["seafood"]).
8) Eating time: capture if a time is mentioned (e.g., “trưa”, “tối”, “đêm”, “sáng”, or clock times).
9) User GPS: always include if provided: {{"lat": <float>, "lng": <float>}}. If missing, set null.
Output Format (Strict):
Return ONLY this JSON structure with every field present:
{{
  "intent": "",
  "cuisine": [],
  "price_range": {{"min": null, "max": null}},
  "distance_limit_km": null,
  "rating_min": null,
  "special_requirements": [],
  "allergies": [],
  "eating_time": null,
  "user_location": {{"lat": null, "lng": null}},
  "raw_input": ""
}}

Additional rules:
- Use null when a value is not provided or cannot be inferred.
- Keep raw_input exactly as given.
- Never output text before or after the JSON.
- Never add extra fields.
"""

PROMPT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        (
            "human",
            'User input: "{user_message}"\nLatitude: {lat}\nLongitude: {lng}\nReturn JSON only.',
        ),
    ]
)


def build_input_parser_chain(model_name: str = "gpt-4o-mini", temperature: float = 0.0):
    """Create a LangChain chain that enforces JSON output for the input parser agent."""
    llm = ChatOpenAI(model=model_name, temperature=temperature, streaming = True)
    parser = JsonOutputParser()
    return PROMPT_TEMPLATE | llm | parser


def parse_user_request(
    user_message: str,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    chain=None,
) -> Dict[str, Any]:
    """Helper to run the input parser chain and return a JSON dict."""
    active_chain = chain or build_input_parser_chain()
    lat_value: Optional[float | str] = "null" if lat is None else lat
    lng_value: Optional[float | str] = "null" if lng is None else lng
    return active_chain.invoke({"user_message": user_message, "lat": lat_value, "lng": lng_value})
