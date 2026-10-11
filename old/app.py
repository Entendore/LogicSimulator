#!/usr/bin/env python3
"""
Improved Digital Logic Simulator with PySide6
Features:
- Visual drag-and-drop circuit design
- Real-time signal propagation
- Multiple gate types (AND, OR, NOT, XOR, NAND, NOR)
- Interactive switches and LED indicators
- Clock signal generator
- Wire routing with state visualization
- Undo/Redo functionality
- Save/Load circuits
"""

import sys
import json
import math
from typing import Dict, List, Tuple, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
import abc

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsScene, QGraphicsView,
    QGraphicsItem, QGraphicsPathItem, QGraphicsEllipseItem,
    QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem,
    QDockWidget, QTreeWidget, QTreeWidgetItem, QToolBar,
    QAction, QMenu, QMessageBox, QFileDialog, QDialog,
    QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QCheckBox,
    QPushButton, QGroupBox, QComboBox, QStatusBar, QSplitter
)
from PySide6.QtCore import (
    Qt, QPointF, QRectF, QLineF, QTimer, Signal, QObject,
    QSize, QPoint
)
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath,
    QFont, QPolygonF, QTransform, QKeySequence, QActionGroup
)


# ============================================================
# Backend: Logic Simulation Engine
# ============================================================

LOW = 0
HIGH = 1
UNDEFINED = -1

class PinType(Enum):
    INPUT = auto()
    OUTPUT = auto()

class Pin:
    def __init__(self, name: str, pin_type: PinType, index: int = 0):
        self.name = name
        self.pin_type = pin_type
        self.index = index
        self.value: int = LOW
        self.connected_to: List['Pin'] = []
    
    def __repr__(self):
        return f"Pin({self.name}, {self.pin_type.name}, {self.value})"


class ComponentType(Enum):
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    XOR = "XOR"
    NAND = "NAND"
    NOR = "NOR"
    SWITCH = "SWITCH"
    LED = "LED"
    CLOCK = "CLOCK"
    BUFFER = "BUFFER"


class LogicComponent(abc.ABC):
    """Abstract base class for all logic components."""
    
    def __init__(self, comp_type: ComponentType, name: str):
        self.comp_type = comp_type
        self.name = name
        self.inputs: Dict[str, Pin] = {}
        self.outputs: Dict[str, Pin] = {}
        self._setup_pins()
    
    @abc.abstractmethod
    def _setup_pins(self):
        pass
    
    @abc.abstractmethod
    def evaluate(self) -> bool:
        """Evaluate and return True if output changed."""
        pass
    
    def get_all_pins(self) -> List[Pin]:
        return list(self.inputs.values()) + list(self.outputs.values())
    
    def reset(self):
        for pin in self.inputs.values():
            pin.value = LOW
        for pin in self.outputs.values():
            pin.value = LOW


class AndGate(LogicComponent):
    def __init__(self, name: str):
        super().__init__(ComponentType.AND, name)
    
    def _setup_pins(self):
        self.inputs = {'A': Pin('A', PinType.INPUT, 0), 'B': Pin('B', PinType.INPUT, 1)}
        self.outputs = {'Y': Pin('Y', PinType.OUTPUT, 0)}
    
    def evaluate(self) -> bool:
        new_val = HIGH if (self.inputs['A'].value == HIGH and 
                          self.inputs['B'].value == HIGH) else LOW
        if self.outputs['Y'].value != new_val:
            self.outputs['Y'].value = new_val
            return True
        return False


class OrGate(LogicComponent):
    def __init__(self, name: str):
        super().__init__(ComponentType.OR, name)
    
    def _setup_pins(self):
        self.inputs = {'A': Pin('A', PinType.INPUT, 0), 'B': Pin('B', PinType.INPUT, 1)}
        self.outputs = {'Y': Pin('Y', PinType.OUTPUT, 0)}
    
    def evaluate(self) -> bool:
        new_val = HIGH if (self.inputs['A'].value == HIGH or 
                          self.inputs['B'].value == HIGH) else LOW
        if self.outputs['Y'].value != new_val:
            self.outputs['Y'].value = new_val
            return True
        return False


class NotGate(LogicComponent):
    def __init__(self, name: str):
        super().__init__(ComponentType.NOT, name)
    
    def _setup_pins(self):
        self.inputs = {'A': Pin('A', PinType.INPUT, 0)}
        self.outputs = {'Y': Pin('Y', PinType.OUTPUT, 0)}
    
    def evaluate(self) -> bool:
        new_val = HIGH if self.inputs['A'].value == LOW else LOW
        if self.outputs['Y'].value != new_val:
            self.outputs['Y'].value = new_val
            return True
        return False


class XorGate(LogicComponent):
    def __init__(self, name: str):
        super().__init__(ComponentType.XOR, name)
    
    def _setup_pins(self):
        self.inputs = {'A': Pin('A', PinType.INPUT, 0), 'B': Pin('B', PinType.INPUT, 1)}
        self.outputs = {'Y': Pin('Y', PinType.OUTPUT, 0)}
    
    def evaluate(self) -> bool:
        new_val = HIGH if self.inputs['A'].value != self.inputs['B'].value else LOW
        if self.outputs['Y'].value != new_val:
            self.outputs['Y'].value = new_val
            return True
        return False


class NandGate(LogicComponent):
    def __init__(self, name: str):
        super().__init__(ComponentType.NAND, name)
    
    def _setup_pins(self):
        self.inputs = {'A': Pin('A', PinType.INPUT, 0), 'B': Pin('B', PinType.INPUT, 1)}
        self.outputs = {'Y': Pin('Y', PinType.OUTPUT, 0)}
    
    def evaluate(self) -> bool:
        new_val = LOW if (self.inputs['A'].value == HIGH and 
                         self.inputs['B'].value == HIGH) else HIGH
        if self.outputs['Y'].value != new_val:
            self.outputs['Y'].value = new_val
            return True
        return False


class NorGate(LogicComponent):
    def __init__(self, name: str):
        super().__init__(ComponentType.NOR, name)
    
    def _setup_pins(self):
        self.inputs = {'A': Pin('A', PinType.INPUT, 0), 'B': Pin('B', PinType.INPUT, 1)}
        self.outputs = {'Y': Pin('Y', PinType.OUTPUT, 0)}
    
    def evaluate(self) -> bool:
        new_val = LOW if (self.inputs['A'].value == HIGH or 
                         self.inputs['B'].value == HIGH) else HIGH
        if self.outputs['Y'].value != new_val:
            self.outputs['Y'].value = new_val
            return True
        return False


class BufferGate(LogicComponent):
    def __init__(self, name: str):
        super().__init__(ComponentType.BUFFER, name)
    
    def _setup_pins(self):
        self.inputs = {'A': Pin('A', PinType.INPUT, 0)}
        self.outputs = {'Y': Pin('Y', PinType.OUTPUT, 0)}
    
    def evaluate(self) -> bool:
        if self.outputs['Y'].value != self.inputs['A'].value:
            self.outputs['Y'].value = self.inputs['A'].value
            return True
        return False


class Switch(LogicComponent):
    def __init__(self, name: str):
        super().__init__(ComponentType.SWITCH, name)
        self.state: bool = False
    
    def _setup_pins(self):
        self.inputs = {}
        self.outputs = {'Q': Pin('Q', PinType.OUTPUT, 0)}
    
    def toggle(self):
        self.state = not self.state
        self.evaluate()
    
    def set_state(self, state: bool):
        self.state = state
        self.evaluate()
    
    def evaluate(self) -> bool:
        new_val = HIGH if self.state else LOW
        if self.outputs['Q'].value != new_val:
            self.outputs['Q'].value = new_val
            return True
        return False


