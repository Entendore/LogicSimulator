"""
Circuit scene and view classes.
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from PySide6.QtWidgets import (QGraphicsScene, QGraphicsView, 
                               QGraphicsPathItem, QMenu)
from PySide6.QtGui import (QPainter, QPen, QBrush, QColor, QPainterPath, 
                           QMouseEvent)
from PySide6.QtCore import Qt, QPointF, QRectF, QLineF, Signal
from config import (ComponentType, PinType, COLOR_WIRE_LOW, COLOR_SELECTED,
                   COLOR_GRID, COLOR_BACKGROUND, GRID_SIZE,
                   MIN_ZOOM, MAX_ZOOM, ZOOM_FACTOR, logger)
from circuit import Circuit
from gates import create_component
from gate_graphics import GateGraphicsItem, GATE_GRAPHICS_MAP
from pin_graphics import PinGraphicsItem
from wire_graphics import WireGraphicsItem


class CircuitScene(QGraphicsScene):
    """Main scene for the circuit editor."""
    
    circuit_changed = Signal()
    simulation_updated = Signal()
    selection_changed_signal = Signal(object)
    component_placed = Signal(object)
    
    def __init__(self, circuit: Circuit):
        super().__init__()
        self.circuit: Circuit = circuit
        self.gate_items: Dict[str, GateGraphicsItem] = {}
        self.wire_items: List[WireGraphicsItem] = []
        
        # Wire drawing state
        self._drawing_wire: bool = False
        self._wire_start_gate: Optional[GateGraphicsItem] = None
        self._wire_start_pin: Optional[str] = None
        self._wire_start_type: Optional[PinType] = None
        self._temp_wire: Optional[QGraphicsPathItem] = None
        self._mouse_pos: QPointF = QPointF()
        
        # Grid settings
        self.grid_size: int = GRID_SIZE
        self.show_grid: bool = True
        
        self.setBackgroundBrush(QBrush(COLOR_BACKGROUND))
        self.setSceneRect(-2000, -2000, 4000, 4000)
        
        logger.debug("CircuitScene initialized")
    
    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        """Draw grid background."""
        super().drawBackground(painter, rect)
        
        if not self.show_grid:
            return
        
        painter.setPen(QPen(COLOR_GRID, 0.5))
        
        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)
        
        lines: List[QLineF] = []
        x = left
        while x <= rect.right():
            lines.append(QLineF(x, rect.top(), x, rect.bottom()))
            x += self.grid_size
        
        y = top
        while y <= rect.bottom():
            lines.append(QLineF(rect.left(), y, rect.right(), y))
            y += self.grid_size
        
        painter.drawLines(lines)
    
    def add_gate(self, comp_type: ComponentType, 
                 pos: QPointF) -> Optional[GateGraphicsItem]:
        """Add a new gate to the scene."""
        name = self.circuit.generate_name(comp_type)
        
        try:
            comp = create_component(comp_type, name)
        except ValueError as e:
            logger.error(f"Failed to create component: {e}")
            return None
        
        self.circuit.add_component(comp)
        
        graphics_class = GATE_GRAPHICS_MAP.get(comp_type, GateGraphicsItem)
        gate_item = graphics_class(comp, pos.x(), pos.y())
        self.addItem(gate_item)
        self.gate_items[name] = gate_item
        
        logger.info(f"Placed {comp_type.value} gate: {name} at ({pos.x():.0f}, {pos.y():.0f})")
        
        self.circuit_changed.emit()
        self.component_placed.emit(comp_type)
        return gate_item
    
    def remove_gate(self, name: str) -> bool:
        """Remove a gate from the scene."""
        if name not in self.gate_items:
            logger.warning(f"Attempted to remove non-existent gate: {name}")
            return False
        
        gate_item = self.gate_items[name]
        
        # Invalidate and remove connected wires first
        wires_to_remove = [
            w for w in self.wire_items 
            if w.src_gate == gate_item or w.dst_gate == gate_item
        ]
        
        for wire in wires_to_remove:
            wire.invalidate()
            self._remove_wire_internal(wire)
        
        # Invalidate the gate before removing
        gate_item.invalidate()
        
        try:
            self.removeItem(gate_item)
        except RuntimeError as e:
            logger.warning(f"Error removing gate item: {e}")
        
        del self.gate_items[name]
        self.circuit.remove_component(name)
        
        logger.info(f"Removed gate: {name}")
        self.circuit_changed.emit()
        return True
    
    def add_wire(self, src_gate_name: str, src_pin: str,
                 dst_gate_name: str, dst_pin: str) -> Optional[WireGraphicsItem]:
        """Add a wire connection."""
        if src_gate_name not in self.gate_items:
            logger.error(f"Source gate not found: {src_gate_name}")
            return None
        if dst_gate_name not in self.gate_items:
            logger.error(f"Destination gate not found: {dst_gate_name}")
            return None
        
        src_gate = self.gate_items[src_gate_name]
        dst_gate = self.gate_items[dst_gate_name]
        
        # Validate gates are still in scene
        if not src_gate.is_gate_valid() or not dst_gate.is_gate_valid():
            logger.error("Cannot create wire - gate(s) invalid")
            return None
        
        try:
            self.circuit.connect(src_gate_name, src_pin, dst_gate_name, dst_pin)
        except ValueError as e:
            logger.warning(f"Connection failed: {e}")
            return None
        
        conn_info = (src_gate_name, src_pin, dst_gate_name, dst_pin)
        wire = WireGraphicsItem(src_gate, src_pin, dst_gate, dst_pin, conn_info)
        
        if not wire.is_valid():
            logger.error("Failed to create valid wire")
            self.circuit.disconnect(src_gate_name, src_pin, dst_gate_name, dst_pin)
            return None
        
        self.addItem(wire)
        self.wire_items.append(wire)
        
        self.circuit_changed.emit()
        self.simulate()
        return wire
    
    def remove_wire(self, wire: WireGraphicsItem) -> bool:
        """Remove a wire connection."""
        wire.invalidate()
        result = self._remove_wire_internal(wire)
        if result:
            self.circuit_changed.emit()
            self.simulate()
        return result
    
    def _remove_wire_internal(self, wire: WireGraphicsItem) -> bool:
        """Internal wire removal without emitting signals."""
        if wire.connection_info:
            src_name, src_pin, dst_name, dst_pin = wire.connection_info
            self.circuit.disconnect(src_name, src_pin, dst_name, dst_pin)
        
        wire.invalidate()
        
        if wire in self.wire_items:
            self.wire_items.remove(wire)
        
        try:
            if wire.scene() == self:
                self.removeItem(wire)
        except RuntimeError:
            pass
        
        return True
    
    def simulate(self) -> None:
        """Run simulation and update visuals."""
        try:
            changed = self.circuit.simulate()
            self.update_all_visuals()
            self.simulation_updated.emit()
            if changed:
                logger.debug("Simulation completed with changes")
        except Exception as e:
            logger.error(f"Simulation error: {e}")
    
    def update_all_visuals(self) -> None:
        """Update all gate and wire visuals safely."""
        # First, collect invalid wires
        invalid_wires = []
        valid_wires = []
        
        for wire in self.wire_items:
            if wire.is_valid():
                valid_wires.append(wire)
            else:
                invalid_wires.append(wire)
        
        # Remove invalid wires
        for wire in invalid_wires:
            logger.warning(f"Removing invalid wire: {wire}")
            self._remove_wire_internal(wire)
        
        # Update valid wires
        for wire in valid_wires:
            try:
                wire.update_path()
                wire.update_color()
            except RuntimeError:
                wire.invalidate()
        
        # Update gates
        gates_to_remove = []
        for name, gate_item in list(self.gate_items.items()):
            if not gate_item.is_gate_valid():
                gates_to_remove.append(name)
                continue
            try:
                gate_item.update_visuals()
            except RuntimeError:
                gates_to_remove.append(name)
        
        # Remove invalid gates
        for name in gates_to_remove:
            logger.warning(f"Removing invalid gate: {name}")
            if name in self.gate_items:
                del self.gate_items[name]
    
    def tick_clocks(self) -> None:
        """Tick all clocks and update."""
        try:
            changed = self.circuit.tick_clocks()
            self.update_all_visuals()
            self.simulation_updated.emit()
            if changed:
                logger.debug("Clock tick completed with changes")
        except Exception as e:
            logger.error(f"Clock tick error: {e}")
    
    def snap_to_grid(self, pos: QPointF) -> QPointF:
        """Snap position to grid."""
        x = round(pos.x() / self.grid_size) * self.grid_size
        y = round(pos.y() / self.grid_size) * self.grid_size
        return QPointF(x, y)
    
    def get_pin_at_pos(self, pos: QPointF) -> Tuple[Optional[GateGraphicsItem], 
                                                     Optional[str], 
                                                     Optional[PinType]]:
        """Find a pin at the given position."""
        try:
            # FIXED: Removed unsupported 'transform' keyword argument for PySide6
            items = self.items(pos, Qt.IntersectsItemShape, Qt.DescendingOrder)
            for item in items:
                if isinstance(item, PinGraphicsItem):
                    gate = item.gate_item
                    if gate and gate.is_gate_valid():
                        return gate, item.pin.name, item.pin.pin_type
        except RuntimeError:
            pass
        return None, None, None
    
    def _start_wire_drawing(self, gate: GateGraphicsItem, 
                           pin_name: str, pin_type: PinType,
                           mouse_pos: QPointF) -> None:
        """Start drawing a wire from a pin."""
        if not gate.is_gate_valid():
            return
            
        self._drawing_wire = True
        self._wire_start_gate = gate
        self._wire_start_pin = pin_name
        self._wire_start_type = pin_type
        self._mouse_pos = mouse_pos
        
        self._temp_wire = QGraphicsPathItem()
        self._temp_wire.setPen(QPen(COLOR_WIRE_LOW, 2, Qt.DashLine))
        self._temp_wire.setZValue(10)
        self.addItem(self._temp_wire)
        
        logger.debug(f"Started wire from {gate.component.name}.{pin_name}")
    
    def _update_temp_wire(self, mouse_pos: QPointF) -> None:
        """Update the temporary wire being drawn."""
        if not self._temp_wire or not self._wire_start_gate:
            return
        
        self._mouse_pos = mouse_pos
        
        if not self._wire_start_gate.is_gate_valid():
            self._cancel_wire_drawing()
            return
        
        try:
            if self._wire_start_type == PinType.OUTPUT:
                start = self._wire_start_gate.get_output_pin_scene_pos(self._wire_start_pin)
            else:
                start = self._wire_start_gate.get_input_pin_scene_pos(self._wire_start_pin)
        except (KeyError, RuntimeError):
            self._cancel_wire_drawing()
            return
        
        path = QPainterPath()
        path.moveTo(start)
        
        dx = abs(self._mouse_pos.x() - start.x())
        mid_x = (start.x() + self._mouse_pos.x()) / 2
        path.cubicTo(
            QPointF(mid_x, start.y()),
            QPointF(mid_x, self._mouse_pos.y()),
            self._mouse_pos
        )
        
        try:
            self._temp_wire.setPath(path)
        except RuntimeError:
            self._cancel_wire_drawing()
    
    def _finish_wire_drawing(self, mouse_pos: QPointF) -> None:
        """Finish drawing a wire."""
        self._drawing_wire = False
        
        if self._temp_wire:
            try:
                self.removeItem(self._temp_wire)
            except RuntimeError:
                pass
            self._temp_wire = None
        
        if not self._wire_start_gate or not self._wire_start_gate.is_gate_valid():
            self._reset_wire_state()
            return
        
        gate, pin_name, pin_type = self.get_pin_at_pos(mouse_pos)
        
        if gate and pin_name and gate != self._wire_start_gate and gate.is_gate_valid():
            if self._wire_start_type == PinType.OUTPUT and pin_type == PinType.INPUT:
                src_gate = self._wire_start_gate
                src_pin = self._wire_start_pin
                dst_gate = gate
                dst_pin = pin_name
            elif self._wire_start_type == PinType.INPUT and pin_type == PinType.OUTPUT:
                src_gate = gate
                src_pin = pin_name
                dst_gate = self._wire_start_gate
                dst_pin = self._wire_start_pin
            else:
                logger.warning("Invalid pin connection types")
                self._reset_wire_state()
                return
            
            self.add_wire(src_gate.component.name, src_pin,
                         dst_gate.component.name, dst_pin)
        elif gate == self._wire_start_gate:
            logger.warning("Cannot connect component to itself")
        
        self._reset_wire_state()
    
    def _cancel_wire_drawing(self) -> None:
        """Cancel wire drawing."""
        if self._temp_wire:
            try:
                self.removeItem(self._temp_wire)
            except RuntimeError:
                pass
            self._temp_wire = None
        self._drawing_wire = False
        self._reset_wire_state()
        logger.debug("Wire drawing cancelled")
    
    def _reset_wire_state(self) -> None:
        """Reset wire drawing state."""
        self._wire_start_gate = None
        self._wire_start_pin = None
        self._wire_start_type = None
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse press events."""
        if event.button() == Qt.LeftButton:
            gate, pin_name, pin_type = self.get_pin_at_pos(event.scenePos())
            
            if gate and pin_name:
                self._start_wire_drawing(gate, pin_name, pin_type, 
                                        event.scenePos())
                return
        
        if event.button() == Qt.RightButton:
            return
            
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move events."""
        if self._drawing_wire:
            self._update_temp_wire(event.scenePos())
            return
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release events."""
        if event.button() == Qt.LeftButton and self._drawing_wire:
            self._finish_wire_drawing(event.scenePos())
            return
        
        super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event) -> None:
        """Handle key press events."""
        if event.key() == Qt.Key_Delete:
            self._delete_selected()
        elif event.key() == Qt.Key_Escape:
            if self._drawing_wire:
                self._cancel_wire_drawing()
        super().keyPressEvent(event)
    
    def _delete_selected(self) -> None:
        """Delete all selected items."""
        try:
            selected = self.selectedItems()
            
            if not selected:
                return
            
            wires_to_remove = [item for item in selected 
                              if isinstance(item, WireGraphicsItem)]
            for wire in wires_to_remove:
                self.remove_wire(wire)
            
            gates_to_remove = [item for item in selected 
                              if isinstance(item, GateGraphicsItem)]
            for gate in gates_to_remove:
                if gate.is_gate_valid() and gate.component:
                    self.remove_gate(gate.component.name)
            
            logger.info(f"Deleted {len(wires_to_remove)} wires and {len(gates_to_remove)} gates")
        except RuntimeError as e:
            logger.error(f"Error during delete: {e}")
    
    def selectionChanged(self) -> None:
        """Emit signal when selection changes."""
        try:
            selected = self.selectedItems()
            gate = None
            for item in selected:
                if isinstance(item, GateGraphicsItem) and item.is_gate_valid():
                    gate = item
                    break
            self.selection_changed_signal.emit(gate)
        except RuntimeError:
            self.selection_changed_signal.emit(None)
    
    def clear_circuit(self) -> None:
        """Clear the entire circuit."""
        logger.info("Clearing circuit")
        
        # Invalidate all wires first
        for wire in list(self.wire_items):
            wire.invalidate()
        
        # Remove wires
        for wire in list(self.wire_items):
            self._remove_wire_internal(wire)
        
        # Invalidate and remove gates
        for name in list(self.gate_items.keys()):
            gate_item = self.gate_items[name]
            gate_item.invalidate()
            try:
                self.removeItem(gate_item)
            except RuntimeError:
                pass
            del self.gate_items[name]
        
        self.circuit.clear()
        self.circuit_changed.emit()
    
    def contextMenuEvent(self, event) -> None:
        """Show context menu."""
        try:
            menu = QMenu()
            
            gate, pin_name, pin_type = self.get_pin_at_pos(event.scenePos())
            
            if gate and gate.is_gate_valid() and gate.component:
                action = menu.addAction(f"Delete {gate.component.name}")
                action.triggered.connect(lambda: self.remove_gate(gate.component.name))
                menu.addSeparator()
            
            if self.selectedItems():
                delete_sel = menu.addAction(f"Delete Selected ({len(self.selectedItems())} items)")
                delete_sel.triggered.connect(self._delete_selected)
            
            menu.addSeparator()
            
            clear_action = menu.addAction("Clear All")
            clear_action.triggered.connect(self.clear_circuit)
            
            menu.exec(event.screenPos())
        except RuntimeError:
            pass


