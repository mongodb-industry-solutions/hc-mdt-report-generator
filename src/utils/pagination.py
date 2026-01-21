from typing import List, Any, Tuple, Dict, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model"""
    items: List[T]
    total: int
    page: int
    page_size: int

def paginate(items: List[Any], page: int, page_size: int) -> Dict:
    """
    Paginate a list of items.
    Returns a dict with total, page, page_size, and items.
    """
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_items = items[start:end]
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": paginated_items
    } 