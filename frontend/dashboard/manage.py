import requests
from PyQt6.QtWidgets import (
    QTableWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
import os
import time
from datetime import datetime

class TableUpdateManager:
    """Manages efficient table updates to prevent UI freezing"""
    
    def __init__(self, table_widget):
        self.table = table_widget
        self.batch_size = 50  # Number of rows to update at once
        self.update_delay = 10  # Milliseconds between batch updates
        
    def begin_update(self):
        """Prepare table for batch updates"""
        self.table.setUpdatesEnabled(False)
        self.table.setSortingEnabled(False)
        
    def end_update(self):
        """Re-enable table updates and sorting"""
        self.table.setUpdatesEnabled(True)
        self.table.setSortingEnabled(True)
        
    def update_table_data(self, data, column_mapping):
        """Update table data in batches to prevent UI freezing
        
        Args:
            data: List of dictionaries containing row data
            column_mapping: Dictionary mapping column indices to data keys
        """
        total_rows = len(data)
        self.table.setRowCount(total_rows)
        
        def update_batch(start_idx):
            end_idx = min(start_idx + self.batch_size, total_rows)
            
            for row in range(start_idx, end_idx):
                row_data = data[row]
                for col, key in column_mapping.items():
                    if isinstance(key, tuple):  # Custom formatting function
                        key, formatter = key
                        value = formatter(row_data.get(key, ""))
                    else:
                        value = str(row_data.get(key, ""))
                    
                    item = QTableWidgetItem(value)
                    
                    # Store original data for sorting
                    if key in ['amount', 'date']:
                        try:
                            if key == 'amount':
                                item.setData(Qt.ItemDataRole.UserRole, float(value.replace(',', '')))
                            elif key == 'date':
                                item.setData(Qt.ItemDataRole.UserRole, datetime.strptime(value, "%Y-%m-%d"))
                        except (ValueError, TypeError):
                            pass
                    
                    self.table.setItem(row, col, item)
            
            if end_idx < total_rows:
                QTimer.singleShot(self.update_delay, lambda: update_batch(end_idx))
            else:
                self.end_update()
        
        self.begin_update()
        update_batch(0)

class DashboardCacheManager:
    """Manages caching for dashboard data"""
    _instance = None
    CACHE_TIMEOUT = 300  # 5 minutes cache timeout

    @classmethod
    def getInstance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.cache = {
            'branches': {'data': None, 'timestamp': 0},
            'transactions': {'data': None, 'timestamp': 0},
            'users': {'data': None, 'timestamp': 0},
            'financial': {'data': None, 'timestamp': 0},
            'activity': {'data': None, 'timestamp': 0}
        }

    def get(self, key):
        """Get cached data if valid"""
        entry = self.cache.get(key)
        if entry and time.time() - entry['timestamp'] < self.CACHE_TIMEOUT:
            return entry['data']
        return None

    def set(self, key, data):
        """Set cache data"""
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }

    def clear(self, key=None):
        """Clear specific or all cache entries"""
        if key:
            if key in self.cache:
                self.cache[key] = {'data': None, 'timestamp': 0}
        else:
            for k in self.cache:
                self.cache[k] = {'data': None, 'timestamp': 0}

class DataLoadThread(QThread):
    """Thread for loading dashboard data asynchronously"""
    data_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(str)
    
    def __init__(self, api_url, token, load_type='all'):
        super().__init__()
        self.api_url = api_url
        self.token = token
        self.load_type = load_type
        self.cache_manager = DashboardCacheManager.getInstance()
        
    def run(self):
        try:
            self.progress_updated.emit("جاري تحميل البيانات...")
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            if self.load_type == 'all' or self.load_type == 'basic':
                # Load basic stats from cache first
                cached_stats = self.cache_manager.get('basic_stats')
                if cached_stats:
                    self.data_loaded.emit({"basic_stats": cached_stats})
                    return

                # Load basic stats in parallel
                responses = {
                    'branches': requests.get(f"{self.api_url}/branches/stats/", headers=headers),
                    'users': requests.get(f"{self.api_url}/users/stats/", headers=headers),
                    'financial': requests.get(f"{self.api_url}/financial/total/", headers=headers)
                }
                
                combined_stats = {}
                for key, response in responses.items():
                    if response.status_code == 200:
                        combined_stats.update(response.json())
                
                self.cache_manager.set('basic_stats', combined_stats)
                self.data_loaded.emit({"basic_stats": combined_stats})

            if self.load_type == 'all' or self.load_type == 'transactions':
                # Load transactions from cache first
                cached_transactions = self.cache_manager.get('transactions')
                if cached_transactions:
                    self.data_loaded.emit({"transactions": cached_transactions})
                    return

                # Load transactions
                response = requests.get(f"{self.api_url}/transactions/", headers=headers)
                if response.status_code == 200:
                    transactions = response.json().get("transactions", [])
                    self.cache_manager.set('transactions', transactions)
                    self.data_loaded.emit({"transactions": transactions})

            if self.load_type == 'all' or self.load_type == 'activity':
                # Load activity from cache first
                cached_activity = self.cache_manager.get('activity')
                if cached_activity:
                    self.data_loaded.emit({"activity": cached_activity})
                    return

                # Load activity
                response = requests.get(f"{self.api_url}/activity/", headers=headers)
                if response.status_code == 200:
                    activity = response.json().get("activities", [])
                    self.cache_manager.set('activity', activity)
                    self.data_loaded.emit({"activity": activity})

        except Exception as e:
            self.error_occurred.emit(f"خطأ في تحميل البيانات: {str(e)}")

