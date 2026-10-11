"""
Logic gate components and I/O components (AND, OR, NOT, XOR, NAND, NOR, BUFFER, Switch, LED, Clock).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Type
from config import (ComponentType, PinType, HIGH, LOW, 
                   MIN_CLOCK_FREQUENCY_HZ, MAX_CLOCK_FREQUENCY_HZ, logger)
from pins import Pin


class LogicComponent(ABC):
    """Abstract base class for all logic components.
    
    Attributes:
        comp_type: The type of component
        name: Unique identifier for this component instance
        inputs: Dictionary of input pins
        outputs: Dictionary of output pins
    """
    
    def __init__(self, comp_type: ComponentType, name: str):
        self.comp_type: ComponentType = comp_type
        self.name: str = name
        self.inputs: Dict[str, Pin] = {}
        self.outputs: Dict[str, Pin] = {}
        self._setup_pins()
        logger.debug(f"Created {comp_type.value} component: {name}")
    
    @abstractmethod
    def _setup_pins(self) -> None:
        """Set up input and output pins."""
        pass
    
    @abstractmethod
    def evaluate(self) -> bool:
        """Evaluate the component and return True if output changed."""
        pass
    
    def get_all_pins(self) -> List[Pin]:
        """Get all pins (inputs and outputs)."""
        return list(self.inputs.values()) + list(self.outputs.values())
    
    def get_input_value(self, name: str) -> int:
        """Get value of a specific input pin."""
        if name not in self.inputs:
            logger.warning(f"Input pin '{name}' not found on component '{self.name}'")
            return LOW
        return self.inputs[name].value
    
    def get_output_value(self, name: str) -> int:
        """Get value of a specific output pin."""
        if name not in self.outputs:
            logger.warning(f"Output pin '{name}' not found on component '{self.name}'")
            return LOW
        return self.outputs[name].value
    
    def set_output(self, name: str, value: int) -> bool:
        """Set output value and return True if changed."""
        if name not in self.outputs:
            logger.error(f"Output pin '{name}' not found on component '{self.name}'")
            return False
        
        old_value = self.outputs[name].value
        self.outputs[name].value = value
        
        if old_value != value:
            logger.debug(f"{self.name}.{name}: {old_value} -> {value}")
            return True
        return False
    
    def reset(self) -> None:
        """Reset all pins to LOW."""
        logger.debug(f"Resetting component: {self.name}")
        for pin in self.inputs.values():
            pin.value = LOW
        for pin in self.outputs.values():
            pin.value = LOW


# ============================================================================
# Basic Logic Gates
# ============================================================================

class AndGate(LogicComponent):
    """AND gate: Y = A AND B"""
    
    def __init__(self, name: str):
        super().__init__(ComponentType.AND, name)
    
    def _setup_pins(self) -> None:
        self.inputs = {'A': Pin('A', PinType.INPUT, 0), 
                       'B': Pin('B', PinType.INPUT, 1)}
        self.outputs = {'Y': Pin('Y', PinType.OUTPUT, 0)}
    
    def evaluate(self) -> bool:
        a, b = self.get_input_value('A'), self.get_input_value('B')
        new_val = HIGH if (a == HIGH and b == HIGH) else LOW
        return self.set_output('Y', new_val)


class OrGate(LogicComponent):
    """OR gate: Y = A OR B"""
    
    def __init__(self, name: str):
        super().__init__(ComponentType.OR, name)
    
    def _setup_pins(self) -> None:
        self.inputs = {'A': Pin('A', PinType.INPUT, 0), 
                       'B': Pin('B', PinType.INPUT, 1)}
        self.outputs = {'Y': Pin('Y', PinType.OUTPUT, 0)}
    
    def evaluate(self) -> bool:
        a, b = self.get_input_value('A'), self.get_input_value('B')
        new_val = HIGH if (a == HIGH or b == HIGH) else LOW
        return self.set_output('Y', new_val)


class NotGate(LogicComponent):
    """NOT gate (inverter): Y = NOT A"""
    
    def __init__(self, name: str):
        super().__init__(ComponentType.NOT, name)
    
    def _setup_pins(self) -> None:
        self.inputs = {'A': Pin('A', PinType.INPUT, 0)}
        self.outputs = {'Y': Pin('Y', PinType.OUTPUT, 0)}
    
    def evaluate(self) -> bool:
        new_val = HIGH if self.get_input_value('A') == LOW else LOW
        return self.set_output('Y', new_val)


class XorGate(LogicComponent):
    """XOR gate: Y = A XOR B"""
    
    def __init__(self, name: str):
        super().__init__(ComponentType.XOR, name)
    
    def _setup_pins(self) -> None:
        self.inputs = {'A': Pin('A', PinType.INPUT, 0), 
                       'B': Pin('B', PinType.INPUT, 1)}
        self.outputs = {'Y': Pin('Y', PinType.OUTPUT, 0)}
    
    def evaluate(self) -> bool:
        a, b = self.get_input_value('A'), self.get_input_value('B')
        new_val = HIGH if a != b else LOW
        return self.set_output('Y', new_val)


class NandGate(LogicComponent):
    """NAND gate: Y = NOT (A AND B)"""
    
    def __init__(self, name: str):
        super().__init__(ComponentType.NAND, name)
    
    def _setup_pins(self) -> None:
        self.inputs = {'A': Pin('A', PinType.INPUT, 0), 
                       'B': Pin('B', PinType.INPUT, 1)}
        self.outputs = {'Y': Pin('Y', PinType.OUTPUT, 0)}
    
    def evaluate(self) -> bool:
        a, b = self.get_input_value('A'), self.get_input_value('B')
        new_val = LOW if (a == HIGH and b == HIGH) else HIGH
        return self.set_output('Y', new_val)


class NorGate(LogicComponent):
    """NOR gate: Y = NOT (A OR B)"""
    
    def __init__(self, name: str):
        super().__init__(ComponentType.NOR, name)
    
    def _setup_pins(self) -> None:
        self.inputs = {'A': Pin('A', PinType.INPUT, 0), 
                       'B': Pin('B', PinType.INPUT, 1)}
        self.outputs = {'Y': Pin('Y', PinType.OUTPUT, 0)}
    
    def evaluate(self) -> bool:
        a, b = self.get_input_value('A'), self.get_input_value('B')
        new_val = LOW if (a == HIGH or b == HIGH) else HIGH
        return self.set_output('Y', new_val)


class BufferGate(LogicComponent):
    """Buffer gate: Y = A"""
    
    def __init__(self, name: str):
        super().__init__(ComponentType.BUFFER, name)
    
    def _setup_pins(self) -> None:
        self.inputs = {'A': Pin('A', PinType.INPUT, 0)}
        self.outputs = {'Y': Pin('Y', PinType.OUTPUT, 0)}
    
    def evaluate(self) -> bool:
        return self.set_output('Y', self.get_input_value('A'))


# ============================================================================
# I/O Components
# ============================================================================

class Switch(LogicComponent):
    """Toggle switch that outputs HIGH or LOW."""
    
    def __init__(self, name: str):
        super().__init__(ComponentType.SWITCH, name)
        self.state: bool = False
        logger.debug(f"Switch '{name}' created with initial state: OFF")
    
    def _setup_pins(self) -> None:
        self.inputs = {}
        self.outputs = {'Q': Pin('Q', PinType.OUTPUT, 0)}
    
    def toggle(self) -> bool:
        """Toggle the switch state. Returns True if state changed."""
        self.state = not self.state
        logger.info(f"Switch '{self.name}' toggled to {'ON' if self.state else 'OFF'}")
        return self.evaluate()
    
    def set_state(self, state: bool) -> bool:
        """Set the switch state explicitly. Returns True if state changed."""
        if self.state != state:
            self.state = state
            logger.info(f"Switch '{self.name}' set to {'ON' if state else 'OFF'}")
            return self.evaluate()
        return False
    
    def evaluate(self) -> bool:
        new_val = HIGH if self.state else LOW
        return self.set_output('Q', new_val)
    
    def reset(self) -> None:
        """Reset switch to off state."""
        self.state = False
        super().reset()


class LED(LogicComponent):
    """LED indicator that lights up when input is HIGH."""
    
    def __init__(self, name: str):
        super().__init__(ComponentType.LED, name)
        self.is_on: bool = False
    
    def _setup_pins(self) -> None:
        self.inputs = {'A': Pin('A', PinType.INPUT, 0)}
        self.outputs = {}
    
    def evaluate(self) -> bool:
        new_state = self.get_input_value('A') == HIGH
        if self.is_on != new_state:
            self.is_on = new_state
            if new_state:
                logger.info(f"LED '{self.name}' turned ON")
            return True
        return False
    
    def reset(self) -> None:
        """Reset LED to off state."""
        self.is_on = False
        super().reset()


class Clock(LogicComponent):
    """Clock signal generator with configurable frequency."""
    
    def __init__(self, name: str, frequency: float = 1.0):
        super().__init__(ComponentType.CLOCK, name)
        self.frequency: float = frequency
        self._tick_count: int = 0
        self.running: bool = True
        logger.debug(f"Clock '{name}' created with frequency: {frequency}Hz")
    
    def _setup_pins(self) -> None:
        self.inputs = {}
        self.outputs = {'Q': Pin('Q', PinType.OUTPUT, 0)}
    
    def get_period_ticks(self) -> int:
        """Calculate ticks per full period based on frequency."""
        return max(1, int(10 / self.frequency))
    
    def tick(self) -> bool:
        """Advance clock by one tick. Returns True if output changed."""
        if not self.running:
            return False
        
        self._tick_count += 1
        period = self.get_period_ticks()
        
        if self._tick_count % period == 0:
            new_val = HIGH if (self._tick_count // period) % 2 == 0 else LOW
            return self.set_output('Q', new_val)
        return False
    
    def evaluate(self) -> bool:
        """Clock is driven externally by tick()."""
        return False
    
    def reset(self) -> None:
        """Reset clock to initial state."""
        super().reset()
        self._tick_count = 0
        logger.debug(f"Clock '{self.name}' reset")
    
    def set_frequency(self, freq: float) -> None:
        """Set clock frequency."""
        old_freq = self.frequency
        self.frequency = max(MIN_CLOCK_FREQUENCY_HZ, min(MAX_CLOCK_FREQUENCY_HZ, freq))
        if old_freq != self.frequency:
            logger.info(f"Clock '{self.name}' frequency: {old_freq}Hz -> {self.frequency}Hz")


# ============================================================================
# Component Registry
# ============================================================================

COMPONENT_CLASSES: Dict[ComponentType, Type[LogicComponent]] = {
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


def create_component(comp_type: ComponentType, name: str) -> LogicComponent:
    """Factory function to create a component by type.
    
    Args:
        comp_type: The type of component to create
        name: The name for the new component
        
    Returns:
        A new LogicComponent instance
        
    Raises:
        ValueError: If comp_type is not recognized
    """
    comp_class = COMPONENT_CLASSES.get(comp_type)
    if comp_class is None:
        logger.error(f"Unknown component type: {comp_type}")
        raise ValueError(f"Unknown component type: {comp_type}")
    
    # Special handling for Clock which has extra parameter
    if comp_type == ComponentType.CLOCK:
        return comp_class(name, frequency=1.0)
    
    return comp_class(name)