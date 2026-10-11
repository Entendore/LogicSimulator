"""
Graphical representations of logic gates and I/O components.
"""

from __future__ import annotations
from typing import Dict, Optional, TYPE_CHECKING
from PySide6.QtWidgets import QGraphicsItem, QGraphicsTextItem
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (QPainter, QPen, QBrush, QColor, 
                           QPainterPath, QFont)
from config import (ComponentType, PinType, HIGH, LOW,
                   GATE_WIDTH, GATE_HEIGHT, SMALL_GATE_WIDTH, 
                   SMALL_GATE_HEIGHT, PIN_RADIUS,
                   COLOR_GATE_FILL, COLOR_GATE_BORDER, COLOR_SELECTED,
                   COLOR_SWITCH_OFF, COLOR_SWITCH_ON, COLOR_LED_OFF, 
                   COLOR_LED_ON, logger)
from pins import Pin
from pin_graphics import PinGraphicsItem

if TYPE_CHECKING:
    from gates import LogicComponent, Switch, LED, Clock


class GateGraphicsItem(QGraphicsItem):
    """Base class for gate graphics items."""
    
    WIDTH = GATE_WIDTH
    HEIGHT = GATE_HEIGHT
    
    def __init__(self, component: 'LogicComponent', x: float = 0, y: float = 0):
        super().__init__()
        self.component: 'LogicComponent' = component
        self.pin_items: Dict[str, PinGraphicsItem] = {}
        self.label_item: Optional[QGraphicsTextItem] = None
        self._is_valid: bool = True
        
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)
        
        self._create_pins()
        self._create_label()
        
        logger.debug(f"Created graphics for: {component.name}")
    
    def invalidate(self) -> None:
        """Mark this gate as invalid."""
        self._is_valid = False
        self.component = None
    
    def is_gate_valid(self) -> bool:
        """Check if this gate is still valid."""
        if not self._is_valid:
            return False
        try:
            # Test if C++ object exists
            _ = self.scene()
            return self.component is not None
        except RuntimeError:
            return False
    
    def _create_pins(self) -> None:
        """Create pin graphics items."""
        if self.component is None:
            return
            
        input_pins = list(self.component.inputs.values())
        output_pins = list(self.component.outputs.values())
        
        # Position input pins on the left
        if input_pins:
            spacing = self.HEIGHT / (len(input_pins) + 1)
            for i, pin in enumerate(input_pins):
                pin_item = PinGraphicsItem(pin, self)
                y_pos = -self.HEIGHT/2 + spacing * (i + 1)
                pin_item.setPos(-self.WIDTH/2, y_pos)
                self.pin_items[f"in_{pin.name}"] = pin_item
        
        # Position output pins on the right
        if output_pins:
            spacing = self.HEIGHT / (len(output_pins) + 1)
            for i, pin in enumerate(output_pins):
                pin_item = PinGraphicsItem(pin, self)
                y_pos = -self.HEIGHT/2 + spacing * (i + 1)
                pin_item.setPos(self.WIDTH/2, y_pos)
                self.pin_items[f"out_{pin.name}"] = pin_item
    
    def _create_label(self) -> None:
        """Create the name label below the gate."""
        if self.component is None:
            return
            
        self.label_item = QGraphicsTextItem(self.component.name, self)
        self.label_item.setFont(QFont("Consolas", 8))
        self.label_item.setDefaultTextColor(QColor(60, 60, 60))
        rect = self.label_item.boundingRect()
        self.label_item.setPos(-rect.width()/2, self.HEIGHT/2 + 2)
    
    def get_input_pin_scene_pos(self, pin_name: str) -> QPointF:
        """Get the scene position of an input pin."""
        key = f"in_{pin_name}"
        if key not in self.pin_items:
            raise KeyError(f"Input pin '{pin_name}' not found")
        return self.pin_items[key].scenePos()
    
    def get_output_pin_scene_pos(self, pin_name: str) -> QPointF:
        """Get the scene position of an output pin."""
        key = f"out_{pin_name}"
        if key not in self.pin_items:
            raise KeyError(f"Output pin '{pin_name}' not found")
        return self.pin_items[key].scenePos()
    
    def update_visuals(self) -> bool:
        """Update all visual elements.
        
        Returns:
            True if update succeeded
        """
        if not self.is_gate_valid():
            return False
        try:
            for pin_item in self.pin_items.values():
                pin_item.update_color()
            self.update()
            return True
        except RuntimeError:
            return False
    
    def boundingRect(self) -> QRectF:
        """Get the bounding rectangle."""
        return QRectF(-self.WIDTH/2 - 10, -self.HEIGHT/2 - 10, 
                      self.WIDTH + 20, self.HEIGHT + 30)
    
    def paint(self, painter: QPainter, option, widget) -> None:
        """Paint the gate."""
        if not self.is_gate_valid():
            return
            
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.isSelected():
            painter.setPen(QPen(COLOR_SELECTED, 3))
        else:
            painter.setPen(QPen(COLOR_GATE_BORDER, 2))
        
        painter.setBrush(QBrush(COLOR_GATE_FILL))
        
        path = self._get_gate_path()
        painter.drawPath(path)
        
        self._draw_symbol(painter)
    
    def _get_gate_path(self) -> QPainterPath:
        """Get the gate outline path. Override for custom shapes."""
        path = QPainterPath()
        path.addRoundedRect(-self.WIDTH/2, -self.HEIGHT/2, 
                           self.WIDTH, self.HEIGHT, 5, 5)
        return path
    
    def _draw_symbol(self, painter: QPainter) -> None:
        """Draw the gate symbol. Override for custom symbols."""
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.setPen(QPen(COLOR_GATE_BORDER))
        text = self.component.comp_type.value if self.component else "?"
        rect = QRectF(-self.WIDTH/2, -self.HEIGHT/2, self.WIDTH, self.HEIGHT)
        painter.drawText(rect, Qt.AlignCenter, text)
    
    def itemChange(self, change, value):
        """Handle item changes."""
        if change == QGraphicsItem.ItemPositionHasChanged:
            try:
                scene = self.scene()
                if scene and hasattr(scene, 'update_all_visuals'):
                    scene.update_all_visuals()
            except RuntimeError:
                pass
        return super().itemChange(change, value)
    
    def mouseDoubleClickEvent(self, event) -> None:
        """Handle double-click for interactive components."""
        if not self.is_gate_valid():
            event.ignore()
            return
            
        from gates import Switch
        if isinstance(self.component, Switch):
            try:
                self.component.toggle()
                self.update_visuals()
                scene = self.scene()
                if scene and hasattr(scene, 'simulate'):
                    scene.simulate()
            except Exception as e:
                logger.error(f"Error toggling switch: {e}")
        super().mouseDoubleClickEvent(event)


