from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QScrollBar, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint, QObject
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import weakref

class VirtualScrollBar(QScrollBar):
    """Custom scrollbar for virtual scrolling"""
    scroll_changed = pyqtSignal(int)
    
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.valueChanged.connect(self.scroll_changed.emit)
        self._last_value = 0
        
    def wheelEvent(self, event):
        """Smooth scrolling with mouse wheel"""
        delta = event.angleDelta().y()
        new_value = self.value() - delta // 2
        self.setValue(new_value)
        if new_value != self._last_value:
            self.scroll_changed.emit(new_value)
            self._last_value = new_value

class OptimizedTableManager(QObject):
    """Manages table data with virtual scrolling and efficient updates"""
    
    _instances = weakref.WeakValueDictionary()
    
    BUFFER_SIZE = 50  # Number of extra rows to load above/below visible area
    UPDATE_INTERVAL = 100  # ms between updates
    CHUNK_SIZE = 20  # Number of rows to update in one batch
    
    @classmethod
    def get_instance(cls, table_widget: QTableWidget) -> 'OptimizedTableManager':
        if table_widget not in cls._instances:
            cls._instances[table_widget] = cls(table_widget)
        return cls._instances[table_widget]
    
    def __init__(self, table_widget: QTableWidget):
        super().__init__(table_widget)  # Pass parent to QObject
        self.table = table_widget
        self.full_data: List[Dict[str, Any]] = []
        self.visible_rows: Dict[int, bool] = {}
        self.column_mapping: Dict[int, str] = {}
        self.formatters: Dict[str, Callable] = {}
        self.is_updating = False
        self.update_queue = []
        self.last_scroll_pos = 0
        self.row_height = self.table.verticalHeader().defaultSectionSize()
        
        # Setup virtual scrollbar
        self.virtual_scrollbar = VirtualScrollBar(Qt.Orientation.Vertical, self.table)
        self.virtual_scrollbar.scroll_changed.connect(self.handle_scroll)
        self.table.setVerticalScrollBar(self.virtual_scrollbar)
        
        # Setup update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.process_updates)
        self.update_timer.setInterval(self.UPDATE_INTERVAL)
        
        # Connect signals
        self.table.destroyed.connect(self.cleanup)
        self.table.verticalScrollBar().valueChanged.connect(self.handle_scroll)
        
    def get_cell_value(self, row_data: Dict[str, Any], key: str, formatter: Optional[Callable] = None) -> str:
        """Safely get and format cell value"""
        try:
            if isinstance(key, tuple):
                key, formatter = key
            
            value = row_data.get(key, "")
            
            if formatter:
                try:
                    value = formatter(value)
                except Exception as e:
                    print(f"Error formatting value: {e}")
                    value = str(value)
            else:
                value = str(value)
            
            return value
        except Exception as e:
            print(f"Error getting cell value: {e}")
            return ""
    
    def set_data(self, data: List[Dict[str, Any]], column_mapping: Dict[int, str]):
        """Set new data for the table"""
        self.full_data = data
        self.column_mapping = column_mapping
        self.visible_rows.clear()
        
        # Update scrollbar
        total_height = len(data) * self.row_height
        self.virtual_scrollbar.setRange(0, max(0, total_height - self.table.viewport().height()))
        self.virtual_scrollbar.setPageStep(self.table.viewport().height())
        
        # Set initial table size
        self.table.setRowCount(len(data))
        
        # Load visible rows
        self.update_visible_rows()
        
    def handle_scroll(self, value: int):
        """Handle scroll events and update visible rows"""
        if abs(value - self.last_scroll_pos) < self.row_height:
            return
            
        self.last_scroll_pos = value
        self.update_visible_rows()
        
    def update_visible_rows(self):
        """Update which rows are currently visible"""
        viewport_height = self.table.viewport().height()
        scroll_pos = self.virtual_scrollbar.value()
        
        # Calculate visible range
        start_row = max(0, scroll_pos // self.row_height - self.BUFFER_SIZE)
        end_row = min(len(self.full_data),
                     (scroll_pos + viewport_height) // self.row_height + self.BUFFER_SIZE)
        
        # Update visible rows
        new_visible = set(range(start_row, end_row))
        current_visible = set(self.visible_rows.keys())
        
        # Rows to add/remove
        to_add = new_visible - current_visible
        to_remove = current_visible - new_visible
        
        # Queue updates
        if to_add or to_remove:
            self.queue_update({
                'add': list(to_add),
                'remove': list(to_remove)
            })
            
    def queue_update(self, update_info: Dict[str, List[int]]):
        """Queue an update to be processed"""
        self.update_queue.append(update_info)
        if not self.update_timer.isActive():
            self.update_timer.start()
            
    def process_updates(self):
        """Process queued updates in chunks"""
        if not self.update_queue or self.is_updating:
            return
            
        self.is_updating = True
        update_info = self.update_queue.pop(0)
        
        # Process removals
        for row in update_info.get('remove', []):
            if row in self.visible_rows:
                self.clear_row(row)
                del self.visible_rows[row]
        
        # Process additions in chunks
        to_add = update_info.get('add', [])
        if to_add:
            chunk = to_add[:self.CHUNK_SIZE]
            self.update_rows(chunk)
            
            if len(to_add) > self.CHUNK_SIZE:
                self.queue_update({
                    'add': to_add[self.CHUNK_SIZE:],
                    'remove': []
                })
        
        self.is_updating = False
        
        if not self.update_queue:
            self.update_timer.stop()
            
    def update_rows(self, rows: List[int]):
        """Update specific rows with data"""
        if not self.table:  # Check if table still exists
            return
            
        for row in rows:
            if row >= len(self.full_data):
                continue
                
            row_data = self.full_data[row]
            for col, key in self.column_mapping.items():
                try:
                    value = self.get_cell_value(row_data, key)
                    
                    item = QTableWidgetItem(value)
                    
                    # Apply special formatting
                    if isinstance(key, str) and key in ['amount', 'date']:
                        try:
                            if key == 'amount':
                                item.setData(Qt.ItemDataRole.UserRole, float(str(value).replace(',', '')))
                            elif key == 'date':
                                item.setData(Qt.ItemDataRole.UserRole, datetime.strptime(str(value), "%Y-%m-%d"))
                        except (ValueError, TypeError):
                            pass
                            
                    if self.table:  # Check again before setting item
                        self.table.setItem(row, col, item)
                    
                except Exception as e:
                    print(f"Error updating cell {row}, {col}: {e}")
                    
            self.visible_rows[row] = True
            
    def clear_row(self, row: int):
        """Clear all cells in a row"""
        for col in range(self.table.columnCount()):
            self.table.takeItem(row, col)
            
    def add_formatter(self, key: str, formatter: Callable):
        """Add a custom formatter for a column"""
        self.formatters[key] = formatter
        
    def refresh(self):
        """Refresh all visible rows"""
        self.update_visible_rows()
        
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.update_timer and self.update_timer.isActive():
                self.update_timer.stop()
            
            self.table = None  # Remove reference to table
            self.update_queue.clear()
            self.visible_rows.clear()
            self.full_data.clear()
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    def eventFilter(self, obj, event):
        """Handle viewport events safely"""
        try:
            if self.table and obj is self.table.viewport():
                if event.type() == event.Type.Resize:
                    self.update_visible_rows()
            return super().eventFilter(obj, event)
        except RuntimeError:
            return False  # Object was deleted 