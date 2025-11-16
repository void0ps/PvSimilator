"""后端健壮性工具：重试、降级、熔断等"""
import time
import logging
from functools import wraps
from typing import Callable, Any, Optional, Type
import threading

logger = logging.getLogger(__name__)


class CacheLock:
    """缓存刷新锁，防止并发刷新"""
    def __init__(self):
        self._locks = {}
        self._lock = threading.Lock()
    
    def acquire(self, key: str, timeout: float = 30.0) -> bool:
        """获取锁"""
        with self._lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
        
        return self._locks[key].acquire(timeout=timeout)
    
    def release(self, key: str):
        """释放锁"""
        if key in self._locks:
            try:
                self._locks[key].release()
            except:
                pass


# 全局缓存锁实例
cache_lock = CacheLock()


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    fallback_value: Any = None
):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 退避倍数
        exceptions: 需要重试的异常类型
        fallback_value: 失败后的回退值
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} 失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}, "
                            f"将在 {current_delay:.1f}秒后重试"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"{func.__name__} 失败 {max_retries} 次，使用回退值: {fallback_value}"
                        )
            
            if fallback_value is not None:
                return fallback_value
            raise last_exception
        
        return wrapper
    return decorator


def with_cache_lock(key_param: str = None):
    """
    缓存锁装饰器
    
    Args:
        key_param: 用作锁key的参数名，默认使用函数名
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 确定锁的key
            if key_param and key_param in kwargs:
                lock_key = f"{func.__name__}:{kwargs[key_param]}"
            else:
                lock_key = func.__name__
            
            # 尝试获取锁
            if not cache_lock.acquire(lock_key, timeout=30.0):
                logger.warning(f"{func.__name__} 获取锁超时: {lock_key}")
                raise TimeoutError(f"无法获取缓存锁: {lock_key}")
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                cache_lock.release(lock_key)
        
        return wrapper
    return decorator


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """安全除法，避免除零错误"""
    try:
        if abs(denominator) < 1e-10:
            return default
        return numerator / denominator
    except:
        return default


def safe_get_dict(data: dict, *keys, default: Any = None) -> Any:
    """安全的多级字典取值"""
    try:
        result = data
        for key in keys:
            result = result[key]
        return result
    except (KeyError, TypeError, AttributeError):
        return default


class CircuitBreaker:
    """熔断器模式实现"""
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        self._lock = threading.Lock()
    
    def call(self, func: Callable, *args, **kwargs):
        """执行函数调用，支持熔断"""
        with self._lock:
            if self.state == "open":
                # 检查是否可以转换为半开状态
                if time.time() - self.last_failure_time > self.timeout:
                    self.state = "half-open"
                    logger.info(f"熔断器进入半开状态: {func.__name__}")
                else:
                    raise Exception(f"熔断器打开，拒绝调用: {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            
            with self._lock:
                # 成功调用，重置计数
                if self.state == "half-open":
                    self.state = "closed"
                    logger.info(f"熔断器关闭: {func.__name__}")
                self.failure_count = 0
            
            return result
            
        except self.expected_exception as e:
            with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
                    logger.error(
                        f"熔断器打开: {func.__name__} "
                        f"(失败{self.failure_count}次)"
                    )
            
            raise e


def validate_input(
    validator: Callable[[Any], bool],
    error_message: str = "输入验证失败"
):
    """输入验证装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 验证第一个参数（通常是self之后的第一个参数）
            if len(args) > 1:
                if not validator(args[1]):
                    raise ValueError(error_message)
            elif 'data' in kwargs:
                if not validator(kwargs['data']):
                    raise ValueError(error_message)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

