class LED(LogicComponent):
    def __init__(self, name: str):
        super().__init__(ComponentType.LED, name)
        self.is_on: bool = False
    
    def _setup_pins(self):
        self.inputs = {'A': Pin('A', PinType.INPUT, 0)}
        self.outputs = {}
    
    def evaluate(self) -> bool:
        new_state = self.inputs['A'].value == HIGH
        if self.is_on != new_state:
            self.is_on = new_state
            return True
        return False


class Clock(LogicComponent):
    def __init__(self, name: str, frequency: float = 1.0):
        super().__init__(ComponentType.CLOCK, name)
        self.frequency = frequency
        self._tick_count = 0
        self.running = True
    
    def _setup_pins(self):
        self.inputs = {}
        self.outputs = {'Q': Pin('Q', PinType.OUTPUT, 0)}
    
    def tick(self):
        if not self.running:
            return False
        self._tick_count += 1
        # Toggle every half period
        period = max(1, int(10 / self.frequency))
        if self._tick_count % period == 0:
            new_val = HIGH if (self._tick_count // period) % 2 == 0 else LOW
            if self.outputs['Q'].value != new_val:
                self.outputs['Q'].value = new_val
                return True
        return False
    
    def evaluate(self) -> bool:
        return False  # Clock is driven externally


# Component factory
COMPONENT_CLASSES = {
    ComponentType.AND: AndGate,
    ComponentType.OR: OrGate,
    ComponentType.NOT: NotGate,
    ComponentType.XOR: XorGate,
    ComponentType.NAND: NandGate,
    ComponentType.NOR: NorGate,
    ComponentType.BUFFER: BufferGate,
    ComponentType.SWITCH: Switch,
    ComponentType.LED: LED,
    ComponentType.CLOCK: Clock,
}


class Circuit:
    """Main circuit container and simulation engine."""
    
    def __init__(self):
        self.components: Dict[str, LogicComponent] = {}
        self.connections: List[Tuple[str, str, str, str]] = []  # (src_comp, src_pin, dst_comp, dst_pin)
        self._event_queue: Set[str] = set()
        self._component_counter = 0
    
    def add_component(self, comp: LogicComponent) -> str:
        """Add a component and return its name."""
        if comp.name in self.components:
            raise ValueError(f"Component '{comp.name}' already exists.")
        self.components[comp.name] = comp
        return comp.name
    
    def remove_component(self, name: str):
        """Remove a component and all its connections."""
        if name not in self.components:
            return
        # Remove all connections involving this component
        self.connections = [
            c for c in self.connections 
            if c[0] != name and c[2] != name
        ]
        # Clear pin connections
        comp = self.components[name]
        for pin in comp.get_all_pins():
            pin.connected_to.clear()
        del self.components[name]
    
    def connect(self, src_comp: str, src_pin: str, dst_comp: str, dst_pin: str):
        """Connect output pin to input pin."""
        if src_comp not in self.components:
            raise ValueError(f"Source component '{src_comp}' not found.")
        if dst_comp not in self.components:
            raise ValueError(f"Destination component '{dst_comp}' not found.")
        
        src = self.components[src_comp]
        dst = self.components[dst_comp]
        
        if src_pin not in src.outputs:
            raise ValueError(f"Output pin '{src_pin}' not found on '{src_comp}'.")
        if dst_pin not in dst.inputs:
            raise ValueError(f"Input pin '{dst_pin}' not found on '{dst_comp}'.")
        
        # Check for duplicate connection
        conn = (src_comp, src_pin, dst_comp, dst_pin)
        if conn in self.connections:
            return
        
        # Remove existing connection to this input (only one driver allowed)
        self.connections = [
            c for c in self.connections if not (c[2] == dst_comp and c[3] == dst_pin)
        ]
        
        self.connections.append(conn)
        
        # Update pin references
        src.outputs[src_pin].connected_to.append(dst.inputs[dst_pin])
        dst.inputs[dst_pin].connected_to.append(src.outputs[src_pin])
    
    def disconnect(self, src_comp: str, src_pin: str, dst_comp: str, dst_pin: str):
        """Remove a connection."""
        conn = (src_comp, src_pin, dst_comp, dst_pin)
        if conn in self.connections:
            self.connections.remove(conn)
            # Update pin references
            src = self.components[src_comp]
            dst = self.components[dst_comp]
            src.outputs[src_pin].connected_to = [
                p for p in src.outputs[src_pin].connected_to 
                if not (p.name == dst_pin and p in dst.inputs.values())
            ]
            dst.inputs[dst_pin].connected_to = [
                p for p in dst.inputs[dst_pin].connected_to 
                if not (p.name == src_pin and p in src.outputs.values())
            ]
    
    def generate_name(self, comp_type: ComponentType) -> str:
        """Generate a unique component name."""
        self._component_counter += 1
        return f"{comp_type.value}_{self._component_counter}"
    
    def simulate(self):
        """Run simulation until stable."""
        # Add all components to initial queue
        for name in self.components:
            self._event_queue.add(name)
        
        max_iterations = len(self.components) * 5 + 20
        iterations = 0
        
        while self._event_queue and iterations < max_iterations:
            current_queue = list(self._event_queue)
            self._event_queue.clear()
            
            for comp_name in current_queue:
                if comp_name not in self.components:
                    continue
                comp = self.components[comp_name]
                
                if comp.evaluate():
                    # Propagate changes
                    for out_pin_name, out_pin in comp.outputs.items():
                        for conn in self.connections:
                            if conn[0] == comp_name and conn[1] == out_pin_name:
                                dst_comp_name, dst_pin_name = conn[2], conn[3]
                                dst_comp = self.components[dst_comp_name]
                                new_val = out_pin.value
                                if dst_comp.inputs[dst_pin_name].value != new_val:
                                    dst_comp.inputs[dst_pin_name].value = new_val
                                    self._event_queue.add(dst_comp_name)
            
            iterations += 1
        
        return iterations > 0
    
    def tick_clocks(self):
        """Tick all clock components and propagate."""
        for comp in self.components.values():
            if isinstance(comp, Clock) and comp.tick():
                self._event_queue.add(comp.name)
        if self._event_queue:
            self.simulate()
    
    def reset(self):
        """Reset all components to initial state."""
        for comp in self.components.values():
            comp.reset()
            if isinstance(comp, Switch):
                comp.state = False
            if isinstance(comp, Clock):
                comp._tick_count = 0
        self._event_queue.clear()
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state of all components."""
        state = {}
        for name, comp in self.components.items():
            comp_state = {
                'type': comp.comp_type.value,
                'inputs': {k: v.value for k, v in comp.inputs.items()},
                'outputs': {k: v.value for k, v in comp.outputs.items()},
            }
            if isinstance(comp, Switch):
                comp_state['switch_state'] = comp.state
            if isinstance(comp, LED):
                comp_state['is_on'] = comp.is_on
            state[name] = comp_state
        return state
    
    def to_dict(self) -> Dict:
        """Serialize circuit to dictionary."""
        return {
            'components': [
                {
                    'name': name,
                    'type': comp.comp_type.value,
                    'x': 0, 'y': 0  # Will be updated by GUI
                }
                for name, comp in self.components.items()
            ],
            'connections': self.connections
        }
    
    def clear(self):
        """Remove all components and connections."""
        self.components.clear()
        self.connections.clear()
        self._event_queue.clear()


# ============================================================
# GUI: Graphics Items
# ============================================================

COLOR_LOW = QColor(60, 120, 216)
COLOR_HIGH = QColor(255, 100, 100)
COLOR_UNDEFINED = QColor(128, 128, 128)
COLOR_WIRE_LOW = QColor(60, 120, 216)
COLOR_WIRE_HIGH = QColor(255, 80, 80)
COLOR_GATE_FILL = QColor(240, 240, 245)
COLOR_GATE_BORDER = QColor(40, 40, 60)
COLOR_PIN = QColor(80, 80, 100)
COLOR_SWITCH_OFF = QColor(200, 200, 200)
COLOR_SWITCH_ON = QColor(100, 255, 100)
COLOR_LED_OFF = QColor(80, 80, 80)
COLOR_LED_ON = QColor(255, 50, 50)
COLOR_SELECTED = QColor(100, 180, 255)


class PinGraphicsItem(QGraphicsEllipseItem):
    """Graphical representation of a pin."""
    
    def __init__(self, pin: Pin, parent: 'GateGraphicsItem'):
        super().__init__(-6, -6, 12, 12, parent)
        self.pin = pin
        self.gate_item = parent
        self.setBrush(QBrush(COLOR_PIN))
        self.setPen(QPen(Qt.black, 1))
        self.setAcceptHoverEvents(True)
        self.setZValue(2)
    
    def update_color(self):
        if self.pin.value == HIGH:
            self.setBrush(QBrush(COLOR_HIGH))
        elif self.pin.value == LOW:
            self.setBrush(QBrush(COLOR_LOW))
        else:
            self.setBrush(QBrush(COLOR_UNDEFINED))
    
    def hoverEnterEvent(self, event):
        self.setScale(1.3)
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        self.setScale(1.0)
        super().hoverLeaveEvent(event)
    
    def get_scene_pos(self) -> QPointF:
        return self.scenePos()
    
    def itemChange(self, change, value):
        return super().itemChange(change, value)


class GateGraphicsItem(QGraphicsItem):
    """Base class for gate graphics items."""
    
    WIDTH = 100
    HEIGHT = 60
    PIN_RADIUS = 6
    
    def __init__(self, component: LogicComponent, x: float = 0, y: float = 0):
        super().__init__()
        self.component = component
        self.pin_items: Dict[str, PinGraphicsItem] = {}
        self.label_item: Optional[QGraphicsTextItem] = None
        
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)
        
        self._create_pins()
        self._create_label()
    
    def _create_pins(self):
        input_pins = list(self.component.inputs.values())
        output_pins = list(self.component.outputs.values())
        
        # Position input pins on the left
        if input_pins:
            spacing = self.HEIGHT / (len(input_pins) + 1)
            for i, pin in enumerate(input_pins):
                pin_item = PinGraphicsItem(pin, self)
                pin_item.setPos(-self.WIDTH/2, -self.HEIGHT/2 + spacing * (i + 1))
                self.pin_items[f"in_{pin.name}"] = pin_item
        
        # Position output pins on the right
        if output_pins:
            spacing = self.HEIGHT / (len(output_pins) + 1)
            for i, pin in enumerate(output_pins):
                pin_item = PinGraphicsItem(pin, self)
                pin_item.setPos(self.WIDTH/2, -self.HEIGHT/2 + spacing * (i + 1))
                self.pin_items[f"out_{pin.name}"] = pin_item
    
    def _create_label(self):
        self.label_item = QGraphicsTextItem(self.component.name, self)
        self.label_item.setFont(QFont("Consolas", 8))
        self.label_item.setDefaultTextColor(QColor(60, 60, 60))
        rect = self.label_item.boundingRect()
        self.label_item.setPos(-rect.width()/2, self.HEIGHT/2 + 2)
    
    def get_input_pin_scene_pos(self, pin_name: str) -> QPointF:
        return self.pin_items[f"in_{pin_name}"].scenePos()
    
    def get_output_pin_scene_pos(self, pin_name: str) -> QPointF:
        return self.pin_items[f"out_{pin_name}"].scenePos()
    
    def update_visuals(self):
        for pin_item in self.pin_items.values():
            pin_item.update_color()
        self.update()
    
    def boundingRect(self) -> QRectF:
        return QRectF(-self.WIDTH/2 - 10, -self.HEIGHT/2 - 10, 
                      self.WIDTH + 20, self.HEIGHT + 30)
    
    def paint(self, painter: QPainter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Selection highlight
        if self.isSelected():
            painter.setPen(QPen(COLOR_SELECTED, 3))
        else:
            painter.setPen(QPen(COLOR_GATE_BORDER, 2))
        
        painter.setBrush(QBrush(COLOR_GATE_FILL))
        
        # Draw gate shape
        path = self._get_gate_path()
        painter.drawPath(path)
        
        # Draw gate symbol
        self._draw_symbol(painter)
    
    def _get_gate_path(self) -> QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(-self.WIDTH/2, -self.HEIGHT/2, self.WIDTH, self.HEIGHT, 5, 5)
        return path
    
    def _draw_symbol(self, painter: QPainter):
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.setPen(QPen(COLOR_GATE_BORDER))
        text = self.component.comp_type.value
        rect = QRectF(-self.WIDTH/2, -self.HEIGHT/2, self.WIDTH, self.HEIGHT)
        painter.drawText(rect, Qt.AlignCenter, text)
    
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            # Notify scene to update wires
            scene = self.scene()
            if scene:
                scene.update()
        return super().itemChange(change, value)
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click for interactive components."""
        if isinstance(self.component, Switch):
            self.component.toggle()
            self.update_visuals()
            scene = self.scene()
            if scene and hasattr(scene, 'simulate'):
                scene.simulate()
        super().mouseDoubleClickEvent(event)


class AndGateGraphicsItem(GateGraphicsItem):
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
    def _get_gate_path(self) -> QPainterPath:
        path = QPainterPath()
        w, h = self.WIDTH/2, self.HEIGHT/2
        path.moveTo(-w, -h)
        path.quadTo(-w/3, -h, w-5, 0)
        path.quadTo(-w/3, h, -w, h)
        path.quadTo(-w/2, 0, -w, -h)
        return path


class NotGateGraphicsItem(GateGraphicsItem):
    WIDTH = 80
    
    def _get_gate_path(self) -> QPainterPath:
        path = QPainterPath()
        w, h = self.WIDTH/2, self.HEIGHT/2
        path.moveTo(-w, -h)
        path.lineTo(w-10, 0)
        path.lineTo(-w, h)
        path.closeSubpath()
        return path
    
    def _draw_symbol(self, painter: QPainter):
        # Draw inversion circle
        w, h = self.WIDTH/2, self.HEIGHT/2
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(QPen(COLOR_GATE_BORDER, 2))
        painter.drawEllipse(w-12, -5, 10, 10)


class XorGateGraphicsItem(OrGateGraphicsItem):
    def _get_gate_path(self) -> QPainterPath:
        path = super()._get_gate_path()
        w, h = self.WIDTH/2, self.HEIGHT/2
        # Add extra curve for XOR
        extra = QPainterPath()
        extra.moveTo(-w-5, -h)
        extra.quadTo(-w/3-5, 0, -w-5, h)
        path.addPath(extra)
        return path


class NandGateGraphicsItem(AndGateGraphicsItem):
    def _draw_symbol(self, painter: QPainter):
        w, h = self.WIDTH/2, self.HEIGHT/2
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(QPen(COLOR_GATE_BORDER, 2))
        painter.drawEllipse(w-8, -5, 10, 10)


class NorGateGraphicsItem(OrGateGraphicsItem):
    def _draw_symbol(self, painter: QPainter):
        w, h = self.WIDTH/2, self.HEIGHT/2
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(QPen(COLOR_GATE_BORDER, 2))
        painter.drawEllipse(w-3, -5, 10, 10)


class SwitchGraphicsItem(GateGraphicsItem):
    WIDTH = 80
    HEIGHT = 50
    
    def _get_gate_path(self) -> QPainterPath:
        path = QPainterPath()
        w, h = self.WIDTH/2, self.HEIGHT/2
        path.addRoundedRect(-w, -h, self.WIDTH, self.HEIGHT, 10, 10)
        return path
    
    def _draw_symbol(self, painter: QPainter):
        w, h = self.WIDTH/2, self.HEIGHT/2
        is_on = self.component.state if isinstance(self.component, Switch) else False
        
        # Draw switch body
        if is_on:
            painter.setBrush(QBrush(COLOR_SWITCH_ON))
        else:
            painter.setBrush(QBrush(COLOR_SWITCH_OFF))
        painter.setPen(QPen(COLOR_GATE_BORDER, 2))
        painter.drawRoundedRect(-w+5, -h+5, self.WIDTH-10, self.HEIGHT-10, 5, 5)
        
        # Draw switch indicator
        painter.setPen(QPen(Qt.black, 3))
        if is_on:
            painter.drawLine(-15, 10, 15, -10)
        else:
            painter.drawLine(-15, -10, 15, 10)
    
    def update_visuals(self):
        super().update_visuals()
        self.update()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if isinstance(self.component, Switch):
                self.component.toggle()
                self.update_visuals()
                scene = self.scene()
                if scene and hasattr(scene, 'simulate'):
                    scene.simulate()
        super().mousePressEvent(event)


class LEDGraphicsItem(GateGraphicsItem):
    WIDTH = 60
    HEIGHT = 60
    
    def _get_gate_path(self) -> QPainterPath:
        path = QPainterPath()
        w, h = self.WIDTH/2, self.HEIGHT/2
        path.addRoundedRect(-w, -h, self.WIDTH, self.HEIGHT, 10, 10)
        return path
    
    def _draw_symbol(self, painter: QPainter):
        w, h = self.WIDTH/2, self.HEIGHT/2
        is_on = self.component.is_on if isinstance(self.component, LED) else False
        
        # Draw LED body
        if is_on:
            color = COLOR_LED_ON
            # Glow effect
            painter.setBrush(QBrush(QColor(255, 100, 100, 50)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(-w+5, -h+5, self.WIDTH-10, self.HEIGHT-10)
        else:
            color = COLOR_LED_OFF
        
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(COLOR_GATE_BORDER, 2))
        painter.drawEllipse(-w+10, -h+10, self.WIDTH-20, self.HEIGHT-20)
        
        # Draw LED symbol lines
        painter.setPen(QPen(color.lighter(150) if is_on else Qt.gray, 2))
        cx, cy = 0, 0
        painter.drawLine(cx-8, cy+8, cx+8, cy+8)
        painter.drawLine(cx-5, cy+12, cx-8, cy+8)
        painter.drawLine(cx-2, cy+12, cx-5, cy+8)
        
        # Arrow for light emission
        if is_on:
            painter.setPen(QPen(COLOR_LED_ON, 2))
            painter.drawLine(5, -15, 12, -22)
            painter.drawLine(12, -22, 8, -18)
            painter.drawLine(12, -22, 12, -18)
    
    def update_visuals(self):
        super().update_visuals()
        self.update()


class ClockGraphicsItem(GateGraphicsItem):
    WIDTH = 80
    HEIGHT = 50
    
    def _get_gate_path(self) -> QPainterPath:
        path = QPainterPath()
        w, h = self.WIDTH/2, self.HEIGHT/2
        path.addRoundedRect(-w, -h, self.WIDTH, self.HEIGHT, 10, 10)
        return path
    
    def _draw_symbol(self, painter: QPainter):
        w, h = self.WIDTH/2, self.HEIGHT/2
        is_high = False
        if isinstance(self.component, Clock):
            is_high = self.component.outputs['Q'].value == HIGH
        
        # Draw clock body
        painter.setBrush(QBrush(QColor(255, 255, 200)))
        painter.setPen(QPen(COLOR_GATE_BORDER, 2))
        painter.drawRoundedRect(-w+5, -h+5, self.WIDTH-10, self.HEIGHT-10, 5, 5)
        
        # Draw clock waveform
        painter.setPen(QPen(COLOR_GATE_BORDER if not is_high else COLOR_HIGH, 2))
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
    
    def update_visuals(self):
        super().update_visuals()
        self.update()


# Graphics item factory
GATE_GRAPHICS_MAP = {
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


class WireGraphicsItem(QGraphicsPathItem):
    """Graphical representation of a wire connection."""
    
    def __init__(self, src_gate: GateGraphicsItem, src_pin: str,
                 dst_gate: GateGraphicsItem, dst_pin: str,
                 connection_info: Tuple[str, str, str, str]):
        super().__init__()
        self.src_gate = src_gate
        self.src_pin = src_pin
        self.dst_gate = dst_gate
        self.dst_pin = dst_pin
        self.connection_info = connection_info
        
        self.setPen(QPen(COLOR_WIRE_LOW, 3))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setZValue(0)
        self.setAcceptHoverEvents(True)
        
        self.update_path()
    
    def update_path(self):
        """Update the wire path based on pin positions."""
        start = self.src_gate.get_output_pin_scene_pos(self.src_pin)
        end = self.dst_gate.get_input_pin_scene_pos(self.dst_pin)
        
        path = QPainterPath()
        path.moveTo(start)
        
        # Calculate control points for smooth curve
        dx = abs(end.x() - start.x())
        control_offset = max(50, dx * 0.5)
        
        if dx < 20:
            # Very close - use simple arc
            path.cubicTo(
                start.x() + control_offset, start.y(),
                end.x() - control_offset, end.y(),
                end
            )
        else:
            # Standard S-curve
            mid_x = (start.x() + end.x()) / 2
            path.cubicTo(
                mid_x, start.y(),
                mid_x, end.y(),
                end
            )
        
        self.setPath(path)
    
    def update_color(self):
        """Update wire color based on signal state."""
        if self.src_gate.component.outputs[self.src_pin].value == HIGH:
            self.setPen(QPen(COLOR_WIRE_HIGH, 3))
        else:
            self.setPen(QPen(COLOR_WIRE_LOW, 3))
        self.update()
    
    def hoverEnterEvent(self, event):
        pen = self.pen()
        pen.setWidth(5)
        self.setPen(pen)
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        pen = self.pen()
        pen.setWidth(3)
        self.setPen(pen)
        super().hoverLeaveEvent(event)
    
    def paint(self, painter: QPainter, option, widget):
        if self.isSelected():
            pen = self.pen()
            pen.setColor(COLOR_SELECTED)
            self.setPen(pen)
        super().paint(painter, option, widget)


# ============================================================
# GUI: Circuit Scene and View
# ============================================================

class CircuitScene(QGraphicsScene):
    """Main scene for the circuit editor."""
    
    circuit_changed = Signal()
    simulation_updated = Signal()
    
    def __init__(self, circuit: Circuit):
        super().__init__()
        self.circuit = circuit
        self.gate_items: Dict[str, GateGraphicsItem] = {}
        self.wire_items: List[WireGraphicsItem] = []
        
        # Wire drawing state
        self.drawing_wire = False
        self.wire_start_gate: Optional[GateGraphicsItem] = None
        self.wire_start_pin: Optional[str] = None
        self.wire_start_type: Optional[PinType] = None
        self.temp_wire: Optional[QGraphicsPathItem] = None
        self.mouse_pos = QPointF()
        
        # Grid settings
        self.grid_size = 20
        self.show_grid = True
        
        # Background color
        self.setBackgroundBrush(QBrush(QColor(245, 245, 250)))
        
        self.setSceneRect(-2000, -2000, 4000, 4000)
    
    def drawBackground(self, painter: QPainter, rect: QRectF):
        super().drawBackground(painter, rect)
        
        if not self.show_grid:
            return
        
        painter.setPen(QPen(QColor(220, 220, 230), 0.5))
        
        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)
        
        lines = []
        x = left
        while x <= rect.right():
            lines.append(QLineF(x, rect.top(), x, rect.bottom()))
            x += self.grid_size
        
        y = top
        while y <= rect.bottom():
            lines.append(QLineF(rect.left(), y, rect.right(), y))
            y += self.grid_size
        
        painter.drawLines(lines)
    
    def add_gate(self, comp_type: ComponentType, pos: QPointF) -> GateGraphicsItem:
        """Add a new gate to the scene."""
        name = self.circuit.generate_name(comp_type)
        
        if comp_type == ComponentType.CLOCK:
            comp = Clock(name)
        else:
            comp = COMPONENT_CLASSES[comp_type](name)
        
        self.circuit.add_component(comp)
        
        graphics_class = GATE_GRAPHICS_MAP[comp_type]
        gate_item = graphics_class(comp, pos.x(), pos.y())
        self.addItem(gate_item)
        self.gate_items[name] = gate_item
        
        self.circuit_changed.emit()
        return gate_item
    
    def remove_gate(self, name: str):
        """Remove a gate from the scene."""
        if name not in self.gate_items:
            return
        
        gate_item = self.gate_items[name]
        
        # Remove all wires connected to this gate
        wires_to_remove = [
            w for w in self.wire_items 
            if w.src_gate == gate_item or w.dst_gate == gate_item
        ]
        for wire in wires_to_remove:
            self.remove_wire(wire)
        
        self.removeItem(gate_item)
        del self.gate_items[name]
        self.circuit.remove_component(name)
        
        self.circuit_changed.emit()
    
    def add_wire(self, src_gate_name: str, src_pin: str,
                 dst_gate_name: str, dst_pin: str) -> Optional[WireGraphicsItem]:
        """Add a wire connection."""
        if src_gate_name not in self.gate_items or dst_gate_name not in self.gate_items:
            return None
        
        src_gate = self.gate_items[src_gate_name]
        dst_gate = self.gate_items[dst_gate_name]
        
        try:
            self.circuit.connect(src_gate_name, src_pin, dst_gate_name, dst_pin)
        except ValueError as e:
            print(f"Connection error: {e}")
            return None
        
        conn_info = (src_gate_name, src_pin, dst_gate_name, dst_pin)
        wire = WireGraphicsItem(src_gate, src_pin, dst_gate, dst_pin, conn_info)
        self.addItem(wire)
        self.wire_items.append(wire)
        
        self.circuit_changed.emit()
        self.simulate()
        return wire
    
    def remove_wire(self, wire: WireGraphicsItem):
        """Remove a wire connection."""
        src_name, src_pin, dst_name, dst_pin = wire.connection_info
        self.circuit.disconnect(src_name, src_pin, dst_name, dst_pin)
        
        if wire in self.wire_items:
            self.wire_items.remove(wire)
        self.removeItem(wire)
        
        self.circuit_changed.emit()
        self.simulate()
    
    def simulate(self):
        """Run simulation and update visuals."""
        self.circuit.simulate()
        self.update_all_visuals()
        self.simulation_updated.emit()
    
    def update_all_visuals(self):
        """Update all gate and wire visuals."""
        for gate_item in self.gate_items.values():
            gate_item.update_visuals()
        for wire in self.wire_items:
            wire.update_path()
            wire.update_color()
    
    def tick_clocks(self):
        """Tick all clocks and update."""
        self.circuit.tick_clocks()
        self.update_all_visuals()
        self.simulation_updated.emit()
    
    def snap_to_grid(self, pos: QPointF) -> QPointF:
        """Snap position to grid."""
        x = round(pos.x() / self.grid_size) * self.grid_size
        y = round(pos.y() / self.grid_size) * self.grid_size
        return QPointF(x, y)
    
    def get_pin_at_pos(self, pos: QPointF) -> Tuple[Optional[GateGraphicsItem], Optional[str], Optional[PinType]]:
        """Find a pin at the given position."""
        items = self.items(pos, Qt.IntersectsItemShape, Qt.DescendingOrder,
                          transform=QTransform())
        for item in items:
            if isinstance(item, PinGraphicsItem):
                gate = item.gate_item
                if item.pin.pin_type == PinType.OUTPUT:
                    return gate, item.pin.name, PinType.OUTPUT
                else:
                    return gate, item.pin.name, PinType.INPUT
        return None, None, None
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            gate, pin_name, pin_type = self.get_pin_at_pos(event.scenePos())
            
            if gate and pin_name:
                # Start drawing wire from output pin
                if pin_type == PinType.OUTPUT:
                    self.drawing_wire = True
                    self.wire_start_gate = gate
                    self.wire_start_pin = pin_name
                    self.wire_start_type = pin_type
                    self.mouse_pos = event.scenePos()
                    
                    self.temp_wire = QGraphicsPathItem()
                    self.temp_wire.setPen(QPen(COLOR_WIRE_LOW, 2, Qt.DashLine))
                    self.addItem(self.temp_wire)
                    return
                # Or allow starting from input pin (will reverse direction)
                elif pin_type == PinType.INPUT:
                    self.drawing_wire = True
                    self.wire_start_gate = gate
                    self.wire_start_pin = pin_name
                    self.wire_start_type = pin_type
                    self.mouse_pos = event.scenePos()
                    
                    self.temp_wire = QGraphicsPathItem()
                    self.temp_wire.setPen(QPen(COLOR_WIRE_LOW, 2, Qt.DashLine))
                    self.addItem(self.temp_wire)
                    return
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        self.mouse_pos = event.scenePos()
        
        if self.drawing_wire and self.temp_wire:
            path = QPainterPath()
            start = self.wire_start_gate.get_output_pin_scene_pos(self.wire_start_pin) \
                if self.wire_start_type == PinType.OUTPUT else \
                self.wire_start_gate.get_input_pin_scene_pos(self.wire_start_pin)
            path.moveTo(start)
            
            dx = abs(self.mouse_pos.x() - start.x())
            control_offset = max(50, dx * 0.5)
            mid_x = (start.x() + self.mouse_pos.x()) / 2
            path.cubicTo(mid_x, start.y(), mid_x, self.mouse_pos.y(), self.mouse_pos)
            
            self.temp_wire.setPath(path)
            return
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing_wire:
            self.drawing_wire = False
            
            if self.temp_wire:
                self.removeItem(self.temp_wire)
                self.temp_wire = None
            
            gate, pin_name, pin_type = self.get_pin_at_pos(event.scenePos())
            
            if gate and pin_name and gate != self.wire_start_gate:
                # Determine source and destination
                if self.wire_start_type == PinType.OUTPUT and pin_type == PinType.INPUT:
                    src_gate = self.wire_start_gate
                    src_pin = self.wire_start_pin
                    dst_gate = gate
                    dst_pin = pin_name
                elif self.wire_start_type == PinType.INPUT and pin_type == PinType.OUTPUT:
                    src_gate = gate
                    src_pin = pin_name
                    dst_gate = self.wire_start_gate
                    dst_pin = self.wire_start_pin
                else:
                    # Invalid connection (same type pins)
                    self.wire_start_gate = None
                    self.wire_start_pin = None
                    return
                
                self.add_wire(src_gate.component.name, src_pin,
                            dst_gate.component.name, dst_pin)
            
            self.wire_start_gate = None
            self.wire_start_pin = None
            self.wire_start_type = None
            return
        
        super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            # Delete selected items
            selected = self.selectedItems()
            for item in selected:
                if isinstance(item, GateGraphicsItem):
                    self.remove_gate(item.component.name)
                elif isinstance(item, WireGraphicsItem):
                    self.remove_wire(item)
        super().keyPressEvent(event)


class CircuitView(QGraphicsView):
    """View for the circuit scene with zoom and pan."""
    
    def __init__(self, scene: CircuitScene):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        self._zoom = 1.0
        self._min_zoom = 0.2
        self._max_zoom = 5.0
    
    def wheelEvent(self, event):
        """Zoom with mouse wheel."""
        factor = 1.15
        if event.angleDelta().y() > 0:
            if self._zoom * factor <= self._max_zoom:
                self.scale(factor, factor)
                self._zoom *= factor
        else:
            if self._zoom / factor >= self._min_zoom:
                self.scale(1/factor, 1/factor)
                self._zoom /= factor
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.RubberBandDrag)
        super().mouseReleaseEvent(event)


# ============================================================
# GUI: Component Palette
# ============================================================

class ComponentPalette(QDockWidget):
    """Dockable widget with available components."""
    
    component_selected = Signal(ComponentType)
    
    def __init__(self):
        super().__init__("Components")
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        widget = QTreeWidget()
        widget.setHeaderLabel("Gate Types")
        widget.setAnimated(True)
        widget.setIndentation(10)
        
        # Basic gates
        basic = QTreeWidgetItem(widget, ["Basic Gates"])
        for gate_type in [ComponentType.AND, ComponentType.OR, ComponentType.NOT,
                          ComponentType.XOR, ComponentType.NAND, ComponentType.NOR,
                          ComponentType.BUFFER]:
            item = QTreeWidgetItem(basic, [gate_type.value])
            item.setData(0, Qt.UserRole, gate_type)
            basic.addChild(item)
        
        # I/O components
        io = QTreeWidgetItem(widget, ["Input/Output"])
        for comp_type in [ComponentType.SWITCH, ComponentType.LED, ComponentType.CLOCK]:
            item = QTreeWidgetItem(io, [comp_type.value])
            item.setData(0, Qt.UserRole, comp_type)
            io.addChild(item)
        
        widget.expandAll()
        
        widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        widget.itemClicked.connect(self._on_item_clicked)
        
        self.tree = widget
        self.setWidget(widget)
        
        self._selected_type: Optional[ComponentType] = None
    
    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.UserRole)
        if data and isinstance(data, ComponentType):
            self._selected_type = data
            self.component_selected.emit(data)
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.UserRole)
        if data and isinstance(data, ComponentType):
            self.component_selected.emit(data)
    
    def get_selected_type(self) -> Optional[ComponentType]:
        return self._selected_type


