import requests
from PyQt6.QtWidgets import (
    QTableWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from queue import Queue
import weakref
import threading
from .table_manager import OptimizedTableManager

class TableUpdateManager:
    """Legacy adapter for OptimizedTableManager"""
    
    def __init__(self, table_widget):
        self.optimized_manager = OptimizedTableManager.get_instance(table_widget)
        
    def begin_update(self):
        pass  # Handled by OptimizedTableManager
        
    def end_update(self):
        pass  # Handled by OptimizedTableManager
        
    def update_table_data(self, data, column_mapping):
        """Forward to OptimizedTableManager"""
        self.optimized_manager.set_data(data, column_mapping)

class DashboardCacheManager:
    """Thread-safe singleton cache manager with advanced memory optimization and monitoring"""
    _instance = None
    _lock = threading.Lock()
    
    # Cache levels with timeouts (in seconds)
    CACHE_LEVELS = {
        'critical': 60,     # 1 minute
        'high': 300,       # 5 minutes
        'medium': 900,     # 15 minutes
        'low': 1800,      # 30 minutes
        'background': 3600 # 1 hour
    }
    
    # Memory limits
    MAX_CACHE_SIZE = 100 * 1024 * 1024  # 100MB max cache size
    WARNING_THRESHOLD = 0.8  # 80% of max size
    CRITICAL_THRESHOLD = 0.9  # 90% of max size
    
    # Performance monitoring
    METRICS_WINDOW = 3600  # 1 hour window for metrics
    
    @classmethod
    def getInstance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_size = 0
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
        
        # Performance metrics
        self.metrics = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0,
            'last_reset': time.time()
        }
        
        # Access patterns tracking
        self.access_patterns = {}
        
        # Start monitoring timers
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self.cleanup_expired)
        self.cleanup_timer.start(self.cleanup_interval * 1000)
        
        self.metrics_timer = QTimer()
        self.metrics_timer.timeout.connect(self.reset_metrics)
        self.metrics_timer.start(self.METRICS_WINDOW * 1000)

    def get(self, key: str, level: str = 'medium') -> Optional[Any]:
        """Get cached data with advanced metrics tracking"""
        with self._lock:
            self.metrics['total_requests'] += 1
            
            entry = self.cache.get(key)
            if not entry:
                self.metrics['misses'] += 1
                return None
                
            timeout = self.CACHE_LEVELS.get(level, self.CACHE_LEVELS['medium'])
            current_time = time.time()
            
            if current_time - entry['timestamp'] < timeout:
                # Update access patterns
                self.access_patterns[key] = self.access_patterns.get(key, 0) + 1
                entry['hits'] = entry.get('hits', 0) + 1
                entry['last_access'] = current_time
                self.metrics['hits'] += 1
                return entry['data']
                
            self.remove(key)
            self.metrics['misses'] += 1
            return None

    def set(self, key: str, data: Any, size_estimate: int = 1000, level: str = 'medium') -> bool:
        """Set cache data with smart memory management"""
        with self._lock:
            # Check memory thresholds
            if self.cache_size + size_estimate > self.MAX_CACHE_SIZE:
                if self.cache_size + size_estimate > self.MAX_CACHE_SIZE * self.CRITICAL_THRESHOLD:
                    # Critical threshold reached - force cleanup
                    self.force_cleanup(size_estimate)
                elif self.cache_size + size_estimate > self.MAX_CACHE_SIZE * self.WARNING_THRESHOLD:
                    # Warning threshold reached - try cleanup
                    self.cleanup_expired()
                    
            # If still not enough space, evict items
            if self.cache_size + size_estimate > self.MAX_CACHE_SIZE:
                self.evict_least_used(size_estimate)
            
            # Store with metadata
            self.cache[key] = {
                'data': data,
                'timestamp': time.time(),
                'size': size_estimate,
                'hits': 0,
                'level': level,
                'last_access': time.time()
            }
            
            self.cache_size += size_estimate
            return True

    def remove(self, key: str) -> None:
        """Remove item from cache with metrics update"""
        with self._lock:
            if key in self.cache:
                self.cache_size -= self.cache[key]['size']
                self.metrics['evictions'] += 1
                del self.cache[key]
                if key in self.access_patterns:
                    del self.access_patterns[key]

    def clear(self, key: str = None) -> None:
        """Clear specific or all cache entries"""
        with self._lock:
            if key:
                self.remove(key)
            else:
                self.cache.clear()
                self.access_patterns.clear()
                self.cache_size = 0
                self.reset_metrics()

    def cleanup_expired(self) -> None:
        """Remove expired entries with smart cleanup"""
        with self._lock:
            current_time = time.time()
            expired_keys = []
            
            for key, entry in self.cache.items():
                level = entry.get('level', 'medium')
                timeout = self.CACHE_LEVELS.get(level, self.CACHE_LEVELS['medium'])
                
                # Check both timeout and access patterns
                if (current_time - entry['timestamp'] > timeout or
                    (current_time - entry.get('last_access', 0) > timeout * 2)):
                    expired_keys.append(key)
            
            for key in expired_keys:
                self.remove(key)
            
            self.last_cleanup = current_time

    def force_cleanup(self, required_size: int) -> None:
        """Force cleanup to free up required space"""
        with self._lock:
            # First try removing expired items
            self.cleanup_expired()
            
            # If still need space, remove least accessed items
            if self.cache_size + required_size > self.MAX_CACHE_SIZE:
                self.evict_least_used(required_size)

    def evict_least_used(self, required_size: int) -> None:
        """Evict least used entries using smart selection"""
        with self._lock:
            if not self.cache:
                return
                
            # Sort entries by priority score
            entries = [(k, v) for k, v in self.cache.items()]
            entries.sort(key=lambda x: self._calculate_priority_score(x[1]))
            
            freed_space = 0
            for key, entry in entries:
                if freed_space >= required_size:
                    break
                freed_space += entry['size']
                self.remove(key)

    def _calculate_priority_score(self, entry: Dict[str, Any]) -> float:
        """Calculate priority score for cache entry"""
        current_time = time.time()
        age = current_time - entry['timestamp']
        last_access = current_time - entry.get('last_access', current_time)
        hits = entry.get('hits', 0)
        level_weights = {
            'critical': 5.0,
            'high': 4.0,
            'medium': 3.0,
            'low': 2.0,
            'background': 1.0
        }
        level_weight = level_weights.get(entry.get('level', 'medium'), 3.0)
        
        # Higher score = lower priority for eviction
        return (hits * level_weight) / (age * last_access + 1)

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics"""
        with self._lock:
            total_requests = self.metrics['total_requests']
            hit_rate = (self.metrics['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'hit_rate': hit_rate,
                'hits': self.metrics['hits'],
                'misses': self.metrics['misses'],
                'evictions': self.metrics['evictions'],
                'total_requests': total_requests,
                'cache_size_mb': self.cache_size / 1024 / 1024,
                'cache_usage_percent': (self.cache_size / self.MAX_CACHE_SIZE) * 100,
                'items_count': len(self.cache)
            }

    def reset_metrics(self) -> None:
        """Reset performance metrics"""
        with self._lock:
            self.metrics = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'total_requests': 0,
                'last_reset': time.time()
            }

    def get_hot_keys(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most frequently accessed cache keys"""
        with self._lock:
            sorted_keys = sorted(
                self.access_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )
            return sorted_keys[:limit]

    def optimize(self) -> None:
        """Optimize cache based on usage patterns"""
        with self._lock:
            hot_keys = self.get_hot_keys()
            for key, _ in hot_keys:
                if key in self.cache:
                    # Promote frequently accessed items to higher cache level
                    entry = self.cache[key]
                    current_level = entry.get('level', 'medium')
                    if current_level != 'critical':
                        levels = list(self.CACHE_LEVELS.keys())
                        current_index = levels.index(current_level)
                        if current_index > 0:  # Can be promoted
                            entry['level'] = levels[current_index - 1]

