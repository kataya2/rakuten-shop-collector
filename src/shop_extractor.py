from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class ShopInfo:
    shop_id: str
    shop_name: str
    shop_url: str
    item_count: int
    avg_review: float
    total_reviews: int
    min_price: int
    genre_id: str


def extract_shops(items: list[dict]) -> list[ShopInfo]:
    """APIレスポンスのアイテムリストをショップ単位に集約し、item_count降順で返す。"""
    groups: dict[str, list[dict]] = defaultdict(list)
    for entry in items:
        item = entry["Item"]
        groups[item["shopCode"]].append(item)

    shops: list[ShopInfo] = []
    for shop_id, item_list in groups.items():
        first = item_list[0]
        reviews = [float(i.get("reviewAverage") or 0) for i in item_list]
        review_counts = [int(i.get("reviewCount") or 0) for i in item_list]
        prices = [int(i.get("itemPrice") or 0) for i in item_list]

        shops.append(ShopInfo(
            shop_id=shop_id,
            shop_name=first["shopName"],
            shop_url=first["shopUrl"],
            item_count=len(item_list),
            avg_review=round(sum(reviews) / len(reviews), 2),
            total_reviews=sum(review_counts),
            min_price=min(prices),
            genre_id=str(first.get("genreId", "")),
        ))

    return sorted(shops, key=lambda s: s.item_count, reverse=True)
