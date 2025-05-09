from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QScrollBar, QWidget, 
                          QVBoxLayout, QProgressDialog, QApplication)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint, QObject, QThread
from PyQt6.QtGui import QColor, QPainter, QPageSize
from PyQt6.QtPrintSupport import QPrinter
from typing import List, Dict, Any, Optional, Callable, Set, Union, Tuple
from datetime import datetime
import weakref
import time
import re
import json
import csv
import threading
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from operator import itemgetter
from functools import reduce
import operator

class TableCache:
    """Cache manager for table data"""
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Any] = {}
        self.max_size = max_size
        self.access_times: Dict[str, float] = {}
        
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        if key in self.cache:
            self.access_times[key] = time.time()
            return self.cache[key]
        return None
        
    def set(self, key: str, value: Any):
        """Set item in cache with LRU eviction"""
        if len(self.cache) >= self.max_size:
            # Remove least recently used items
            oldest = min(self.access_times.items(), key=lambda x: x[1])[0]
            del self.cache[oldest]
            del self.access_times[oldest]
        
        self.cache[key] = value
        self.access_times[key] = time.time()
        
    def clear(self):
        """Clear the cache"""
        self.cache.clear()
        self.access_times.clear()

class VirtualScrollBar(QScrollBar):
    """Custom scrollbar for virtual scrolling"""
    scroll_changed = pyqtSignal(int)
    scroll_finished = pyqtSignal()  # New signal for scroll end
    
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.valueChanged.connect(self.scroll_changed.emit)
        self._last_value = 0
        self._scroll_timer = QTimer()
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.timeout.connect(self.scroll_finished.emit)
        
    def wheelEvent(self, event):
        """Smooth scrolling with mouse wheel"""
        delta = event.angleDelta().y()
        new_value = self.value() - delta // 2
        self.setValue(new_value)
        if new_value != self._last_value:
            self.scroll_changed.emit(new_value)
            self._last_value = new_value
            # Reset scroll end timer
            self._scroll_timer.start(150)

class SearchWorker(QThread):
    """Worker thread for performing searches"""
    result_ready = pyqtSignal(list)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, data: List[Dict], search_text: str, columns: List[str], 
                 case_sensitive: bool = False):
        super().__init__()
        self.data = data
        self.search_text = search_text
        self.columns = columns
        self.case_sensitive = case_sensitive
        self._stop = False
        
    def stop(self):
        self._stop = True
        
    def run(self):
        try:
            results = []
            pattern = re.compile(self.search_text, 
                               re.IGNORECASE if not self.case_sensitive else 0)
            
            for i, row in enumerate(self.data):
                if self._stop:
                    break
                    
                for col in self.columns:
                    value = str(row.get(col, ""))
                    if pattern.search(value):
                        results.append(row)
                        break
                
                # Emit progress every 100 items
                if i % 100 == 0:
                    self.progress_updated.emit(int((i / len(self.data)) * 100))
            
            if not self._stop:
                self.result_ready.emit(results)
                
        except Exception as e:
            print(f"Search error: {e}")