class DataLoadThread(QThread):
    """Thread for loading dashboard data asynchronously with enhanced progress tracking and error handling"""
    # Basic signals
    data_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(str)
    
    # Enhanced progress signals
    progress_percentage = pyqtSignal(int)
    stage_updated = pyqtSignal(str)
    request_started = pyqtSignal(str)
    request_finished = pyqtSignal(str)
    state_changed = pyqtSignal(str)
    
    # Constants
    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 5]  # Increasing delays between retries (seconds)
    REQUEST_TIMEOUT = 10
    
    # States
    STATES = {
        'IDLE': 'idle',
        'LOADING': 'loading',
        'RETRYING': 'retrying',
        'ERROR': 'error',
        'COMPLETED': 'completed',
        'CANCELLED': 'cancelled'
    }
    
    def __init__(self, api_url: str, token: str, load_type: str = 'all'):
        super().__init__()
        self.api_url = api_url
        self.token = token
        self.load_type = load_type
        self.cache_manager = DashboardCacheManager.getInstance()
        self.should_stop = False
        self.paused = False
        self.current_state = self.STATES['IDLE']
        self.current_stage = ""
        self.total_stages = 0
        self.completed_stages = 0
        self._start_time = None
        self._operation_times = {}
        
    def _set_state(self, state: str) -> None:
        """Update current state and emit signal"""
        self.current_state = self.STATES.get(state, self.STATES['IDLE'])
        self.state_changed.emit(self.current_state)
        
    def pause(self) -> None:
        """Pause the loading process"""
        self.paused = True
        self._set_state('IDLE')
        
    def resume(self) -> None:
        """Resume the loading process"""
        self.paused = False
        self._set_state('LOADING')
        
    def stop(self) -> None:
        """Stop the loading process"""
        self.should_stop = True
        self._set_state('CANCELLED')
        self._cleanup_memory()
        
    def _update_progress(self, stage: str, percentage: int) -> None:
        """Update progress information"""
        self.current_stage = stage
        self.stage_updated.emit(stage)
        self.progress_percentage.emit(percentage)
        self.progress_updated.emit(f"جاري {stage}... {percentage}%")
        
    def _track_memory(self, operation: str) -> None:
        """Track memory usage for operations"""
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        self._operation_times[operation] = {
            'memory_used': memory_info.rss / 1024 / 1024,  # MB
            'time': time.time() - self._start_time
        }
        
    def _cleanup_memory(self) -> None:
        """Cleanup memory after operations"""
        import gc
        gc.collect()
        
    def _log_performance(self, operation: str, start_time: float) -> None:
        """Log performance metrics"""
        duration = time.time() - start_time
        print(f"Operation '{operation}' took {duration:.2f} seconds")
        if operation in self._operation_times:
            memory_used = self._operation_times[operation]['memory_used']
            print(f"Memory used: {memory_used:.2f} MB")
            
    def make_request(self, url: str, headers: dict, timeout: int = None) -> Optional[requests.Response]:
        """Make HTTP request with enhanced error handling"""
        if timeout is None:
            timeout = self.REQUEST_TIMEOUT
            
        self.request_started.emit(url)
        start_time = time.time()
        
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            self.request_finished.emit(url)
            self._log_performance(f"Request to {url}", start_time)
            return response
        except requests.RequestException as e:
            self.error_occurred.emit(f"خطأ في الاتصال: {str(e)}")
            return None
            
    def run(self):
        """Execute the data loading process with fully parallel loading of all data types"""
        self._start_time = time.time()
        self._set_state('LOADING')
        try:
            self.progress_updated.emit("جاري تحميل البيانات...")
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

            import concurrent.futures
            tasks = []
            results = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                if self.load_type == 'all':
                    tasks.append(executor.submit(self.load_basic_stats, headers))
                    tasks.append(executor.submit(self.load_transactions, headers))
                    tasks.append(executor.submit(self.load_activity, headers))
                else:
                    if self.load_type == 'basic':
                        tasks.append(executor.submit(self.load_basic_stats, headers))
                    if self.load_type == 'transactions':
                        tasks.append(executor.submit(self.load_transactions, headers))
                    if self.load_type == 'activity':
                        tasks.append(executor.submit(self.load_activity, headers))
                for future in concurrent.futures.as_completed(tasks):
                    pass
            self._set_state('COMPLETED')
        except Exception as e:
            self._set_state('ERROR')
            self.error_occurred.emit(f"خطأ في تحميل البيانات: {str(e)}")
        finally:
            self._cleanup_memory()
            self._log_performance("Total operation", self._start_time)
        
    def load_basic_stats(self, headers: dict) -> None:
        """Load basic statistics with progress tracking and parallel requests"""
        operation_start = time.time()
        
        cached_stats = self.cache_manager.get('basic_stats', 'critical')
        if cached_stats:
            self.data_loaded.emit({"basic_stats": cached_stats})
            return

        self._update_progress("تحميل إحصائيات النظام", 33)
        
        # Use concurrent requests
        import concurrent.futures
        
        urls = {
            'branches': f"{self.api_url}/branches/stats/",
            'users': f"{self.api_url}/users/stats/",
            'financial': f"{self.api_url}/financial/total/"
        }
        
        combined_stats = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Start all requests concurrently
            future_to_url = {
                executor.submit(self.make_request, url, headers): key
                for key, url in urls.items()
            }
            
            # Process responses as they complete
            for future in concurrent.futures.as_completed(future_to_url):
                key = future_to_url[future]
                try:
                    response = future.result()
                    if response and response.status_code == 200:
                        combined_stats.update(response.json())
                except Exception as e:
                    print(f"Error loading {key} stats: {e}")
        
        self._update_progress("معالجة البيانات", 66)
        
        if combined_stats:
            self._update_progress("حفظ البيانات", 100)
            self.cache_manager.set('basic_stats', combined_stats)
            self.data_loaded.emit({"basic_stats": combined_stats})
        
        self._track_memory('load_basic_stats')
        self._log_performance('load_basic_stats', operation_start)
        
    def load_transactions(self, headers: dict) -> None:
        """Load transactions with progress tracking"""
        operation_start = time.time()
        
        cached_transactions = self.cache_manager.get('transactions', 'high')
        if cached_transactions:
            self.data_loaded.emit({"transactions": cached_transactions})
            return

        self._update_progress("تحميل التحويلات", 50)
        response = self.make_request(f"{self.api_url}/transactions/", headers)
        
        if response and response.status_code == 200:
            transactions = response.json().get("transactions", [])
            self.cache_manager.set('transactions', transactions)
            self.data_loaded.emit({"transactions": transactions})
            
        self._track_memory('load_transactions')
        self._log_performance('load_transactions', operation_start)
        
    def load_activity(self, headers: dict) -> None:
        """Load activity data with progress tracking"""
        operation_start = time.time()
        
        cached_activity = self.cache_manager.get('activity', 'medium')
        if cached_activity:
            self.data_loaded.emit({"activity": cached_activity})
            return

        self._update_progress("تحميل النشاطات", 50)
        response = self.make_request(f"{self.api_url}/activity/", headers)
        
        if response and response.status_code == 200:
            activity = response.json().get("activities", [])
            self.cache_manager.set('activity', activity)
            self.data_loaded.emit({"activity": activity})
            
        self._track_memory('load_activity')
        self._log_performance('load_activity', operation_start)

