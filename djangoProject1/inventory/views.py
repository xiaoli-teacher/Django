from django.shortcuts import render
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from .services import ProductService, InventoryService
import logging

# 配置日志
logger = logging.getLogger(__name__)

#渲染搜索页面
def search_page(request):
    try:
        return render(request, 'inventory/search.html')
    except Exception as e:
        logger.error(f"渲染搜索页面异常: {str(e)}")
        return JsonResponse({'error': '系统繁忙，请稍后重试'}, status=500)

#商品搜索视图
def search_products(request):
    query = request.GET.get('query', '')
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)

    try:
        # 使用服务层搜索商品
        result = ProductService.search_products(query, page, per_page)
        
        if isinstance(result, dict) and 'products' in result:
            # 需要从数据库查询
            products = result['products']
            paginator = Paginator(products, per_page)
            page_obj = paginator.get_page(page)
            
            # 格式化数据
            formatted_result = ProductService.format_product_data(products, page_obj)
            
            # 缓存结果
            try:
                cache.set(result['cache_key'], formatted_result, timeout=300)
            except Exception as e:
                logger.error(f"缓存写入异常: {str(e)}")
            
            return JsonResponse(formatted_result)
        
        # 返回缓存的结果
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"搜索处理异常: {str(e)}")
        return JsonResponse({'error': '系统繁忙，请稍后重试'}, status=500)

# 库存预订视图
@csrf_exempt
@require_http_methods(["POST"])
def reserve_inventory(request):
    try:
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 0))

        if not product_id or quantity <= 0:
            logger.warning(f"无效的预订参数: product_id={product_id}, quantity={quantity}")
            return JsonResponse({'error': '无效的参数'}, status=400)

        try:
            # 使用服务层进行库存预订
            success = InventoryService.reserve_inventory(product_id, quantity)
            
            if success:
                return JsonResponse({'message': '预订成功'})
            else:
                return JsonResponse({'error': '库存不足'}, status=400)
        except ValueError as e:
            logger.error(f"预订处理异常: {str(e)}")
            return JsonResponse({'error': '无效的数量'}, status=400)
        except Exception as e:
            logger.error(f"预订处理异常: {str(e)}")
            return JsonResponse({'error': '系统繁忙，请稍后重试'}, status=500)
    except Exception as e:
        logger.error(f"预订请求处理异常: {str(e)}")
        return JsonResponse({'error': '系统繁忙，请稍后重试'}, status=500)

# 获取商品库存视图
def get_inventory(request, product_id):
    try:
        try:
            # 使用服务层获取库存
            inventory = InventoryService.get_inventory(product_id)
            if inventory:
                return JsonResponse({
                    'product_id': product_id,
                    'quantity': inventory.quantity
                })
            return JsonResponse({'error': '商品不存在'}, status=404)
        except Exception as e:
            logger.error(f"获取库存异常: {str(e)}")
            return JsonResponse({'error': '系统繁忙，请稍后重试'}, status=500)
    except Exception as e:
        logger.error(f"库存查询请求处理异常: {str(e)}")
        return JsonResponse({'error': '系统繁忙，请稍后重试'}, status=500)
