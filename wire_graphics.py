"""
Graphical representation of wire connections.
"""

from __future__ import annotations
from typing import Tuple, TYPE_CHECKING, Optional
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsItem
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QPen, QPainterPath
from config import (COLOR_WIRE_LOW, COLOR_WIRE_HIGH, COLOR_SELECTED, HIGH, logger)
from circuit import Connection

if TYPE_CHECKING:
    from gate_graphics import GateGraphicsItem


class WireGraphicsItem(QGraphicsPathItem):
    """Graphical representation of a wire connection.
    
    Draws an S-curve between connected pins and updates color based on signal state.
    """
    
    def __init__(self, src_gate: 'GateGraphicsItem', src_pin: str,
                 dst_gate: 'GateGraphicsItem', dst_pin: str,
                 connection_info: Connection):
        super().__init__()
        
        # Store connection info for recovery
        self.connection_info: Connection = connection_info
        self.src_pin: str = src_pin
        self.dst_pin: str = dst_pin
        
        # Use weak references to avoid holding deleted objects
        self._src_gate_ref = None
        self._dst_gate_ref = None
        
        try:
            # Validate gates before storing
            if src_gate is None or dst_gate is None:
                logger.error("Cannot create wire with None gate references")
                self._is_valid = False
            elif src_gate.scene() is None or dst_gate.scene() is None:
                logger.error("Cannot create wire with gates not in scene")
                self._is_valid = False
            else:
                self._src_gate_ref = src_gate
                self._dst_gate_ref = dst_gate
                self._is_valid = True
        except RuntimeError as e:
            # C++ object already deleted
            logger.error(f"RuntimeError creating wire: {e}")
            self._is_valid = False
        
        self._base_width: float = 3.0
        self._hover_width: float = 5.0
        
        self.setPen(QPen(COLOR_WIRE_LOW, self._base_width))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setZValue(0)
        self.setAcceptHoverEvents(True)
        
        if self._is_valid:
            self.update_path()
            logger.debug(f"Created wire: {self._get_wire_description()}")
    
    @property
    def src_gate(self) -> Optional['GateGraphicsItem']:
        """Safely get source gate, returning None if deleted."""
        try:
            if self._src_gate_ref is not None:
                # Test if C++ object still exists
                _ = self._src_gate_ref.scene()
                return self._src_gate_ref
        except RuntimeError:
            logger.debug("Source gate C++ object deleted")
            self._src_gate_ref = None
            self._is_valid = False
        except Exception as e:
            logger.debug(f"Error accessing source gate: {e}")
        return None
    
    @property
    def dst_gate(self) -> Optional['GateGraphicsItem']:
        """Safely get destination gate, returning None if deleted."""
        try:
            if self._dst_gate_ref is not None:
                # Test if C++ object still exists
                _ = self._dst_gate_ref.scene()
                return self._dst_gate_ref
        except RuntimeError:
            logger.debug("Destination gate C++ object deleted")
            self._dst_gate_ref = None
            self._is_valid = False
        except Exception as e:
            logger.debug(f"Error accessing destination gate: {e}")
        return None
    
    def _get_wire_description(self) -> str:
        """Get a safe string description of this wire."""
        try:
            src = self.src_gate
            dst = self.dst_gate
            src_name = src.component.name if src and hasattr(src, 'component') and src.component else "?"
            dst_name = dst.component.name if dst and hasattr(dst, 'component') and dst.component else "?"
            return f"{src_name}.{self.src_pin} -> {dst_name}.{self.dst_pin}"
        except Exception:
            return f"{self.src_pin} -> {self.dst_pin} (refs lost)"
    
    def update_path(self) -> bool:
        """Update the wire path based on pin positions.
        
        Returns:
            True if path was updated successfully
        """
        if not self._is_valid:
            return False
            
        src = self.src_gate
        dst = self.dst_gate
        
        if src is None or dst is None:
            self._is_valid = False
            return False
        
        try:
            start = src.get_output_pin_scene_pos(self.src_pin)
            end = dst.get_input_pin_scene_pos(self.dst_pin)
        except KeyError:
            self._is_valid = False
            logger.warning(f"Wire path update failed - invalid pins: {self._get_wire_description()}")
            return False
        except RuntimeError as e:
            self._is_valid = False
            logger.warning(f"Wire path update failed - C++ error: {e}")
            return False
        except AttributeError:
            self._is_valid = False
            logger.warning(f"Wire path update failed - gate removed: {self._get_wire_description()}")
            return False
        
        try:
            path = self._calculate_path(start, end)
            self.setPath(path)
            return True
        except RuntimeError as e:
            logger.error(f"RuntimeError setting wire path: {e}")
            self._is_valid = False
            return False
    
    def _calculate_path(self, start: QPointF, end: QPointF) -> QPainterPath:
        """Calculate a smooth S-curve path between two points."""
        path = QPainterPath()
        path.moveTo(start)
        
        dx = abs(end.x() - start.x())
        
        if dx < 20:
            # Very close - use arc with larger control offset
            control_offset = max(50, dx * 0.5)
            path.cubicTo(
                QPointF(start.x() + control_offset, start.y()),
                QPointF(end.x() - control_offset, end.y()),
                end
            )
        else:
            # Standard S-curve
            mid_x = (start.x() + end.x()) / 2
            path.cubicTo(
                QPointF(mid_x, start.y()),
                QPointF(mid_x, end.y()),
                end
            )
        
        return path
    
    def update_color(self) -> bool:
        """Update wire color based on signal state.
        
        Returns:
            True if color was updated successfully
        """
        if not self._is_valid:
            return False
            
        src = self.src_gate
        if src is None:
            return False
        
        try:
            component = src.component
            if component is None:
                return False
                
            output_pin = component.outputs.get(self.src_pin)
            if output_pin is None:
                return False
                
            if output_pin.value == HIGH:
                self.setPen(QPen(COLOR_WIRE_HIGH, self._base_width))
            else:
                self.setPen(QPen(COLOR_WIRE_LOW, self._base_width))
            self.update()
            return True
        except RuntimeError as e:
            logger.debug(f"RuntimeError updating wire color: {e}")
            self._is_valid = False
            return False
        except (KeyError, AttributeError) as e:
            logger.debug(f"Error updating wire color: {e}")
            return False
    
    def hoverEnterEvent(self, event) -> None:
        """Highlight wire on hover."""
        if not self._is_valid:
            event.ignore()
            return
        try:
            pen = self.pen()
            pen.setWidth(self._hover_width)
            self.setPen(pen)
            super().hoverEnterEvent(event)
        except RuntimeError:
            event.ignore()
    
    def hoverLeaveEvent(self, event) -> None:
        """Reset wire width on leave."""
        if not self._is_valid:
            event.ignore()
            return
        try:
            pen = self.pen()
            pen.setWidth(self._base_width)
            self.setPen(pen)
            super().hoverLeaveEvent(event)
        except RuntimeError:
            event.ignore()
    
    def paint(self, painter: QPainter, option, widget) -> None:
        """Paint the wire with selection highlight."""
        if not self._is_valid:
            return
        try:
            if self.isSelected():
                pen = self.pen()
                pen.setColor(COLOR_SELECTED)
                pen.setWidth(self._hover_width)
                self.setPen(pen)
            super().paint(painter, option, widget)
        except RuntimeError:
            pass
    
    def get_connection_tuple(self) -> Connection:
        """Get the connection as a tuple."""
        return self.connection_info
    
    def is_valid(self) -> bool:
        """Check if the wire is still valid (gates and pins exist)."""
        if not self._is_valid:
            return False
        
        # Check if gates are still accessible
        src = self.src_gate
        dst = self.dst_gate
        
        if src is None or dst is None:
            self._is_valid = False
            return False
        
        try:
            src.get_output_pin_scene_pos(self.src_pin)
            dst.get_input_pin_scene_pos(self.dst_pin)
            return True
        except (KeyError, AttributeError, RuntimeError):
            self._is_valid = False
            return False
    
    def invalidate(self) -> None:
        """Mark this wire as invalid and clear references."""
        self._is_valid = False
        self._src_gate_ref = None
        self._dst_gate_ref = None
        logger.debug(f"Wire invalidated: {self._get_wire_description()}")
    
    def __repr__(self) -> str:
        return f"Wire({self._get_wire_description()})"