class TabDataManager:
    """Manages data loading and caching for each tab with memory optimization and parallel preloading"""
    def __init__(self, parent):
        self.parent = parent
        self.loading_states = {}
        self.preload_queue = []
        self.cache_manager = DashboardCacheManager.getInstance()
        self._active_threads = weakref.WeakSet()
        self._preload_futures = {}
        self._executor = None

    def is_loading(self, tab_name: str) -> bool:
        return self.loading_states.get(tab_name, False)

    def set_loading(self, tab_name: str, state: bool) -> None:
        self.loading_states[tab_name] = state

    def preload_tab_data(self, tab_name: str) -> None:
        if tab_name not in self.preload_queue:
            self.preload_queue.append(tab_name)

    def process_preload_queue(self) -> None:
        if not self.preload_queue:
            return
        if self._executor is None:
            import concurrent.futures
            self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        while self.preload_queue:
            tab_name = self.preload_queue.pop(0)
            if tab_name not in self._preload_futures:
                future = self._executor.submit(self.load_tab_data, tab_name, True)
                self._preload_futures[tab_name] = future

    def load_tab_data(self, tab_name: str, is_preload: bool = False) -> None:
        if self.is_loading(tab_name) and not is_preload:
            return
        self.set_loading(tab_name, True)
        try:
            load_thread = DataLoadThread(
                self.parent.api_url,
                self.parent.token,
                self._get_load_type(tab_name)
            )
            load_thread.finished.connect(
                lambda: self.set_loading(tab_name, False)
            )
            load_thread.data_loaded.connect(self.parent.handle_loaded_data)
            load_thread.error_occurred.connect(self.parent.handle_load_error)
            self._active_threads.add(load_thread)
            load_thread.start()
        except Exception as e:
            print(f"Error loading tab data: {e}")
            self.set_loading(tab_name, False)

    def cancel_loading(self, tab_name: str) -> None:
        """Cancel loading for a specific tab if possible"""
        for thread in list(self._active_threads):
            if hasattr(thread, 'load_type') and self._get_load_type(tab_name) == thread.load_type:
                thread.stop()
                self._active_threads.discard(thread)
        self.set_loading(tab_name, False)

    def _get_load_type(self, tab_name: str) -> str:
        load_types = {
            'transactions': 'transactions',
            'users': 'users',
            'activity': 'activity',
            'branches': 'branches',
            'basic': 'basic'
        }
        return load_types.get(tab_name, 'basic')

    def cleanup(self) -> None:
        """Stop all active threads and clear queues"""
        for thread in list(self._active_threads):
            if thread.isRunning():
                thread.stop()
                thread.wait()
        self._active_threads.clear()
        self.preload_queue.clear()
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None
        self._preload_futures.clear()