# ============================================================
# GUI: Properties Panel
# ============================================================

class PropertiesPanel(QDockWidget):
    """Dockable widget showing component properties."""
    
    def __init__(self):
        super().__init__("Properties")
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        self.widget = QGroupBox("Selected Component")
        layout = QVBoxLayout()
        
        self.name_label = QLabel("Name: -")
        self.type_label = QLabel("Type: -")
        self.inputs_group = QGroupBox("Inputs")
        self.inputs_layout = QVBoxLayout()
        self.inputs_group.setLayout(self.inputs_layout)
        self.outputs_group = QGroupBox("Outputs")
        self.outputs_layout = QVBoxLayout()
        self.outputs_group.setLayout(self.outputs_layout)
        self.extra_widget = None
        
        layout.addWidget(self.name_label)
        layout.addWidget(self.type_label)
        layout.addWidget(self.inputs_group)
        layout.addWidget(self.outputs_group)
        
        self.extra_layout = QVBoxLayout()
        layout.addLayout(self.extra_layout)
        
        layout.addStretch()
        self.widget.setLayout(layout)
        self.setWidget(self.widget)
        
        self._current_gate: Optional[GateGraphicsItem] = None
    
    def update_properties(self, gate: Optional[GateGraphicsItem]):
        """Update the properties panel for the given gate."""
        # Clear previous extra widgets
        if self.extra_widget:
            self.extra_layout.removeWidget(self.extra_widget)
            self.extra_widget.deleteLater()
            self.extra_widget = None
        
        self._current_gate = gate
        
        # Clear input/output labels
        while self.inputs_layout.count():
            item = self.inputs_layout.takeAt(0)
            item.widget().deleteLater()
        while self.outputs_layout.count():
            item = self.outputs_layout.takeAt(0)
            item.widget().deleteLater()
        
        if gate is None:
            self.name_label.setText("Name: -")
            self.type_label.setText("Type: -")
            return
        
        comp = gate.component
        self.name_label.setText(f"Name: {comp.name}")
        self.type_label.setText(f"Type: {comp.comp_type.value}")
        
        # Show inputs
        for name, pin in comp.inputs.items():
            color = "red" if pin.value == HIGH else "blue"
            label = QLabel(f"{name}: <span style='color:{color}'>{pin.value}</span>")
            self.inputs_layout.addWidget(label)
        
        # Show outputs
        for name, pin in comp.outputs.items():
            color = "red" if pin.value == HIGH else "blue"
            label = QLabel(f"{name}: <span style='color:{color}'>{pin.value}</span>")
            self.outputs_layout.addWidget(label)
        
        # Extra controls for specific components
        if isinstance(comp, Clock):
            self.extra_widget = ClockControls(comp)
            self.extra_layout.addWidget(self.extra_widget)
        elif isinstance(comp, Switch):
            btn = QPushButton("Toggle Switch")
            btn.clicked.connect(lambda: self._toggle_switch(comp, gate))
            self.extra_widget = btn
            self.extra_layout.addWidget(btn)
    
    def _toggle_switch(self, switch: Switch, gate: GateGraphicsItem):
        switch.toggle()
        gate.update_visuals()
        scene = gate.scene()
        if scene and hasattr(scene, 'simulate'):
            scene.simulate()
        self.update_properties(gate)