class ExportWorker(QThread):
    """Worker thread for exporting data"""
    progress_updated = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, data: List[Dict], filename: str, format: str):
        super().__init__()
        self.data = data
        self.filename = filename
        self.format = format.lower()
        
    def run(self):
        try:
            if self.format == 'csv':
                self._export_csv()
            elif self.format == 'excel':
                self._export_excel()
            elif self.format == 'json':
                self._export_json()
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))
            
    def _export_csv(self):
        with open(self.filename, 'w', newline='', encoding='utf-8') as f:
            if not self.data:
                return
                
            writer = csv.DictWriter(f, fieldnames=self.data[0].keys())
            writer.writeheader()
            
            for i, row in enumerate(self.data):
                writer.writerow(row)
                if i % 100 == 0:
                    self.progress_updated.emit(int((i / len(self.data)) * 100))
                    
    def _export_excel(self):
        df = pd.DataFrame(self.data)
        df.to_excel(self.filename, index=False)
        self.progress_updated.emit(100)
        
    def _export_json(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        self.progress_updated.emit(100)

class AdvancedFilter:
    """Advanced filter with compound conditions"""
    
    def __init__(self):
        self.conditions = []
        
    def add_condition(self, field: str, operator: str, value: Any):
        """Add a filter condition"""
        self.conditions.append((field, operator, value))
        
    def matches(self, item: Dict[str, Any]) -> bool:
        """Check if item matches all conditions"""
        return all(self._evaluate_condition(item, field, op, value)
                  for field, op, value in self.conditions)
                  
    def _evaluate_condition(self, item: Dict[str, Any], 
                          field: str, op: str, value: Any) -> bool:
        """Evaluate a single condition"""
        item_value = item.get(field)
        
        if op == '=':
            return item_value == value
        elif op == '!=':
            return item_value != value
        elif op == '>':
            return item_value > value
        elif op == '<':
            return item_value < value
        elif op == '>=':
            return item_value >= value
        elif op == '<=':
            return item_value <= value
        elif op == 'contains':
            return str(value).lower() in str(item_value).lower()
        elif op == 'starts_with':
            return str(item_value).lower().startswith(str(value).lower())
        elif op == 'ends_with':
            return str(item_value).lower().endswith(str(value).lower())
        elif op == 'in':
            return item_value in value
        elif op == 'between':
            if isinstance(value, (list, tuple)) and len(value) == 2:
                return value[0] <= item_value <= value[1]
        return False

class MultiSortKey:
    """Handle multiple column sorting"""
    
    def __init__(self, columns: List[Tuple[str, bool]]):
        """Initialize with list of (column, reverse) tuples"""
        self.columns = columns
        
    def __call__(self, item: Dict[str, Any]) -> tuple:
        """Get sort key tuple for item"""
        result = []
        for col, reverse in self.columns:
            value = item.get(col)
            
            # Handle different types
            if isinstance(value, (int, float)):
                key = (0, value)
            elif isinstance(value, datetime):
                key = (1, value.timestamp())
            else:
                key = (2, str(value).lower())
                
            result.append(key if not reverse else self._invert_key(key))
            
        return tuple(result)
        
    def _invert_key(self, key: tuple) -> tuple:
        """Invert a key for reverse sorting"""
        return (key[0], self._invert_value(key[1]))
        
    def _invert_value(self, value: Any) -> Any:
        """Invert a value for reverse sorting"""
        if isinstance(value, (int, float)):
            return float('-inf') if value == float('inf') else float('inf') if value == float('-inf') else -value
        return value

class PDFExporter(QThread):
    """Export table data to PDF"""
    
    progress_updated = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, data: List[Dict], headers: List[str], 
                 filename: str, title: str = ""):
        super().__init__()
        self.data = data
        self.headers = headers
        self.filename = filename
        self.title = title
        
    def run(self):
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(self.filename)
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            
            painter = QPainter()
            if not painter.begin(printer):
                raise Exception("Could not open PDF file for writing")
                
            try:
                self._draw_pdf(painter, printer)
            finally:
                painter.end()
                
            self.finished.emit(True, "")
            
        except Exception as e:
            self.finished.emit(False, str(e))
            
    def _draw_pdf(self, painter: QPainter, printer: QPrinter):
        """Draw the PDF content"""
        # Configure text options
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)
        
        # Calculate dimensions
        page_rect = printer.pageRect()
        margin = 40
        available_width = page_rect.width() - 2 * margin
        row_height = 30
        col_width = available_width / len(self.headers)
        
        # Start position
        x = margin
        y = margin
        
        # Draw title if provided
        if self.title:
            font.setPointSize(16)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(x, y, self.title)
            y += row_height * 2
            font.setPointSize(12)
            font.setBold(False)
            painter.setFont(font)
        
        # Draw headers
        for header in self.headers:
            painter.drawText(x, y, col_width, row_height, 
                           Qt.AlignmentFlag.AlignCenter, header)
            x += col_width
        y += row_height
        
        # Draw data
        rows_per_page = int((page_rect.height() - y) / row_height)
        current_row = 0
        
        for i, row_data in enumerate(self.data):
            # New page if needed
            if current_row >= rows_per_page:
                printer.newPage()
                y = margin
                current_row = 0
            
            x = margin
            for header in self.headers:
                value = str(row_data.get(header, ""))
                painter.drawText(x, y, col_width, row_height,
                               Qt.AlignmentFlag.AlignCenter, value)
                x += col_width
            
            y += row_height
            current_row += 1
            
            # Update progress
            if i % 10 == 0:
                self.progress_updated.emit(int((i / len(self.data)) * 100))