class AndGateGraphicsItem(GateGraphicsItem):
    """AND gate with distinctive D-shape."""
    
    def _get_gate_path(self) -> QPainterPath:
        path = QPainterPath()
        w, h = self.WIDTH/2, self.HEIGHT/2
        path.moveTo(-w, -h)
        path.lineTo(0, -h)
        path.arcTo(0, -h, w, self.HEIGHT, -90, 180)
        path.lineTo(-w, h)
        path.closeSubpath()
        return path


class OrGateGraphicsItem(GateGraphicsItem):
    """OR gate with curved shape."""
    
    def _get_gate_path(self) -> QPainterPath:
        path = QPainterPath()
        w, h = self.WIDTH/2, self.HEIGHT/2
        path.moveTo(-w, -h)
        path.quadTo(-w/3, -h, w-5, 0)
        path.quadTo(-w/3, h, -w, h)
        path.quadTo(-w/2, 0, -w, -h)
        return path


class NotGateGraphicsItem(GateGraphicsItem):
    """NOT gate (inverter) with triangle and bubble."""
    
    WIDTH = SMALL_GATE_WIDTH
    
    def _get_gate_path(self) -> QPainterPath:
        path = QPainterPath()
        w, h = self.WIDTH/2, self.HEIGHT/2
        path.moveTo(-w, -h)
        path.lineTo(w-10, 0)
        path.lineTo(-w, h)
        path.closeSubpath()
        return path
    
    def _draw_symbol(self, painter: QPainter) -> None:
        """Draw inversion bubble."""
        w, h = self.WIDTH/2, self.HEIGHT/2
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(QPen(COLOR_GATE_BORDER, 2))
        painter.drawEllipse(QPointF(w-7, 0), 5, 5)


