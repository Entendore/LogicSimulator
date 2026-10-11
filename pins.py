"""
Pin class for logic components.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING
from config import PinType, LOW, logger

if TYPE_CHECKING:
    pass


class Pin:
    """Represents a connection point on a logic component.
    
    Attributes:
        name: Human-readable pin name (e.g., 'A', 'B', 'Y')
        pin_type: Whether this is an INPUT or OUTPUT pin
        index: Pin index for ordering
        value: Current signal value (LOW=0, HIGH=1, UNDEFINED=-1)
        connected_to: List of pins this pin is connected to
    """
    
    __slots__ = ('name', 'pin_type', 'index', 'value', 'connected_to')
    
    def __init__(self, name: str, pin_type: PinType, index: int = 0):
        self.name: str = name
        self.pin_type: PinType = pin_type
        self.index: int = index
        self.value: int = LOW
        self.connected_to: List[Pin] = []
    
    def __repr__(self) -> str:
        state = "HIGH" if self.value == 1 else "LOW" if self.value == 0 else "UNDEF"
        return f"Pin({self.name}, {self.pin_type.name}, {state})"
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Pin):
            return NotImplemented
        return id(self) == id(other)
    
    def __hash__(self) -> int:
        return id(self)
    
    def is_high(self) -> bool:
        """Check if pin value is HIGH."""
        return self.value == 1
    
    def is_low(self) -> bool:
        """Check if pin value is LOW."""
        return self.value == 0
    
    def is_connected(self) -> bool:
        """Check if pin has any connections."""
        return len(self.connected_to) > 0
    
    def clear_connections(self) -> None:
        """Remove all connections from this pin."""
        if self.connected_to:
            logger.debug(f"Clearing {len(self.connected_to)} connections from pin '{self.name}'")
            self.connected_to.clear()
    
    def add_connection(self, other: Pin) -> bool:
        """Add a connection to another pin.
        
        Returns:
            True if connection was added, False if already connected
        """
        if other is self:
            logger.warning(f"Attempted to connect pin '{self.name}' to itself")
            return False
            
        if other not in self.connected_to:
            self.connected_to.append(other)
            logger.debug(f"Connected pin '{self.name}' to '{other.name}'")
            return True
        return False
    
    def remove_connection(self, other: Pin) -> bool:
        """Remove a connection to another pin.
        
        Returns:
            True if connection was removed, False if not connected
        """
        if other in self.connected_to:
            self.connected_to.remove(other)
            logger.debug(f"Disconnected pin '{self.name}' from '{other.name}'")
            return True
        return False