class OptimizedTableManager(QObject):
    """Manages table data with virtual scrolling and efficient updates"""
    
    data_changed = pyqtSignal()  # New signal for data changes
    loading_changed = pyqtSignal(bool)  # Signal for loading state
    
    _instances = weakref.WeakValueDictionary()
    
    BUFFER_SIZE = 50  # Number of extra rows to load above/below visible area
    UPDATE_INTERVAL = 50  # Reduced from 100 to 50ms for smoother updates
    CHUNK_SIZE = 30  # Increased from 20 to 30 for better performance
    CACHE_SIZE = 1000  # Maximum number of cached items
    
    @classmethod
    def get_instance(cls, table_widget: QTableWidget) -> 'OptimizedTableManager':
        if table_widget not in cls._instances:
            cls._instances[table_widget] = cls(table_widget)
        return cls._instances[table_widget]
    
    def __init__(self, table_widget: QTableWidget):
        super().__init__(table_widget)
        self.table = table_widget
        self.full_data: List[Dict[str, Any]] = []
        self.visible_rows: Dict[int, bool] = {}
        self.column_mapping: Dict[int, str] = {}
        self.formatters: Dict[str, Callable] = {}
        self.is_updating = False
        self.update_queue = []
        self.last_scroll_pos = 0
        self.row_height = self.table.verticalHeader().defaultSectionSize()
        
        # Initialize cache
        self.cache = TableCache(self.CACHE_SIZE)
        
        # Performance optimizations
        self.table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setShowGrid(False)  # Disable grid for better performance
        
        # Setup virtual scrollbar
        self.virtual_scrollbar = VirtualScrollBar(Qt.Orientation.Vertical, self.table)
        self.virtual_scrollbar.scroll_changed.connect(self.handle_scroll)
        self.virtual_scrollbar.scroll_finished.connect(self.on_scroll_finished)
        self.table.setVerticalScrollBar(self.virtual_scrollbar)
        
        # Batch update timer with dynamic interval
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.process_updates)
        self.update_timer.setInterval(self.UPDATE_INTERVAL)
        
        # Track pending updates for optimization
        self.pending_updates: Set[int] = set()
        
        # Connect signals
        self.table.destroyed.connect(self.cleanup)
        self.table.verticalScrollBar().valueChanged.connect(self.handle_scroll)
        
        # Install event filter for resize events
        self.table.viewport().installEventFilter(self)
        
    def get_cell_value(self, row_data: Dict[str, Any], key: str, formatter: Optional[Callable] = None) -> str:
        """Safely get and format cell value with caching"""
        cache_key = f"{id(row_data)}_{key}"
        cached_value = self.cache.get(cache_key)
        if cached_value is not None:
            return cached_value
            
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
            
            # Cache the formatted value
            self.cache.set(cache_key, value)
            return value
            
        except Exception as e:
            print(f"Error getting cell value: {e}")
            return ""
    
    def on_scroll_finished(self):
        """Handle end of scrolling"""
        self.update_visible_rows(force=True)
        
    def set_data(self, data: List[Dict[str, Any]], column_mapping: Dict[int, str]):
        """Set new data for the table with improved performance"""
        self.loading_changed.emit(True)
        try:
            self.full_data = data
            self.column_mapping = column_mapping
            self.visible_rows.clear()
            self.cache.clear()
            self.pending_updates.clear()
            
            # Update scrollbar
            total_height = len(data) * self.row_height
            self.virtual_scrollbar.setRange(0, max(0, total_height - self.table.viewport().height()))
            self.virtual_scrollbar.setPageStep(self.table.viewport().height())
            
            # Set initial table size
            self.table.setRowCount(len(data))
            
            # Load visible rows
            self.update_visible_rows(force=True)
            
            # Emit data changed signal
            self.data_changed.emit()
            
        finally:
            self.loading_changed.emit(False)
    
    def handle_scroll(self, value: int):
        """Handle scroll events with improved smoothness"""
        if not self.is_updating and abs(value - self.last_scroll_pos) >= self.row_height:
            self.last_scroll_pos = value
            self.update_visible_rows()
    
    def update_visible_rows(self, force: bool = False):
        """Update which rows are currently visible with improved efficiency"""
        if self.is_updating and not force:
            return
            
        viewport_height = self.table.viewport().height()
        scroll_pos = self.virtual_scrollbar.value()
        
        # Calculate visible range with improved buffering
        start_row = max(0, scroll_pos // self.row_height - self.BUFFER_SIZE)
        end_row = min(len(self.full_data),
                     (scroll_pos + viewport_height) // self.row_height + self.BUFFER_SIZE)
        
        # Update visible rows with set operations for better performance
        new_visible = set(range(start_row, end_row))
        current_visible = set(self.visible_rows.keys())
        
        # Only update if there are actual changes
        if force or new_visible != current_visible:
            to_add = new_visible - current_visible
            to_remove = current_visible - new_visible
            
            if to_add or to_remove:
                self.queue_update({
                    'add': sorted(list(to_add)),  # Sort for more efficient updates
                    'remove': sorted(list(to_remove), reverse=True)  # Remove from bottom up
                })
    
    def queue_update(self, update_info: Dict[str, List[int]]):
        """Queue an update with improved batching"""
        # Merge with existing updates if possible
        if self.update_queue:
            last_update = self.update_queue[-1]
            last_update['add'].extend(update_info['add'])
            last_update['remove'].extend(update_info['remove'])
            # Remove duplicates and sort
            last_update['add'] = sorted(set(last_update['add']))
            last_update['remove'] = sorted(set(last_update['remove']), reverse=True)
        else:
            self.update_queue.append(update_info)
        
        if not self.update_timer.isActive():
            self.update_timer.start()
    
    def process_updates(self):
        """Process queued updates with improved efficiency"""
        if not self.update_queue or self.is_updating:
            return
            
        self.is_updating = True
        try:
            update_info = self.update_queue.pop(0)
            
            # Process removals first (from bottom up)
            for row in update_info.get('remove', []):
                if row in self.visible_rows:
                    self.clear_row(row)
                    del self.visible_rows[row]
            
            # Process additions in optimized chunks
            to_add = update_info.get('add', [])
            if to_add:
                chunk = to_add[:self.CHUNK_SIZE]
                self.update_rows(chunk)
                
                if len(to_add) > self.CHUNK_SIZE:
                    remaining = to_add[self.CHUNK_SIZE:]
                    self.queue_update({
                        'add': remaining,
                        'remove': []
                    })
            
        finally:
            self.is_updating = False
            
        if not self.update_queue:
            self.update_timer.stop()
    
    def update_rows(self, rows: List[int]):
        """Update specific rows with improved error handling and caching"""
        if not self.table:
            return
            
        self.table.setUpdatesEnabled(False)
        try:
            for row in rows:
                if row >= len(self.full_data):
                    continue
                    
                row_data = self.full_data[row]
                for col, key in self.column_mapping.items():
                    try:
                        # Get cached or computed value
                        value = self.get_cell_value(row_data, key)
                        
                        # Create item only if needed
                        current_item = self.table.item(row, col)
                        if current_item is None or current_item.text() != value:
                            item = QTableWidgetItem(value)
                            
                            # Apply special formatting
                            if isinstance(key, str):
                                if key == 'amount':
                                    try:
                                        item.setData(Qt.ItemDataRole.UserRole, 
                                                   float(str(value).replace(',', '')))
                                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | 
                                                           Qt.AlignmentFlag.AlignVCenter)
                                    except (ValueError, TypeError):
                                        pass
                                elif key == 'date':
                                    try:
                                        item.setData(Qt.ItemDataRole.UserRole,
                                                   datetime.strptime(str(value), "%Y-%m-%d"))
                                    except (ValueError, TypeError):
                                        pass
                                elif key in ['status', 'state']:
                                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                            
                            if self.table:
                                self.table.setItem(row, col, item)
                        
                    except Exception as e:
                        print(f"Error updating cell {row}, {col}: {e}")
                        
                self.visible_rows[row] = True
                
        finally:
            if self.table:
                self.table.setUpdatesEnabled(True)
    
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
        """Clean up resources with improved memory management"""
        try:
            if self.update_timer and self.update_timer.isActive():
                self.update_timer.stop()
            
            # Clear all data structures
            self.table = None
            self.update_queue.clear()
            self.visible_rows.clear()
            self.full_data.clear()
            self.pending_updates.clear()
            self.cache.clear()
            
            # Remove instance from class dictionary
            for key, value in list(self._instances.items()):
                if value is self:
                    del self._instances[key]
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    def eventFilter(self, obj, event):
        """Handle viewport events with improved error handling"""
        try:
            if self.table and obj is self.table.viewport():
                if event.type() == event.Type.Resize:
                    QTimer.singleShot(100, lambda: self.update_visible_rows(force=True))
            return super().eventFilter(obj, event)
        except RuntimeError:
            return False  # Object was deleted

    def sort_by_column(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        """Sort table by column with improved performance"""
        if not self.full_data:
            return
            
        key = self.column_mapping.get(column)
        if not key:
            return
            
        self.loading_changed.emit(True)
        try:
            # Get sort key function
            def get_sort_key(item):
                if isinstance(key, tuple):
                    k, _ = key
                else:
                    k = key
                    
                value = item.get(k)
                
                # Handle special cases
                if k == 'amount':
                    try:
                        return float(str(value).replace(',', ''))
                    except (ValueError, TypeError):
                        return 0
                elif k == 'date':
                    try:
                        return datetime.strptime(str(value), "%Y-%m-%d")
                    except (ValueError, TypeError):
                        return datetime.min
                        
                return str(value).lower()
            
            # Sort data
            self.full_data.sort(
                key=get_sort_key,
                reverse=(order == Qt.SortOrder.DescendingOrder)
            )
            
            # Reset view
            self.visible_rows.clear()
            self.cache.clear()
            self.update_visible_rows(force=True)
            
        finally:
            self.loading_changed.emit(False)
    
    def filter_data(self, filter_func: Callable[[Dict[str, Any]], bool]):
        """Filter table data with callback"""
        if not self.full_data:
            return
            
        self.loading_changed.emit(True)
        try:
            filtered_data = [row for row in self.full_data if filter_func(row)]
            self.set_data(filtered_data, self.column_mapping)
        finally:
            self.loading_changed.emit(False)
    
    def export_to_csv(self, filename: str):
        """Export table data to CSV"""
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write headers
            headers = []
            for col in range(self.table.columnCount()):
                headers.append(self.table.horizontalHeaderItem(col).text())
            writer.writerow(headers)
            
            # Write data
            for row_data in self.full_data:
                row = []
                for col, key in self.column_mapping.items():
                    value = self.get_cell_value(row_data, key)
                    row.append(value)
                writer.writerow(row)

    def quick_search(self, search_text: str, case_sensitive: bool = False):
        """Perform quick search across all columns"""
        if not search_text:
            self.reset_filter()
            return
            
        self.loading_changed.emit(True)
        
        # Create and start search worker
        self.search_worker = SearchWorker(
            self.full_data,
            search_text,
            [key[0] if isinstance(key, tuple) else key 
             for key in self.column_mapping.values()],
            case_sensitive
        )
        
        # Create progress dialog
        progress = QProgressDialog("جاري البحث...", "إلغاء", 0, 100)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        # Connect signals
        self.search_worker.result_ready.connect(
            lambda results: self._handle_search_results(results, progress))
        self.search_worker.progress_updated.connect(progress.setValue)
        progress.canceled.connect(self.search_worker.stop)
        
        self.search_worker.start()
        
    def _handle_search_results(self, results: List[Dict], progress: QProgressDialog):
        """Handle search results"""
        progress.close()
        self.set_data(results, self.column_mapping)
        self.loading_changed.emit(False)
        
    def reset_filter(self):
        """Reset to original data"""
        if hasattr(self, '_original_data'):
            self.set_data(self._original_data, self.column_mapping)
            
    def export_data(self, filename: str, format: str = 'csv'):
        """Export data with progress tracking"""
        # Create and start export worker
        self.export_worker = ExportWorker(self.full_data, filename, format)
        
        # Create progress dialog
        progress = QProgressDialog("جاري التصدير...", "إلغاء", 0, 100)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        # Connect signals
        self.export_worker.progress_updated.connect(progress.setValue)
        self.export_worker.finished.connect(
            lambda success, error: self._handle_export_finished(success, error, progress))
        
        self.export_worker.start()
        
    def _handle_export_finished(self, success: bool, error: str, 
                              progress: QProgressDialog):
        """Handle export completion"""
        progress.close()
        if not success:
            QApplication.beep()
            print(f"Export error: {error}")
            
    def highlight_search(self, text: str, color: QColor = QColor(255, 255, 0, 100)):
        """Highlight search matches in the table"""
        if not text:
            return
            
        pattern = re.compile(text, re.IGNORECASE)
        
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and pattern.search(item.text()):
                    item.setBackground(color)
                else:
                    item.setBackground(QColor(0, 0, 0, 0))
                    
    def clear_highlights(self):
        """Clear all search highlights"""
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QColor(0, 0, 0, 0))
                    
    def set_column_colors(self, column: int, 
                         color_func: Callable[[str], QColor]):
        """Set column colors based on cell values"""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, column)
            if item:
                color = color_func(item.text())
                item.setForeground(color)
                
    def set_conditional_formatting(self, column: int, 
                                 condition: Callable[[str], bool],
                                 true_color: QColor,
                                 false_color: QColor = QColor(0, 0, 0)):
        """Apply conditional formatting to a column"""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, column)
            if item:
                color = true_color if condition(item.text()) else false_color
                item.setForeground(color)
                
    def batch_update(self, updates: List[Dict[str, Any]]):
        """Perform batch updates efficiently"""
        if not updates:
            return
            
        self.loading_changed.emit(True)
        try:
            # Create ID to index mapping for faster lookups
            id_to_index = {row.get('id'): i for i, row in enumerate(self.full_data)}
            
            # Process updates in batches
            batch_size = 50
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i + batch_size]
                
                for update in batch:
                    if 'id' not in update:
                        continue
                        
                    idx = id_to_index.get(update['id'])
                    if idx is not None:
                        # Update data
                        self.full_data[idx].update(update)
                        
                        # Update visible row if needed
                        if idx in self.visible_rows:
                            self.update_rows([idx])
                            
        finally:
            self.loading_changed.emit(False)
            
    def get_selected_data(self) -> List[Dict[str, Any]]:
        """Get data for selected rows"""
        selected_rows = set(item.row() for item in self.table.selectedItems())
        return [self.full_data[row] for row in selected_rows if row < len(self.full_data)]
        
    def copy_selected_to_clipboard(self):
        """Copy selected cells to clipboard in a table format"""
        selected = self.table.selectedItems()
        if not selected:
            return
            
        # Get bounds of selection
        rows = set(item.row() for item in selected)
        cols = set(item.column() for item in selected)
        min_row, max_row = min(rows), max(rows)
        min_col, max_col = min(cols), max(cols)
        
        # Build table string
        table = []
        for row in range(min_row, max_row + 1):
            row_data = []
            for col in range(min_col, max_col + 1):
                item = self.table.item(row, col)
                row_data.append(item.text() if item else "")
            table.append("\t".join(row_data))
            
        # Copy to clipboard
        QApplication.clipboard().setText("\n".join(table))
        
    def set_row_colors(self, color_func: Callable[[Dict[str, Any]], QColor]):
        """Set row background colors based on data"""
        for row, data in enumerate(self.full_data):
            if row in self.visible_rows:
                color = color_func(data)
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(color)

    def apply_advanced_filter(self, filter_obj: AdvancedFilter):
        """Apply advanced filter to data"""
        if not self.full_data:
            return
            
        self.loading_changed.emit(True)
        try:
            # Store original data if not already stored
            if not hasattr(self, '_original_data'):
                self._original_data = self.full_data.copy()
                
            # Apply filter
            filtered_data = [
                item for item in self._original_data
                if filter_obj.matches(item)
            ]
            
            self.set_data(filtered_data, self.column_mapping)
            
        finally:
            self.loading_changed.emit(False)
            
    def multi_column_sort(self, sort_specs: List[Tuple[int, Qt.SortOrder]]):
        """Sort by multiple columns"""
        if not self.full_data:
            return
            
        self.loading_changed.emit(True)
        try:
            # Convert column indices to field names
            sort_columns = [
                (self.column_mapping[col], order == Qt.SortOrder.DescendingOrder)
                for col, order in sort_specs
            ]
            
            # Create sort key
            key_func = MultiSortKey(sort_columns)
            
            # Sort data
            self.full_data.sort(key=key_func)
            
            # Reset view
            self.visible_rows.clear()
            self.cache.clear()
            self.update_visible_rows(force=True)
            
        finally:
            self.loading_changed.emit(False)
            
    def export_to_pdf(self, filename: str, title: str = ""):
        """Export data to PDF with progress tracking"""
        # Get headers from column mapping
        headers = []
        for i in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(i)
            if header_item:
                headers.append(header_item.text())
            
        # Create and start PDF export worker
        self.pdf_worker = PDFExporter(self.full_data, headers, filename, title)
        
        # Create progress dialog
        progress = QProgressDialog("جاري التصدير إلى PDF...", "إلغاء", 0, 100)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        # Connect signals
        self.pdf_worker.progress_updated.connect(progress.setValue)
        self.pdf_worker.finished.connect(
            lambda success, error: self._handle_export_finished(success, error, progress)
        )
        
        self.pdf_worker.start()
        
    def create_summary(self, group_by: str, 
                      aggregations: Dict[str, List[str]]) -> Dict:
        """Create data summary with grouping and aggregations"""
        if not self.full_data:
            return {}
            
        # Group data
        groups = {}
        for item in self.full_data:
            key = item.get(group_by)
            if key not in groups:
                groups[key] = []
            groups[key].append(item)
            
        # Calculate aggregations
        result = {}
        for key, group in groups.items():
            group_result = {'count': len(group)}
            
            for field, funcs in aggregations.items():
                values = [item.get(field, 0) for item in group]
                
                for func in funcs:
                    if func == 'sum':
                        group_result[f'{field}_sum'] = sum(values)
                    elif func == 'avg':
                        group_result[f'{field}_avg'] = sum(values) / len(values)
                    elif func == 'min':
                        group_result[f'{field}_min'] = min(values)
                    elif func == 'max':
                        group_result[f'{field}_max'] = max(values)
                        
            result[key] = group_result
            
        return result
        
    def set_column_format(self, column: int, format_type: str, 
                         format_spec: str = ""):
        """Set column format for display"""
        if not self.table:
            return
            
        for row in range(self.table.rowCount()):
            item = self.table.item(row, column)
            if not item:
                continue
                
            try:
                value = item.text()
                
                if format_type == 'number':
                    formatted = format(float(value), format_spec)
                elif format_type == 'date':
                    date_obj = datetime.strptime(value, format_spec)
                    formatted = date_obj.strftime(format_spec)
                elif format_type == 'currency':
                    formatted = f"{float(value):,.2f} {format_spec}"
                else:
                    formatted = value
                    
                item.setText(formatted)
                
            except (ValueError, TypeError):
                continue 