class ChartManager:
    """Manages efficient chart updates and statistics visualization"""
    
    def __init__(self, dashboard):
        self.dashboard = dashboard
        self._data_cache = {}
        self._update_queue = []
        self._is_updating = False
        
    def queue_update(self, chart_type, data):
        """Queue a chart update to be processed efficiently"""
        # No-op: charts are disabled
        pass
    
    def _process_next_update(self):
        """Process the next chart update in the queue"""
        # No-op: charts are disabled
        pass
    
    def _update_transfers_chart(self, data):
        """Update transfers chart efficiently"""
        # No-op: charts are disabled
        pass
    
    def _update_amounts_chart(self, data):
        """Update amounts chart efficiently"""
        # No-op: charts are disabled
        pass

class BranchStatsLoader(QThread):
    """Asynchronous loader for branch statistics"""
    stats_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(str)
    
    def __init__(self, api_url, token):
        super().__init__()
        self.api_url = api_url
        self.token = token
        
    def run(self):
        try:
            self.progress_updated.emit("جاري تحميل إحصائيات الفروع...")
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            
            # Load branch statistics
            response = requests.get(f"{self.api_url}/branches/stats/", headers=headers)
            if response.status_code == 200:
                stats = response.json()
                self.stats_loaded.emit(stats)
            else:
                self.error_occurred.emit(f"فشل تحميل إحصائيات الفروع: {response.status_code}")
        except Exception as e:
            self.error_occurred.emit(f"خطأ في تحميل إحصائيات الفروع: {str(e)}")

class TabDataManager:
    """Manages data loading and caching for each tab"""
    def __init__(self, parent):
        self.parent = parent
        self.loading_states = {}  # Track loading state for each tab
        self.preload_queue = []   # Queue for preloading data
        
    def is_loading(self, tab_name):
        """Check if a tab is currently loading data"""
        return self.loading_states.get(tab_name, False)
        
    def set_loading(self, tab_name, state):
        """Set loading state for a tab"""
        self.loading_states[tab_name] = state
        
    def preload_tab_data(self, tab_name):
        """Add tab to preload queue"""
        if tab_name not in self.preload_queue:
            self.preload_queue.append(tab_name)
            
    def process_preload_queue(self):
        """Process preload queue in background"""
        if not self.preload_queue:
            return
            
        tab_name = self.preload_queue.pop(0)
        self.load_tab_data(tab_name, is_preload=True)
        
    def load_tab_data(self, tab_name, is_preload=False):
        """Load data for specific tab"""
        if self.is_loading(tab_name) and not is_preload:
            return
            
        self.set_loading(tab_name, True)
        
        try:
            if tab_name == 'transactions':
                self.parent.load_thread = DataLoadThread(
                    self.parent.api_url, 
                    self.parent.token, 
                    'transactions'
                )
            elif tab_name == 'users':
                self.parent.load_thread = DataLoadThread(
                    self.parent.api_url, 
                    self.parent.token, 
                    'users'
                )
            elif tab_name == 'activity':
                self.parent.load_thread = DataLoadThread(
                    self.parent.api_url, 
                    self.parent.token, 
                    'activity'
                )
            else:
                self.parent.load_thread = DataLoadThread(
                    self.parent.api_url, 
                    self.parent.token, 
                    'basic'
                )
                
            self.parent.load_thread.finished.connect(
                lambda: self.set_loading(tab_name, False)
            )
            self.parent.load_thread.data_loaded.connect(self.parent.handle_loaded_data)
            self.parent.load_thread.error_occurred.connect(self.parent.handle_load_error)
            self.parent.load_thread.start()
            
        except Exception as e:
            print(f"Error loading tab data: {e}")
            self.set_loading(tab_name, False)