class ClockControls(QGroupBox):
    """Controls for clock components."""
    
    def __init__(self, clock: Clock):
        super().__init__("Clock Settings")
        self.clock = clock
        
        layout = QVBoxLayout()
        
        # Frequency control
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Frequency:"))
        self.freq_spin = QDoubleSpinBox()
        self.freq_spin.setRange(0.1, 10.0)
        self.freq_spin.setValue(clock.frequency)
        self.freq_spin.setSingleStep(0.1)
        self.freq_spin.valueChanged.connect(self._on_freq_changed)
        freq_layout.addWidget(self.freq_spin)
        layout.addLayout(freq_layout)
        
        # Running control
        self.running_check = QCheckBox("Running")
        self.running_check.setChecked(clock.running)
        self.running_check.toggled.connect(self._on_running_changed)
        layout.addWidget(self.running_check)
        
        self.setLayout(layout)
    
    def _on_freq_changed(self, value: float):
        self.clock.frequency = value
    
    def _on_running_changed(self, checked: bool):
        self.clock.running = checked


# ============================================================
# GUI: State Viewer
# ============================================================

class StateViewer(QDockWidget):
    """Dockable widget showing circuit state."""
    
    def __init__(self):
        super().__init__("Circuit State")
        self.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.RightDockWidgetArea)
        
        self.text = QTreeWidget()
        self.text.setHeaderLabels(["Component", "Inputs", "Outputs"])
        self.text.setColumnWidth(0, 120)
        self.text.setColumnWidth(1, 150)
        self.text.setColumnWidth(2, 150)
        
        self.setWidget(self.text)
    
    def update_state(self, state: Dict[str, Any]):
        """Update the state display."""
        self.text.clear()
        
        for name, comp_state in state.items():
            item = QTreeWidgetItem([
                f"{name} ({comp_state['type']})",
                str(comp_state['inputs']),
                str(comp_state['outputs'])
            ])
            self.text.addTopLevelItem(item)


