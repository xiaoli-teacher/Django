from django.db import models
from django.core.cache import cache
from django.db.models import F
from django.db import transaction
import logging

# 配置日志
logger = logging.getLogger(__name__)

class Product(models.Model):
    """商品信息表"""
    name = models.CharField(max_length=100, verbose_name='商品名称')
    description = models.TextField(verbose_name='商品描述', blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='商品价格')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '商品'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['name']),  # 为商品名称创建索引
        ]

    def __str__(self):
        return self.name

class Inventory(models.Model):
    """库存信息表"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='inventory', verbose_name='商品')
    quantity = models.IntegerField(default=0, verbose_name='库存数量')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '库存'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.product.name} - 库存: {self.quantity}"

    @classmethod
    def get_inventory(cls, product_id):
        """获取商品库存，优先从缓存获取"""
        try:
            cache_key = f'inventory_{product_id}'
            try:
                inventory = cache.get(cache_key)
            except Exception as e:
                logger.error(f"缓存读取异常: {str(e)}")
                inventory = None
            
            if inventory is None:
                try:
                    inventory = cls.objects.select_related('product').get(product_id=product_id)
                    try:
                        cache.set(cache_key, inventory, timeout=300)
                    except Exception as e:
                        logger.error(f"缓存写入异常: {str(e)}")
                except cls.DoesNotExist:
                    logger.warning(f"商品不存在: {product_id}")
                    return None
                except Exception as e:
                    logger.error(f"数据库查询异常: {str(e)}")
                    raise
            return inventory
        except Exception as e:
            logger.error(f"获取库存异常: {str(e)}")
            raise

    @classmethod
    def reserve_inventory(cls, product_id, quantity):
        """
        预订商品库存
        使用数据库事务和行级锁确保并发安全
        """
        try:
            with transaction.atomic():
                try:
                    inventory = cls.objects.select_for_update().get(product_id=product_id)
                    if inventory.quantity >= quantity:
                        inventory.quantity = F('quantity') - quantity
                        inventory.save()
                        # 更新缓存
                        try:
                            cache_key = f'inventory_{product_id}'
                            cache.delete(cache_key)
                        except Exception as e:
                            logger.error(f"缓存删除异常: {str(e)}")
                        return True
                    logger.warning(f"库存不足: 商品ID {product_id}, 请求数量 {quantity}, 当前库存 {inventory.quantity}")
                    return False
                except cls.DoesNotExist:
                    logger.warning(f"商品不存在: {product_id}")
                    return False
        except Exception as e:
            logger.error(f"库存预订异常: {str(e)}")
            raise