class XorGateGraphicsItem(OrGateGraphicsItem):
    """XOR gate with extra curve."""
    
    def _get_gate_path(self) -> QPainterPath:
        path = super()._get_gate_path()
        w, h = self.WIDTH/2, self.HEIGHT/2
        extra = QPainterPath()
        extra.moveTo(-w-5, -h)
        extra.quadTo(-w/3-5, 0, -w-5, h)
        path.addPath(extra)
        return path


class NandGateGraphicsItem(AndGateGraphicsItem):
    """NAND gate with bubble."""
    
    def _draw_symbol(self, painter: QPainter) -> None:
        """Draw inversion bubble."""
        w, h = self.WIDTH/2, self.HEIGHT/2
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(QPen(COLOR_GATE_BORDER, 2))
        painter.drawEllipse(QPointF(w-3, 0), 5, 5)


class NorGateGraphicsItem(OrGateGraphicsItem):
    """NOR gate with bubble."""
    
    def _draw_symbol(self, painter: QPainter) -> None:
        """Draw inversion bubble."""
        w, h = self.WIDTH/2, self.HEIGHT/2
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(QPen(COLOR_GATE_BORDER, 2))
        painter.drawEllipse(QPointF(w-2, 0), 5, 5)


class SwitchGraphicsItem(GateGraphicsItem):
    """Toggle switch component."""
    
    WIDTH = SMALL_GATE_WIDTH
    HEIGHT = SMALL_GATE_HEIGHT
    
    def _get_gate_path(self) -> QPainterPath:
        path = QPainterPath()
        w, h = self.WIDTH/2, self.HEIGHT/2
        path.addRoundedRect(-w, -h, self.WIDTH, self.HEIGHT, 10, 10)
        return path
    
    def _draw_symbol(self, painter: QPainter) -> None:
        """Draw switch toggle."""
        from gates import Switch
        w, h = self.WIDTH/2, self.HEIGHT/2
        is_on = self.component.state if isinstance(self.component, Switch) else False
        
        color = COLOR_SWITCH_ON if is_on else COLOR_SWITCH_OFF
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(COLOR_GATE_BORDER, 2))
        painter.drawRoundedRect(-w+5, -h+5, self.WIDTH-10, self.HEIGHT-10, 5, 5)
        
        painter.setPen(QPen(Qt.black, 3, Qt.SolidLine, Qt.RoundCap))
        if is_on:
            painter.drawLine(int(-15), int(10), int(15), int(-10))
        else:
            painter.drawLine(int(-15), int(-10), int(15), int(10))
        
        painter.setFont(QFont("Arial", 9))
        painter.drawText(QRectF(-w+5, -h+5, self.WIDTH-10, self.HEIGHT-10),
                        Qt.AlignCenter, "SW")
    
    def update_visuals(self) -> bool:
        """Update switch visuals."""
        result = super().update_visuals()
        if result:
            self.update()
        return result
    
    def mousePressEvent(self, event) -> None:
        """Toggle switch on click."""
        if not self.is_gate_valid():
            event.ignore()
            return
            
        from gates import Switch
        if event.button() == Qt.LeftButton and isinstance(self.component, Switch):
            try:
                self.component.toggle()
                self.update_visuals()
                scene = self.scene()
                if scene and hasattr(scene, 'simulate'):
                    scene.simulate()
            except Exception as e:
                logger.error(f"Error toggling switch: {e}")
        else:
            super().mousePressEvent(event)


