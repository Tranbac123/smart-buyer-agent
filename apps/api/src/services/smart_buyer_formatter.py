from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional


def render_smart_buyer_summary(response: Dict[str, Any], *, query: Optional[str] = None, max_other_options: int = 3) -> str:
    """
    Render a chatbot-friendly summary string from a Smart Buyer JSON payload.

    Parameters
    ----------
    response:
        Dict returned by Smart Buyer flow (offers, scoring, explanation, metadata).
    query:
        Optional override for the user query; falls back to response["query"].
    max_other_options:
        How many alternative offers to list in the summary section.
    """
    offers = _as_offer_list(response.get("offers"))
    q = (query or response.get("query") or "").strip()
    if not offers:
        if q:
            return f"Mình chưa tìm được kết quả phù hợp cho “{q}”. Bạn thử mô tả chi tiết hơn được không?"
        return "Mình chưa tìm được kết quả phù hợp. Bạn thử mô tả chi tiết hơn được không?"

    scoring = response.get("scoring") or {}
    best_id = scoring.get("best")
    offer_by_id = { _offer_id(o): o for o in offers if _offer_id(o) }
    best_offer = offer_by_id.get(best_id) if best_id else None
    if best_offer is None and offers:
        best_offer = offers[0]

    sites_list = _format_sites(offers)
    best_price_text = _format_price(best_offer.get("price"), best_offer.get("currency", "VND"))
    best_site = (best_offer.get("site") or "shop").capitalize()
    best_title = best_offer.get("title") or "sản phẩm"
    rating_text = _format_rating(best_offer.get("rating") or best_offer.get("seller_rating"))
    review_text = _format_review_count(best_offer.get("review_count") or best_offer.get("rating_count"))
    shop_text = best_offer.get("shop_name") or "shop trên sàn"

    conf = scoring.get("confidence")
    conf_text = f" (độ tự tin khoảng {conf * 100:.0f}%)" if isinstance(conf, (int, float)) else ""

    other_lines = []
    for offer in (o for o in offers if o is not best_offer):
        if len(other_lines) >= max_other_options:
            break
        o_rating = _format_rating(offer.get("rating") or offer.get("seller_rating"))
        o_reviews = _format_review_count(offer.get("review_count") or offer.get("rating_count"))
        other_lines.append(
            f"- { (offer.get('site') or 'shop').capitalize() }: “{ offer.get('title') or 'sản phẩm' }” – khoảng {_format_price(offer.get('price'), offer.get('currency', 'VND'))}₫ ({o_rating}, {o_reviews})"
        )
    other_block = "\n".join(other_lines) if other_lines else "Hiện chưa có lựa chọn nào khác nổi bật."

    intro_query = f"“{q}”" if q else "sản phẩm bạn hỏi"

    return f"""✅ Tóm tắt cho {intro_query}

Mình đã tìm cho bạn trên {sites_list}.

🎯 Giá tham khảo tốt nhất hiện tại:
- Khoảng **{best_price_text}₫** tại **{best_site}** – sản phẩm: **“{best_title}”**.

Lý do gợi ý{conf_text}:
- Đây là lựa chọn có giá tốt nhất trong {len(offers)} kết quả mình tìm được.
- Thông tin thêm: {rating_text}, {review_text}, {shop_text}.

Các lựa chọn khác để tham khảo:
{other_block}

👉 Nếu bạn ưu tiên **giá rẻ**, mình khuyên nên chọn phương án ở trên.
Nếu bạn muốn ưu tiên **uy tín shop** hoặc **đánh giá**, mình có thể tra cứu sâu hơn theo tiêu chí đó."""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _as_offer_list(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, list):
        return [o for o in raw if isinstance(o, dict)]
    return []


def _offer_id(offer: Dict[str, Any]) -> Optional[str]:
    oid = offer.get("id") or offer.get("option_id") or offer.get("title")
    if not oid:
        return None
    return str(oid)


def _format_sites(offers: List[Dict[str, Any]]) -> str:
    sites = []
    seen = set()
    for offer in offers:
        site = (offer.get("site") or "").strip()
        if site and site not in seen:
            seen.add(site)
            sites.append(site.capitalize())
    if not sites:
        return "các sàn thương mại điện tử"
    return ", ".join(sites)


def _format_price(value: Any, currency: str = "VND") -> str:
    amount = _to_number(value)
    if amount is None:
        return str(value)
    return f"{amount:,.0f}".replace(",", ".")


def _format_rating(value: Any) -> str:
    rating = _to_number(value)
    if rating is None:
        return "chưa có dữ liệu rating"
    return f"khoảng {rating:.1f}★"


def _format_review_count(value: Any) -> str:
    count = _to_number(value)
    if count is None:
        return "chưa rõ số lượng đánh giá"
    if isinstance(count, float) and not count.is_integer():
        count = int(round(count))
    return f"{int(count):,} đánh giá".replace(",", ".")


def _to_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(Decimal(str(value)))
    except Exception:
        return None
