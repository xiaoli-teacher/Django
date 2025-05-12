from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from .models import Product, Inventory
import logging

logger = logging.getLogger(__name__)

class ProductService:
    """商品服务类"""

    # 搜索商品
    @staticmethod
    def search_products(query, page, per_page):
        try:
            cache_key = f'search_{query}_{page}_{per_page}'
            try:
                result = cache.get(cache_key)
            except Exception as e:
                logger.error(f"缓存读取异常: {str(e)}")
                result = None

            if result is None:
                products = Product.objects.filter(name__icontains=query)
                return {
                    'products': products,
                    'cache_key': cache_key
                }
            return result
        except Exception as e:
            logger.error(f"商品搜索异常: {str(e)}")
            raise

    # 格式化商品数据
    @staticmethod
    def format_product_data(products, page_obj):
        return {
            'products': [
                {
                    'id': product.id,
                    'name': product.name,
                    'price': float(product.price),
                    'inventory': product.inventory.quantity if hasattr(product, 'inventory') else 0
                }
                for product in page_obj
            ],
            'total_pages': page_obj.paginator.num_pages,
            'current_page': page_obj.number,
            'total_items': page_obj.paginator.count
        }

class InventoryService:
    """库存服务类"""

    # 获取商品库存
    @staticmethod
    def get_inventory(product_id):
        try:
            cache_key = f'inventory_{product_id}'
            try:
                inventory = cache.get(cache_key)
            except Exception as e:
                logger.error(f"缓存读取异常: {str(e)}")
                inventory = None
            
            if inventory is None:
                try:
                    inventory = Inventory.objects.select_related('product').get(product_id=product_id)
                    try:
                        cache.set(cache_key, inventory, timeout=300)
                    except Exception as e:
                        logger.error(f"缓存写入异常: {str(e)}")
                except Inventory.DoesNotExist:
                    logger.warning(f"商品不存在: {product_id}")
                    return None
            return inventory
        except Exception as e:
            logger.error(f"获取库存异常: {str(e)}")
            raise

    # 预订商品库存
    @staticmethod
    def reserve_inventory(product_id, quantity):
        try:
            with transaction.atomic():
                try:
                    inventory = Inventory.objects.select_for_update().get(product_id=product_id)
                    if inventory.quantity >= quantity:
                        inventory.quantity = F('quantity') - quantity
                        inventory.save()
                        # 更新缓存
                        try:
                            cache_key = f'inventory_{product_id}'
                            cache.delete(cache_key)
                            # 清除搜索缓存
                            cache.delete_pattern('search_*')
                        except Exception as e:
                            logger.error(f"缓存删除异常: {str(e)}")
                        return True
                    logger.warning(f"库存不足: 商品ID {product_id}, 请求数量 {quantity}, 当前库存 {inventory.quantity}")
                    return False
                except Inventory.DoesNotExist:
                    logger.warning(f"商品不存在: {product_id}")
                    return False
        except Exception as e:
            logger.error(f"库存预订异常: {str(e)}")
            raise 