class CircuitView(QGraphicsView):
    """View for the circuit scene with zoom and pan."""
    
    def __init__(self, scene: CircuitScene):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        self._zoom: float = 1.0
        self._panning: bool = False
        
        logger.debug("CircuitView initialized")
    
    def wheelEvent(self, event) -> None:
        """Zoom with mouse wheel."""
        factor = ZOOM_FACTOR
        if event.angleDelta().y() > 0:
            new_zoom = self._zoom * factor
            if new_zoom <= MAX_ZOOM:
                self.scale(factor, factor)
                self._zoom = new_zoom
        else:
            new_zoom = self._zoom / factor
            if new_zoom >= MIN_ZOOM:
                self.scale(1/factor, 1/factor)
                self._zoom = new_zoom
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press for middle-button pan."""
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.setCursor(Qt.ClosedHandCursor)
            fake_event = QMouseEvent(
                QMouseEvent.Type.MouseButtonPress,
                event.position(),
                Qt.LeftButton,
                Qt.LeftButton,
                Qt.NoModifier
            )
            super().mousePressEvent(fake_event)
        else:
            super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release for middle-button pan."""
        if event.button() == Qt.MiddleButton and self._panning:
            self._panning = False
            self.setDragMode(QGraphicsView.RubberBandDrag)
            self.setCursor(Qt.ArrowCursor)
            fake_event = QMouseEvent(
                QMouseEvent.Type.MouseButtonRelease,
                event.position(),
                Qt.LeftButton,
                Qt.LeftButton,
                Qt.NoModifier
            )
            super().mouseReleaseEvent(fake_event)
        else:
            super().mouseReleaseEvent(event)
    
    def fit_to_scene(self) -> None:
        """Fit the view to show all items."""
        rect = self.scene().itemsBoundingRect()
        if rect.isEmpty():
            return
        rect.adjust(-50, -50, 50, 50)
        self.fitInView(rect, Qt.KeepAspectRatio)
        self._zoom = 1.0
        logger.debug("Fit to scene")
    
    def zoom_in(self) -> None:
        """Zoom in."""
        if self._zoom * ZOOM_FACTOR <= MAX_ZOOM:
            self.scale(ZOOM_FACTOR, ZOOM_FACTOR)
            self._zoom *= ZOOM_FACTOR
    
    def zoom_out(self) -> None:
        """Zoom out."""
        if self._zoom / ZOOM_FACTOR >= MIN_ZOOM:
            self.scale(1/ZOOM_FACTOR, 1/ZOOM_FACTOR)
            self._zoom /= ZOOM_FACTOR
    
    def reset_zoom(self) -> None:
        """Reset zoom to 100%."""
        self.resetTransform()
        self._zoom = 1.0
        logger.debug("Zoom reset")