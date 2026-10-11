"""
Graphical representation of pins.
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from PySide6.QtWidgets import QGraphicsEllipseItem
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QBrush, QPen, QColor
from config import (PinType, COLOR_LOW, COLOR_HIGH, COLOR_UNDEFINED, 
                   COLOR_PIN, PIN_RADIUS, logger)

if TYPE_CHECKING:
    from gate_graphics import GateGraphicsItem
    from pins import Pin


class PinGraphicsItem(QGraphicsEllipseItem):
    """Graphical representation of a pin.
    
    Displays the pin as a circle that changes color based on signal state.
    Enlarges on hover for easier wire connection.
    """
    
    def __init__(self, pin: 'Pin', parent: 'GateGraphicsItem'):
        super().__init__(-PIN_RADIUS, -PIN_RADIUS, 
                         PIN_RADIUS * 2, PIN_RADIUS * 2, parent)
        self.pin: 'Pin' = pin
        self.gate_item: 'GateGraphicsItem' = parent
        
        self.setBrush(QBrush(COLOR_PIN))
        self.setPen(QPen(Qt.black, 1))
        self.setAcceptHoverEvents(True)
        self.setZValue(2)
        
        # Store original scale
        self._original_scale = 1.0
        self._hover_scale = 1.5
    
    def update_color(self) -> None:
        """Update pin color based on signal state."""
        if self.pin.value == 1:  # HIGH
            self.setBrush(QBrush(COLOR_HIGH))
        elif self.pin.value == 0:  # LOW
            self.setBrush(QBrush(COLOR_LOW))
        else:
            self.setBrush(QBrush(COLOR_UNDEFINED))
    
    def hoverEnterEvent(self, event) -> None:
        """Enlarge pin on hover."""
        self.setScale(self._hover_scale)
        self.setPen(QPen(QColor(255, 255, 255), 2))
        logger.debug(f"Pin hover: {self.gate_item.component.name}.{self.pin.name}")
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event) -> None:
        """Reset pin size on leave."""
        self.setScale(self._original_scale)
        self.setPen(QPen(Qt.black, 1))
        super().hoverLeaveEvent(event)
    
    def get_scene_pos(self) -> QPointF:
        """Get the pin's position in scene coordinates."""
        return self.scenePos()
    
    def is_output(self) -> bool:
        """Check if this is an output pin."""
        return self.pin.pin_type == PinType.OUTPUT
    
    def is_input(self) -> bool:
        """Check if this is an input pin."""
        return self.pin.pin_type == PinType.INPUT
    
    def __repr__(self) -> str:
        return f"PinGraphicsItem({self.pin.name}, {self.pin.pin_type.name})"