import requests
from PyQt6.QtWidgets import (
    QTableWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional
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
    """Thread-safe singleton cache manager with memory optimization"""
    _instance = None
    _lock = threading.Lock()
    
    CACHE_LEVELS = {
        'critical': 60,    # 1 minute
        'high': 300,      # 5 minutes
        'medium': 900,    # 15 minutes
        'low': 1800      # 30 minutes
    }
    
    MAX_CACHE_SIZE = 100 * 1024 * 1024  # 100MB max cache size
    
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
        
        # Start cleanup timer
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self.cleanup_expired)
        self.cleanup_timer.start(self.cleanup_interval * 1000)

    def get(self, key: str, level: str = 'medium') -> Optional[Any]:
        """Get cached data if valid"""
        with self._lock:
            entry = self.cache.get(key)
            if not entry:
                return None
                
            timeout = self.CACHE_LEVELS.get(level, self.CACHE_LEVELS['medium'])
            if time.time() - entry['timestamp'] < timeout:
                entry['hits'] = entry.get('hits', 0) + 1
                return entry['data']
                
            self.remove(key)
            return None

    def set(self, key: str, data: Any, size_estimate: int = 1000) -> bool:
        """Set cache data with size management"""
        with self._lock:
            # Check if we need to make room
            if self.cache_size + size_estimate > self.MAX_CACHE_SIZE:
                self.cleanup_expired()
                if self.cache_size + size_estimate > self.MAX_CACHE_SIZE:
                    self.evict_least_used(size_estimate)
            
            self.cache[key] = {
                'data': data,
                'timestamp': time.time(),
                'size': size_estimate,
                'hits': 0
            }
            self.cache_size += size_estimate
            return True

    def remove(self, key: str) -> None:
        """Remove item from cache"""
        with self._lock:
            if key in self.cache:
                self.cache_size -= self.cache[key]['size']
                del self.cache[key]

    def clear(self, key: str = None) -> None:
        """Clear specific or all cache entries"""
        with self._lock:
            if key:
                self.remove(key)
            else:
                self.cache.clear()
                self.cache_size = 0

    def cleanup_expired(self) -> None:
        """Remove expired entries"""
        with self._lock:
            current_time = time.time()
            expired_keys = []
            
            for key, entry in self.cache.items():
                timeout = self.CACHE_LEVELS['low']  # Use longest timeout
                if current_time - entry['timestamp'] > timeout:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self.remove(key)

    def evict_least_used(self, required_size: int) -> None:
        """Evict least used entries until required size is available"""
        with self._lock:
            entries = [(k, v) for k, v in self.cache.items()]
            entries.sort(key=lambda x: (x[1]['hits'], -x[1]['timestamp']))
            
            freed_space = 0
            for key, entry in entries:
                if freed_space >= required_size:
                    break
                freed_space += entry['size']
                self.remove(key)

class DataLoadThread(QThread):
    """Thread for loading dashboard data asynchronously with error handling and retry"""
    data_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(str)
    
    MAX_RETRIES = 3
    RETRY_DELAY = 1000  # 1 second
    
    def __init__(self, api_url: str, token: str, load_type: str = 'all'):
        super().__init__()
        self.api_url = api_url
        self.token = token
        self.load_type = load_type
        self.cache_manager = DashboardCacheManager.getInstance()
        self.should_stop = False
        
    def stop(self):
        self.should_stop = True
        
    def run(self):
        try:
            self.progress_updated.emit("جاري تحميل البيانات...")
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            for attempt in range(self.MAX_RETRIES):
                if self.should_stop:
                    return
                    
                try:
                    if self.load_type == 'all' or self.load_type == 'basic':
                        self.load_basic_stats(headers)
                    
                    if self.should_stop:
                        return
                        
                    if self.load_type == 'all' or self.load_type == 'transactions':
                        self.load_transactions(headers)
                        
                    if self.should_stop:
                        return
                        
                    if self.load_type == 'all' or self.load_type == 'activity':
                        self.load_activity(headers)
                        
                    break
                    
                except requests.RequestException as e:
                    if attempt < self.MAX_RETRIES - 1:
                        self.progress_updated.emit(f"إعادة المحاولة {attempt + 1}/{self.MAX_RETRIES}...")
                        time.sleep(self.RETRY_DELAY / 1000)
                    else:
                        raise e
                        
        except Exception as e:
            self.error_occurred.emit(f"خطأ في تحميل البيانات: {str(e)}")
            
    def load_basic_stats(self, headers):
        cached_stats = self.cache_manager.get('basic_stats', 'critical')
        if cached_stats:
            self.data_loaded.emit({"basic_stats": cached_stats})
            return

        responses = {
            'branches': self.make_request(f"{self.api_url}/branches/stats/", headers),
            'users': self.make_request(f"{self.api_url}/users/stats/", headers),
            'financial': self.make_request(f"{self.api_url}/financial/total/", headers)
        }
        
        combined_stats = {}
        for key, response in responses.items():
            if response and response.status_code == 200:
                combined_stats.update(response.json())
        
        self.cache_manager.set('basic_stats', combined_stats)
        self.data_loaded.emit({"basic_stats": combined_stats})
        
    def load_transactions(self, headers):
        cached_transactions = self.cache_manager.get('transactions', 'high')
        if cached_transactions:
            self.data_loaded.emit({"transactions": cached_transactions})
            return

        response = self.make_request(f"{self.api_url}/transactions/", headers)
        if response and response.status_code == 200:
            transactions = response.json().get("transactions", [])
            self.cache_manager.set('transactions', transactions)
            self.data_loaded.emit({"transactions": transactions})
            
    def load_activity(self, headers):
        cached_activity = self.cache_manager.get('activity', 'medium')
        if cached_activity:
            self.data_loaded.emit({"activity": cached_activity})
            return

        response = self.make_request(f"{self.api_url}/activity/", headers)
        if response and response.status_code == 200:
            activity = response.json().get("activities", [])
            self.cache_manager.set('activity', activity)
            self.data_loaded.emit({"activity": activity})
            
    def make_request(self, url, headers, timeout=5):
        try:
            return requests.get(url, headers=headers, timeout=timeout)
        except requests.RequestException:
            return None

class TabDataManager:
    """Manages data loading and caching for each tab with memory optimization"""
    def __init__(self, parent):
        self.parent = parent
        self.loading_states = {}
        self.preload_queue = []
        self.cache_manager = DashboardCacheManager.getInstance()
        self._active_threads = weakref.WeakSet()
        
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
            
        tab_name = self.preload_queue.pop(0)
        self.load_tab_data(tab_name, is_preload=True)
        
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
            
    def _get_load_type(self, tab_name: str) -> str:
        load_types = {
            'transactions': 'transactions',
            'users': 'users',
            'activity': 'activity'
        }
        return load_types.get(tab_name, 'basic')
        
    def cleanup(self) -> None:
        """Stop all active threads and clear queues"""
        for thread in self._active_threads:
            if thread.isRunning():
                thread.stop()
                thread.wait()
        self._active_threads.clear()
        self.preload_queue.clear()