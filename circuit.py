"""
Circuit container and simulation engine.
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Set, Any, Optional
from config import ComponentType, MAX_SIMULATION_ITERATIONS, logger
from pins import Pin
from gates import LogicComponent, COMPONENT_CLASSES, create_component


Connection = Tuple[str, str, str, str]  # (src_comp, src_pin, dst_comp, dst_pin)


class Circuit:
    """Main circuit container and simulation engine.
    
    Manages components, connections, and simulation state propagation.
    """
    
    def __init__(self):
        self.components: Dict[str, LogicComponent] = {}
        self.connections: List[Connection] = []
        self._event_queue: Set[str] = set()
        self._component_counts: Dict[ComponentType, int] = {}
        logger.info("Circuit initialized")
    
    def add_component(self, comp: LogicComponent) -> str:
        """Add a component and return its name.
        
        Args:
            comp: The component to add
            
        Returns:
            The component's name
            
        Raises:
            ValueError: If a component with the same name already exists
        """
        if comp.name in self.components:
            error_msg = f"Component '{comp.name}' already exists"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.components[comp.name] = comp
        self._component_counts[comp.comp_type] = \
            self._component_counts.get(comp.comp_type, 0) + 1
        logger.debug(f"Added component: {comp.name} ({comp.comp_type.value})")
        return comp.name
    
    def remove_component(self, name: str) -> bool:
        """Remove a component and all its connections.
        
        Args:
            name: The name of the component to remove
            
        Returns:
            True if component was removed, False if not found
        """
        if name not in self.components:
            logger.warning(f"Attempted to remove non-existent component: {name}")
            return False
        
        # Remove all connections involving this component
        removed_connections = [
            c for c in self.connections 
            if c[0] == name or c[2] == name
        ]
        
        for conn in removed_connections:
            self._remove_connection_internal(conn)
        
        # Clear pin connections
        comp = self.components[name]
        for pin in comp.get_all_pins():
            pin.clear_connections()
        
        # Update count
        comp_type = comp.comp_type
        if comp_type in self._component_counts:
            self._component_counts[comp_type] -= 1
        
        del self.components[name]
        logger.info(f"Removed component: {name} ({comp_type.value})")
        return True
    
    def connect(self, src_comp: str, src_pin: str, 
                dst_comp: str, dst_pin: str) -> bool:
        """Connect output pin to input pin.
        
        Args:
            src_comp: Source component name
            src_pin: Source output pin name
            dst_comp: Destination component name
            dst_pin: Destination input pin name
            
        Returns:
            True if connection was made
            
        Raises:
            ValueError: If connection is invalid
        """
        self._validate_connection(src_comp, src_pin, dst_comp, dst_pin)
        
        src = self.components[src_comp]
        dst = self.components[dst_comp]
        
        # Check for duplicate connection
        conn: Connection = (src_comp, src_pin, dst_comp, dst_pin)
        if conn in self.connections:
            logger.debug(f"Duplicate connection ignored: {conn}")
            return False
        
        # Remove existing connection to this input (only one driver allowed)
        self._disconnect_input(dst_comp, dst_pin)
        
        self.connections.append(conn)
        
        # Update pin references
        src.outputs[src_pin].add_connection(dst.inputs[dst_pin])
        dst.inputs[dst_pin].add_connection(src.outputs[src_pin])
        
        logger.info(f"Connected: {src_comp}.{src_pin} -> {dst_comp}.{dst_pin}")
        return True
    
    def disconnect(self, src_comp: str, src_pin: str, 
                   dst_comp: str, dst_pin: str) -> bool:
        """Remove a connection.
        
        Returns:
            True if connection was removed, False if not found
        """
        conn: Connection = (src_comp, src_pin, dst_comp, dst_pin)
        
        if conn not in self.connections:
            logger.warning(f"Connection not found: {conn}")
            return False
        
        return self._remove_connection_internal(conn)
    
    def _remove_connection_internal(self, conn: Connection) -> bool:
        """Internal connection removal without logging duplicate warning."""
        if conn not in self.connections:
            return False
            
        self.connections.remove(conn)
        
        src_comp, src_pin, dst_comp, dst_pin = conn
        src = self.components.get(src_comp)
        dst = self.components.get(dst_comp)
        
        if src and src_pin in src.outputs:
            src_pin_obj = src.outputs[src_pin]
            if dst and dst_pin in dst.inputs:
                src_pin_obj.remove_connection(dst.inputs[dst_pin])
        
        if dst and dst_pin in dst.inputs:
            dst_pin_obj = dst.inputs[dst_pin]
            if src and src_pin in src.outputs:
                dst_pin_obj.remove_connection(src.outputs[src_pin])
        
        logger.debug(f"Disconnected: {src_comp}.{src_pin} -> {dst_comp}.{dst_pin}")
        return True
    
    def _validate_connection(self, src_comp: str, src_pin: str,
                             dst_comp: str, dst_pin: str) -> None:
        """Validate a connection request.
        
        Raises:
            ValueError: If validation fails
        """
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
        
        # Prevent self-connection
        if src_comp == dst_comp:
            raise ValueError("Cannot connect a component to itself.")
    
    def _disconnect_input(self, dst_comp: str, dst_pin: str) -> None:
        """Remove any existing connection to an input pin."""
        to_remove = [
            c for c in self.connections 
            if c[2] == dst_comp and c[3] == dst_pin
        ]
        
        for conn in to_remove:
            self._remove_connection_internal(conn)
    
    def generate_name(self, comp_type: ComponentType) -> str:
        """Generate a unique component name."""
        count = self._component_counts.get(comp_type, 0) + 1
        name = f"{comp_type.value}_{count}"
        logger.debug(f"Generated name: {name}")
        return name
    
    def simulate(self) -> bool:
        """Run simulation until stable.
        
        Uses event-driven propagation: only components whose inputs
        have changed are re-evaluated.
        
        Returns:
            True if any changes occurred during simulation
        """
        # Add all components to initial queue
        for name in self.components:
            self._event_queue.add(name)
        
        iterations = 0
        changed = False
        
        while self._event_queue and iterations < MAX_SIMULATION_ITERATIONS:
            current_queue = list(self._event_queue)
            self._event_queue.clear()
            
            for comp_name in current_queue:
                if comp_name not in self.components:
                    continue
                
                comp = self.components[comp_name]
                
                if comp.evaluate():
                    changed = True
                    self._propagate_output(comp_name, comp)
            
            iterations += 1
        
        if iterations >= MAX_SIMULATION_ITERATIONS:
            logger.warning(f"Simulation reached max iterations ({MAX_SIMULATION_ITERATIONS})")
        
        if changed:
            logger.debug(f"Simulation completed in {iterations} iterations")
        
        return changed
    
    def _propagate_output(self, comp_name: str, comp: LogicComponent) -> None:
        """Propagate output changes to connected inputs."""
        for out_pin_name, out_pin in comp.outputs.items():
            for conn in self.connections:
                if conn[0] == comp_name and conn[1] == out_pin_name:
                    dst_comp_name, dst_pin_name = conn[2], conn[3]
                    
                    if dst_comp_name not in self.components:
                        continue
                    
                    dst_comp = self.components[dst_comp_name]
                    new_val = out_pin.value
                    
                    if dst_comp.inputs[dst_pin_name].value != new_val:
                        dst_comp.inputs[dst_pin_name].value = new_val
                        self._event_queue.add(dst_comp_name)
    
    def tick_clocks(self) -> bool:
        """Tick all clock components and propagate.
        
        Returns:
            True if any clock output changed
        """
        changed = False
        for comp in self.components.values():
            if hasattr(comp, 'tick') and callable(comp.tick):
                if comp.tick():
                    self._event_queue.add(comp.name)
                    changed = True
        
        if self._event_queue:
            self.simulate()
        
        return changed
    
    def reset(self) -> None:
        """Reset all components to initial state."""
        logger.info("Resetting all components")
        for comp in self.components.values():
            comp.reset()
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
            if hasattr(comp, 'state'):  # Switch
                comp_state['switch_state'] = comp.state
            if hasattr(comp, 'is_on'):  # LED
                comp_state['is_on'] = comp.is_on
            state[name] = comp_state
        return state
    
    def clear(self) -> None:
        """Remove all components and connections."""
        logger.info("Clearing circuit")
        self.components.clear()
        self.connections.clear()
        self._event_queue.clear()
        self._component_counts.clear()
    
    def to_dict(self) -> Dict[str, Any]:
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
            'connections': [list(c) for c in self.connections]
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserialize circuit from dictionary.
        
        Args:
            data: Dictionary containing circuit data
            
        Raises:
            ValueError: If data contains invalid component types
        """
        self.clear()
        
        for comp_data in data.get('components', []):
            try:
                comp_type = ComponentType(comp_data['type'])
                name = comp_data['name']
                comp = create_component(comp_type, name)
                self.add_component(comp)
            except ValueError as e:
                logger.error(f"Failed to load component: {e}")
                raise
        
        for conn in data.get('connections', []):
            if len(conn) == 4:
                try:
                    self.connect(*conn)
                except ValueError as e:
                    logger.warning(f"Skipping invalid connection: {e}")
        
        logger.info(f"Loaded circuit: {len(self.components)} components, {len(self.connections)} connections")
    
    def get_connected_wires(self, comp_name: str) -> List[Connection]:
        """Get all connections involving a component."""
        return [c for c in self.connections 
                if c[0] == comp_name or c[2] == comp_name]
    
    def get_input_connections(self, comp_name: str) -> List[Connection]:
        """Get all connections where this component is the destination."""
        return [c for c in self.connections if c[2] == comp_name]
    
    def get_output_connections(self, comp_name: str) -> List[Connection]:
        """Get all connections where this component is the source."""
        return [c for c in self.connections if c[0] == comp_name]
    
    def get_component_count(self) -> int:
        """Get the number of components."""
        return len(self.components)
    
    def get_connection_count(self) -> int:
        """Get the number of connections."""
        return len(self.connections)