class LEDGraphicsItem(GateGraphicsItem):
    """LED indicator component."""
    
    WIDTH = 60
    HEIGHT = 60
    
    def _get_gate_path(self) -> QPainterPath:
        path = QPainterPath()
        w, h = self.WIDTH/2, self.HEIGHT/2
        path.addRoundedRect(-w, -h, self.WIDTH, self.HEIGHT, 10, 10)
        return path
    
    def _draw_symbol(self, painter: QPainter) -> None:
        """Draw LED with glow effect."""
        from gates import LED
        w, h = self.WIDTH/2, self.HEIGHT/2
        is_on = self.component.is_on if isinstance(self.component, LED) else False
        
        if is_on:
            painter.setBrush(QBrush(QColor(255, 100, 100, 50)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(-w+2, -h+2, self.WIDTH-4, self.HEIGHT-4)
        
        color = COLOR_LED_ON if is_on else COLOR_LED_OFF
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(COLOR_GATE_BORDER, 2))
        painter.drawEllipse(-w+10, -h+10, self.WIDTH-20, self.HEIGHT-20)
        
        if is_on:
            painter.setPen(QPen(COLOR_LED_ON, 2))
            painter.drawLine(5, -15, 12, -22)
            painter.drawLine(12, -22, 8, -18)
            painter.drawLine(12, -22, 12, -18)
            painter.drawLine(12, -12, 19, -19)
            painter.drawLine(19, -19, 15, -15)
            painter.drawLine(19, -19, 19, -15)
    
    def update_visuals(self) -> bool:
        """Update LED visuals."""
        result = super().update_visuals()
        if result:
            self.update()
        return result


class ClockGraphicsItem(GateGraphicsItem):
    """Clock signal generator component."""
    
    WIDTH = SMALL_GATE_WIDTH
    HEIGHT = SMALL_GATE_HEIGHT
    
    def _get_gate_path(self) -> QPainterPath:
        path = QPainterPath()
        w, h = self.WIDTH/2, self.HEIGHT/2
        path.addRoundedRect(-w, -h, self.WIDTH, self.HEIGHT, 10, 10)
        return path
    
    def _draw_symbol(self, painter: QPainter) -> None:
        """Draw clock waveform symbol."""
        from gates import Clock
        w, h = self.WIDTH/2, self.HEIGHT/2
        is_high = False
        if isinstance(self.component, Clock):
            try:
                is_high = self.component.outputs['Q'].value == HIGH
            except (KeyError, AttributeError):
                pass
        
        painter.setBrush(QBrush(QColor(255, 255, 200)))
        painter.setPen(QPen(COLOR_GATE_BORDER, 2))
        painter.drawRoundedRect(-w+5, -h+5, self.WIDTH-10, self.HEIGHT-10, 5, 5)
        
        wave_color = COLOR_HIGH if is_high else COLOR_GATE_BORDER
        painter.setPen(QPen(wave_color, 2))
        path = QPainterPath()
        path.moveTo(-20, 5)
        path.lineTo(-10, 5)
        path.lineTo(-10, -8)
        path.lineTo(0, -8)
        path.lineTo(0, 5)
        path.lineTo(10, 5)
        path.lineTo(10, -8)
        path.lineTo(20, -8)
        painter.drawPath(path)
        
        if isinstance(self.component, Clock):
            painter.setFont(QFont("Arial", 7))
            painter.setPen(QPen(COLOR_GATE_BORDER))
            painter.drawText(QRectF(-w+5, h-15, self.WIDTH-10, 12),
                           Qt.AlignCenter, f"{self.component.frequency:.1f}Hz")
    
    def update_visuals(self) -> bool:
        """Update clock visuals."""
        result = super().update_visuals()
        if result:
            self.update()
        return result


# Graphics item factory mapping
GATE_GRAPHICS_MAP: Dict[ComponentType, type] = {
    ComponentType.AND: AndGateGraphicsItem,
    ComponentType.OR: OrGateGraphicsItem,
    ComponentType.NOT: NotGateGraphicsItem,
    ComponentType.XOR: XorGateGraphicsItem,
    ComponentType.NAND: NandGateGraphicsItem,
    ComponentType.NOR: NorGateGraphicsItem,
    ComponentType.BUFFER: GateGraphicsItem,
    ComponentType.SWITCH: SwitchGraphicsItem,
    ComponentType.LED: LEDGraphicsItem,
    ComponentType.CLOCK: ClockGraphicsItem,
}