# ============================================================
# GUI: Main Window
# ============================================================

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Digital Logic Simulator")
        self.setMinimumSize(1200, 800)
        
        # Create circuit and scene
        self.circuit = Circuit()
        self.scene = CircuitScene(self.circuit)
        self.view = CircuitView(self.scene)
        
        self.setCentralWidget(self.view)
        
        # Create docks
        self.palette = ComponentPalette()
        self.addDockWidget(Qt.LeftDockWidgetArea, self.palette)
        
        self.properties = PropertiesPanel()
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties)
        
        self.state_viewer = StateViewer()
        self.addDockWidget(Qt.BottomDockWidgetArea, self.state_viewer)
        
        # Create toolbars
        self._create_toolbars()
        
        # Create menus
        self._create_menus()
        
        # Status bar
        self.statusBar().showMessage("Ready. Select a component from the palette and click on the canvas to place it.")
        
        # Connect signals
        self.palette.component_selected.connect(self._on_component_selected)
        self.scene.circuit_changed.connect(self._on_circuit_changed)
        self.scene.simulation_updated.connect(self._on_simulation_updated)
        self.scene.selectionChanged.connect(self._on_selection_changed)
        
        # Clock timer
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self._on_clock_tick)
        self.clock_running = False
        self.clock_speed = 200  # ms
        
        # Place mode
        self._place_mode = False
        self._place_type: Optional[ComponentType] = None
        
        # Undo/Redo stacks
        self.undo_stack: List[Dict] = []
        self.redo_stack: List[Dict] = []
        
        self._apply_style()
    
    def _apply_style(self):
        """Apply modern stylesheet."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5fa;
            }
            QDockWidget {
                font-size: 12px;
                color: #333;
            }
            QDockWidget::title {
                background: #e0e0e8;
                padding: 6px;
                border: 1px solid #c0c0c8;
            }
            QTreeWidget {
                background-color: #fafafa;
                border: 1px solid #ddd;
                font-size: 11px;
            }
            QTreeWidget::item:selected {
                background-color: #4a90d9;
                color: white;
            }
            QToolBar {
                background: #e8e8f0;
                border: none;
                spacing: 5px;
                padding: 3px;
            }
            QToolButton {
                background: #f0f0f5;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 11px;
            }
            QToolButton:hover {
                background: #ddd;
            }
            QToolButton:pressed {
                background: #ccc;
            }
            QToolButton:checked {
                background: #4a90d9;
                color: white;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                font-size: 11px;
            }
            QPushButton {
                background: #4a90d9;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #3a80c9;
            }
            QSpinBox, QDoubleSpinBox {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 3px;
            }
            QStatusBar {
                background: #e0e0e8;
                color: #333;
            }
        """)
    
    def _create_toolbars(self):
        """Create toolbars."""
        # File toolbar
        file_toolbar = self.addToolBar("File")
        file_toolbar.setMovable(False)
        
        new_action = QAction("New", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self._new_circuit)
        file_toolbar.addAction(new_action)
        
        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._save_circuit)
        file_toolbar.addAction(save_action)
        
        load_action = QAction("Load", self)
        load_action.setShortcut(QKeySequence.Open)
        load_action.triggered.connect(self._load_circuit)
        file_toolbar.addAction(load_action)
        
        file_toolbar.addSeparator()
        
        # Edit toolbar
        edit_toolbar = self.addToolBar("Edit")
        edit_toolbar.setMovable(False)
        
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self._undo)
        edit_toolbar.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(self._redo)
        edit_toolbar.addAction(redo_action)
        
        edit_toolbar.addSeparator()
        
        delete_action = QAction("Delete", self)
        delete_action.setShortcut(QKeySequence.Delete)
        delete_action.triggered.connect(self._delete_selected)
        edit_toolbar.addAction(delete_action)
        
        # Simulation toolbar
        sim_toolbar = self.addToolBar("Simulation")
        sim_toolbar.setMovable(False)
        
        self.simulate_action = QAction("Simulate", self)
        self.simulate_action.triggered.connect(self._run_simulation)
        sim_toolbar.addAction(self.simulate_action)
        
        self.clock_action = QAction("Start Clock", self)
        self.clock_action.setCheckable(True)
        self.clock_action.toggled.connect(self._toggle_clock)
        sim_toolbar.addAction(self.clock_action)
        
        speed_label = QLabel("  Speed: ")
        sim_toolbar.addWidget(speed_label)
        
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["Slow (500ms)", "Normal (200ms)", "Fast (100ms)", "Very Fast (50ms)"])
        self.speed_combo.setCurrentIndex(1)
        self.speed_combo.currentIndexChanged.connect(self._on_speed_changed)
        sim_toolbar.addWidget(self.speed_combo)
        
        sim_toolbar.addSeparator()
        
        reset_action = QAction("Reset", self)
        reset_action.triggered.connect(self._reset_circuit)
        sim_toolbar.addAction(reset_action)
        
        # View toolbar
        view_toolbar = self.addToolBar("View")
        view_toolbar.setMovable(False)
        
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        zoom_in_action.triggered.connect(lambda: self.view.scale(1.2, 1.2))
        view_toolbar.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        zoom_out_action.triggered.connect(lambda: self.view.scale(1/1.2, 1/1.2))
        view_toolbar.addAction(zoom_out_action)
        
        fit_action = QAction("Fit View", self)
        fit_action.triggered.connect(self._fit_view)
        view_toolbar.addAction(fit_action)
        
        grid_action = QAction("Grid", self)
        grid_action.setCheckable(True)
        grid_action.setChecked(True)
        grid_action.toggled.connect(lambda v: setattr(self.scene, 'show_grid', v))
        view_toolbar.addAction(grid_action)
    
    def _create_menus(self):
        """Create menus."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        file_menu.addAction("New", self._new_circuit, QKeySequence.New)
        file_menu.addAction("Save", self._save_circuit, QKeySequence.Save)
        file_menu.addAction("Load", self._load_circuit, QKeySequence.Open)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close, QKeySequence.Quit)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        edit_menu.addAction("Undo", self._undo, QKeySequence.Undo)
        edit_menu.addAction("Redo", self._redo, QKeySequence.Redo)
        edit_menu.addSeparator()
        edit_menu.addAction("Delete", self._delete_selected, QKeySequence.Delete)
        edit_menu.addSeparator()
        edit_menu.addAction("Select All", self._select_all, QKeySequence.SelectAll)
        
        # Simulation menu
        sim_menu = menubar.addMenu("Simulation")
        sim_menu.addAction("Run Simulation", self._run_simulation)
        sim_menu.addAction("Start Clock", self._toggle_clock)
        sim_menu.addAction("Reset Circuit", self._reset_circuit)
        
        # View menu
        view_menu = menubar.addMenu("View")
        view_menu.addAction("Zoom In", lambda: self.view.scale(1.2, 1.2), QKeySequence.ZoomIn)
        view_menu.addAction("Zoom Out", lambda: self.view.scale(1/1.2, 1/1.2), QKeySequence.ZoomOut)
        view_menu.addAction("Fit View", self._fit_view)
        view_menu.addAction("Toggle Grid", lambda: setattr(self.scene, 'show_grid', not self.scene.show_grid))
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About", self._show_about)
        help_menu.addAction("Usage", self._show_usage)
    
    def _on_component_selected(self, comp_type: ComponentType):
        """Handle component selection from palette."""
        self._place_mode = True
        self._place_type = comp_type
        self.statusBar().showMessage(f"Click on canvas to place {comp_type.value}. Right-click to cancel.")
        self.view.setCursor(Qt.CrossCursor)
    
    def mousePressEvent(self, event):
        """Handle clicks for placing components."""
        if event.button() == Qt.LeftButton and self._place_mode and self._place_type:
            # Get scene position from view
            pos = self.view.mapToScene(self.view.viewport().mapFromGlobal(event.globalPos()))
            pos = self.scene.snap_to_grid(pos)
            
            self.scene.add_gate(self._place_type, pos)
            self.statusBar().showMessage(f"Placed {self._place_type.value}")
        
        elif event.button() == Qt.RightButton and self._place_mode:
            self._cancel_place_mode()
        
        super().mousePressEvent(event)
    
    def _cancel_place_mode(self):
        """Cancel place mode."""
        self._place_mode = False
        self._place_type = None
        self.view.setCursor(Qt.ArrowCursor)
        self.statusBar().showMessage("Place mode cancelled.")
    
    def _on_circuit_changed(self):
        """Handle circuit changes."""
        self.statusBar().showMessage(f"Circuit: {len(self.circuit.components)} components, {len(self.circuit.connections)} connections")
    
    def _on_simulation_updated(self):
        """Handle simulation updates."""
        state = self.circuit.get_state()
        self.state_viewer.update_state(state)
        
        # Update properties if a gate is selected
        selected = self.scene.selectedItems()
        if selected and isinstance(selected[0], GateGraphicsItem):
            self.properties.update_properties(selected[0])
    
    def _on_selection_changed(self):
        """Handle selection changes."""
        selected = self.scene.selectedItems()
        if len(selected) == 1 and isinstance(selected[0], GateGraphicsItem):
            self.properties.update_properties(selected[0])
        else:
            self.properties.update_properties(None)
    
    def _new_circuit(self):
        """Create a new circuit."""
        reply = QMessageBox.question(self, "New Circuit",
                                     "Are you sure you want to create a new circuit?\nUnsaved changes will be lost.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.circuit.clear()
            self.scene.clear()
            self.scene.gate_items.clear()
            self.scene.wire_items.clear()
            self.scene.update()
            self.statusBar().showMessage("New circuit created.")
    
    def _save_circuit(self):
        """Save circuit to file."""
        filename, _ = QFileDialog.getSaveFileName(self, "Save Circuit", "", "JSON Files (*.json)")
        if filename:
            # Gather positions
            data = {
                'components': [],
                'connections': self.circuit.connections
            }
            for name, gate_item in self.scene.gate_items.items():
                comp = gate_item.component
                item_data = {
                    'name': name,
                    'type': comp.comp_type.value,
                    'x': gate_item.pos().x(),
                    'y': gate_item.pos().y(),
                }
                if isinstance(comp, Switch):
                    item_data['state'] = comp.state
                if isinstance(comp, Clock):
                    item_data['frequency'] = comp.frequency
                    item_data['running'] = comp.running
                data['components'].append(item_data)
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.statusBar().showMessage(f"Circuit saved to {filename}")
    
    def _load_circuit(self):
        """Load circuit from file."""
        filename, _ = QFileDialog.getOpenFileName(self, "Load Circuit", "", "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                
                # Clear current circuit
                self.circuit.clear()
                self.scene.clear()
                self.scene.gate_items.clear()
                self.scene.wire_items.clear()
                
                # Load components
                for comp_data in data['components']:
                    comp_type = ComponentType(comp_data['type'])
                    gate_item = self.scene.add_gate(comp_type, QPointF(comp_data['x'], comp_data['y']))
                    
                    if comp_type == ComponentType.SWITCH and 'state' in comp_data:
                        gate_item.component.set_state(comp_data['state'])
                    if comp_type == ComponentType.CLOCK:
                        if 'frequency' in comp_data:
                            gate_item.component.frequency = comp_data['frequency']
                        if 'running' in comp_data:
                            gate_item.component.running = comp_data['running']
                
                # Load connections
                for conn in data['connections']:
                    self.scene.add_wire(*conn)
                
                self.scene.simulate()
                self.statusBar().showMessage(f"Circuit loaded from {filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load circuit:\n{str(e)}")
    
    def _run_simulation(self):
        """Run a simulation step."""
        self.scene.simulate()
        self.statusBar().showMessage("Simulation complete.")
    
    def _toggle_clock(self, checked: bool):
        """Toggle clock running state."""
        if checked:
            self.clock_timer.start(self.clock_speed)
            self.clock_action.setText("Stop Clock")
            self.statusBar().showMessage("Clock running...")
        else:
            self.clock_timer.stop()
            self.clock_action.setText("Start Clock")
            self.statusBar().showMessage("Clock stopped.")
    
    def _on_clock_tick(self):
        """Handle clock tick."""
        self.scene.tick_clocks()
    
    def _on_speed_changed(self, index: int):
        """Handle speed combo change."""
        speeds = [500, 200, 100, 50]
        self.clock_speed = speeds[index]
        if self.clock_timer.isActive():
            self.clock_timer.setInterval(self.clock_speed)
    
    def _reset_circuit(self):
        """Reset the circuit to initial state."""
        # Stop clock
        if self.clock_timer.isActive():
            self.clock_action.setChecked(False)
        
        self.circuit.reset()
        self.scene.update_all_visuals()
        self.statusBar().showMessage("Circuit reset.")
    
    def _delete_selected(self):
        """Delete selected items."""
        selected = self.scene.selectedItems()
        for item in selected:
            if isinstance(item, GateGraphicsItem):
                self.scene.remove_gate(item.component.name)
            elif isinstance(item, WireGraphicsItem):
                self.scene.remove_wire(item)
    
    def _select_all(self):
        """Select all items."""
        for item in self.scene.items():
            item.setSelected(True)
    
    def _fit_view(self):
        """Fit view to show all items."""
        rect = self.scene.itemsBoundingRect()
        rect.adjust(-50, -50, 50, 50)
        self.view.fitInView(rect, Qt.KeepAspectRatio)
    
    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(self, "About Digital Logic Simulator",
                         """<h2>Digital Logic Simulator</h2>
                         <p>Version 1.0</p>
                         <p>A visual digital logic circuit simulator built with PySide6.</p>
                         <p><b>Features:</b></p>
                         <ul>
                         <li>Drag and drop gate placement</li>
                         <li>Visual wire connections</li>
                         <li>Real-time simulation</li>
                         <li>Clock signal generation</li>
                         <li>Save/Load circuits</li>
                         </ul>
                         """)
    
    def _show_usage(self):
        """Show usage dialog."""
        QMessageBox.information(self, "Usage",
                               """<h2>How to Use</h2>
                               <p><b>Placing Components:</b></p>
                               <ol>
                               <li>Select a component from the left palette</li>
                               <li>Click on the canvas to place it</li>
                               <li>Right-click to cancel placement</li>
                               </ol>
                               <p><b>Connecting Components:</b></p>
                               <ol>
                               <li>Click and drag from an output pin (right side)</li>
                               <li>Release on an input pin (left side)</li>
                               </ol>
                               <p><b>Interacting:</b></p>
                               <ul>
                               <li>Click on a SWITCH to toggle it</li>
                               <li>Double-click a SWITCH to toggle it</li>
                               <li>Use mouse wheel to zoom</li>
                               <li>Middle-click and drag to pan</li>
                               <li>Press Delete to remove selected items</li>
                               </ul>
                               <p><b>Simulation:</b></p>
                               <ul>
                               <li>Click "Simulate" to run one step</li>
                               <li>Click "Start Clock" for automatic clock ticks</li>
                               <li>Click "Reset" to clear all signals</li>
                               </ul>
                               """)


# ============================================================
# Main Entry Point
# ============================================================

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Digital Logic Simulator")
    app.setOrganizationName("LogicSim")
    
    # Set application icon (optional)
    # app.setWindowIcon(QIcon("icon.png"))
    
    window = MainWindow()
    window.show()
    
    # Center window on screen
    screen = app.primaryScreen().geometry()
    x = (screen.width() - window.width()) // 2
    y = (screen.height() - window.height()) // 2
    window.move(x, y)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()