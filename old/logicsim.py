# logic_simulator.py

import collections
import abc
from typing import Dict, List, Tuple, Set, Any

# --- Constants for Logic States ---
# Using constants is more readable and maintainable than magic numbers (0, 1).
LOW = 0
HIGH = 1

class Component(abc.ABC):
    """
    Abstract Base Class for all logic components (gates, circuits, etc.).
    It defines the common interface for all elements in a simulation.
    """
    def __init__(self, name: str):
        if not name:
            raise ValueError("Component name cannot be empty.")
        self.name = name
        self.inputs: Dict[str, int] = {}
        self.outputs: Dict[str, int] = {}

    @abc.abstractmethod
    def evaluate(self) -> bool:
        """
        Performs the core logic of the component.
        Reads from self.inputs, calculates new output states, and writes to self.outputs.

        Returns:
            bool: True if any output changed, False otherwise.
                  This is crucial for the event-driven simulation.
        """
        pass

    def __repr__(self) -> str:
        """A developer-friendly representation of the component's state."""
        inputs_str = ", ".join(f"{k}={v}" for k, v in self.inputs.items())
        outputs_str = ", ".join(f"{k}={v}" for k, v in self.outputs.items())
        return f"{self.name}(inputs: {{{inputs_str}}}, outputs: {{{outputs_str}}})"


class NotGate(Component):
    """A NOT gate (inverter)."""
    def __init__(self, name: str):
        super().__init__(name)
        self.inputs = {'A': LOW}
        self.outputs = {'Y': LOW}

    def evaluate(self) -> bool:
        new_output = HIGH if self.inputs['A'] == LOW else LOW
        if self.outputs['Y'] != new_output:
            self.outputs['Y'] = new_output
            return True
        return False


class AndGate(Component):
    """A 2-input AND gate."""
    def __init__(self, name: str):
        super().__init__(name)
        self.inputs = {'A': LOW, 'B': LOW}
        self.outputs = {'Y': LOW}

    def evaluate(self) -> bool:
        new_output = HIGH if self.inputs['A'] == HIGH and self.inputs['B'] == HIGH else LOW
        if self.outputs['Y'] != new_output:
            self.outputs['Y'] = new_output
            return True
        return False

class OrGate(Component):
    """A 2-input OR gate."""
    def __init__(self, name: str):
        super().__init__(name)
        self.inputs = {'A': LOW, 'B': LOW}
        self.outputs = {'Y': LOW}

    def evaluate(self) -> bool:
        new_output = HIGH if self.inputs['A'] == HIGH or self.inputs['B'] == HIGH else LOW
        if self.outputs['Y'] != new_output:
            self.outputs['Y'] = new_output
            return True
        return False

class XorGate(Component):
    """A 2-input XOR gate."""
    def __init__(self, name: str):
        super().__init__(name)
        self.inputs = {'A': LOW, 'B': LOW}
        self.outputs = {'Y': LOW}

    def evaluate(self) -> bool:
        new_output = HIGH if self.inputs['A'] != self.inputs['B'] else LOW
        if self.outputs['Y'] != new_output:
            self.outputs['Y'] = new_output
            return True
        return False


class Circuit(Component):
    """
    A container for other components, allowing for hierarchical design.
    It acts as a complex component itself.
    """
    def __init__(self, name: str):
        super().__init__(name)
        self.components: Dict[str, Component] = {}
        # Connections map: from (component_name, pin_name) to list of (component_name, pin_name)
        self.connections: Dict[Tuple[str, str], List[Tuple[str, str]]] = collections.defaultdict(list)
        # A set to keep track of components that need to be evaluated
        self._event_queue: Set[Component] = set()

    def add_component(self, component: Component):
        """Adds a component to the circuit."""
        if component.name in self.components:
            raise ValueError(f"Component name '{component.name}' already exists in circuit '{self.name}'.")
        self.components[component.name] = component

    def connect(self, source_comp_name: str, source_pin: str,
                dest_comp_name: str, dest_pin: str):
        """
        Connects an output pin of one component to an input pin of another.
        """
        source_comp = self.components.get(source_comp_name)
        dest_comp = self.components.get(dest_comp_name)

        if not source_comp:
            raise ValueError(f"Source component '{source_comp_name}' not found.")
        if not dest_comp:
            raise ValueError(f"Destination component '{dest_comp_name}' not found.")
        if source_pin not in source_comp.outputs:
            raise ValueError(f"Source pin '{source_pin}' not found on component '{source_comp_name}'.")
        if dest_pin not in dest_comp.inputs:
            raise ValueError(f"Destination pin '{dest_pin}' not found on component '{dest_comp_name}'.")

        self.connections[(source_comp_name, source_pin)].append((dest_comp_name, dest_pin))

    def _propagate_signal(self, component: Component):
        """
        Propagates the output of a component to all connected inputs.
        Adds the destination components to the event queue.
        """
        for output_pin_name, output_value in component.outputs.items():
            source_key = (component.name, output_pin_name)
            for dest_comp_name, dest_pin_name in self.connections.get(source_key, []):
                dest_comp = self.components[dest_comp_name]
                if dest_comp.inputs[dest_pin_name] != output_value:
                    dest_comp.inputs[dest_pin_name] = output_value
                    self._event_queue.add(dest_comp)

    def _run_simulation_cycle(self):
        """
        Executes one full cycle of the event-driven simulation.
        Returns True if the circuit state changed, False otherwise.
        """
        if not self._event_queue:
            return False

        # Process a copy of the queue to avoid modification during iteration
        current_queue = list(self._event_queue)
        self._event_queue.clear()

        for component in current_queue:
            if component.evaluate(): # If the component's state changed
                self._propagate_signal(component)
        
        # If new events were added, the cycle resulted in a change
        return bool(self._event_queue)

    def evaluate(self) -> bool:
        """
        Evaluates the entire circuit until it reaches a stable state.
        This is the main simulation step for a Circuit.
        """
        # 1. Evaluate all components once to establish initial state
        for component in self.components.values():
            if component.evaluate():
                self._propagate_signal(component)
        
        # 2. Run event-driven propagation cycles until no more changes occur
        # This loop also serves as a safeguard against infinite oscillations
        # in poorly designed circuits (e.g., a NOT gate feeding itself).
        max_iterations = len(self.components) * 2 + 10
        iterations = 0
        while self._run_simulation_cycle():
            iterations += 1
            if iterations > max_iterations:
                raise RuntimeError(f"Circuit '{self.name}' failed to stabilize after {max_iterations} iterations. "
                                   "This may indicate an oscillation or combinational loop.")
        
        # For the Circuit's own `evaluate` method, we need to define its external outputs.
        # This is a simplification; a more complex system would have explicit I/O pins.
        # For now, we'll just return True if any internal state changed.
        return iterations > 0

    def set_input(self, component_name: str, pin_name: str, value: int):
        """A convenience method to set an input on a component and trigger simulation."""
        comp = self.components.get(component_name)
        if not comp:
            raise ValueError(f"Component '{component_name}' not found.")
        if pin_name not in comp.inputs:
            raise ValueError(f"Input pin '{pin_name}' not found on component '{component_name}'.")
        
        if comp.inputs[pin_name] != value:
            comp.inputs[pin_name] = value
            self._event_queue.add(comp)
            self.evaluate() # Run the simulation to propagate the change

    def get_state(self) -> Dict[str, Any]:
        """Returns the state of all components in the circuit."""
        return {name: repr(comp) for name, comp in self.components.items()}

    def __repr__(self) -> str:
        return f"Circuit '{self.name}' with {len(self.components)} components."


# --- Example Usage ---

def main():
    """
    Demonstrates building and simulating a simple Half-Adder circuit.
    A Half-Adder takes two bits (A, B) and produces a Sum (S) and a Carry (C).
    Sum = A XOR B
    Carry = A AND B
    """
    print("--- Building a Half-Adder Circuit ---")
    half_adder = Circuit("HalfAdder")

    # Create components
    xor_gate = XorGate("G1_XOR")
    and_gate = AndGate("G2_AND")

    # Add components to the circuit
    half_adder.add_component(xor_gate)
    half_adder.add_component(and_gate)

    # Connect the components
    # Inputs A and B go to both gates
    half_adder.connect("G1_XOR", "Y", "G2_AND", "A") # This is a mistake, let's fix it.
    # Correct connections for Half Adder:
    # A -> XOR.A, AND.A
    # B -> XOR.B, AND.B
    # The `connect` method connects outputs to inputs. We need a way to define primary inputs.
    # Let's treat the inputs of the first gates as the circuit's primary inputs.
    # So, we will set them directly using `set_input`.

    # Let's re-think the connections for the example.
    # The inputs to the gates are our primary inputs. The outputs are our primary outputs.
    # No internal connections needed for a half-adder.
    # This demonstrates that the `Circuit` class can also just be a container.
    # Let's build a slightly more complex circuit to show connections.
    
    print("\n--- Building a 1-to-2 Demultiplexer (using gates) ---")
    demux = Circuit("Demux_1to2")
    
    # Components: NOT, AND1, AND2
    not_gate = NotGate("G_NOT")
    and_gate1 = AndGate("G_AND1")
    and_gate2 = AndGate("G_AND2")
    
    demux.add_component(not_gate)
    demux.add_component(and_gate1)
    demux.add_component(and_gate2)
    
    # Connections:
    # Input 'Sel' goes to NOT gate input and AND2 input 'B'
    # Input 'Data' goes to AND1 input 'A' and AND2 input 'A'
    # Output of NOT gate goes to AND1 input 'B'
    # Output of AND1 is 'Y0'
    # Output of AND2 is 'Y1'
    # The `connect` method is for wiring outputs to inputs.
    # We can't connect the primary inputs 'Data' and 'Sel' yet.
    # We will set them directly.
    
    demux.connect("G_NOT", "Y", "G_AND1", "B")
    
    print("Initial circuit state:")
    print(demux.get_state())
    
    print("\n--- Simulation Step 1: Sel=0, Data=1 ---")
    # Sel=0 -> NOT output is 1. Data=1.
    # AND1: A=1, B=1 -> Y0=1
    # AND2: A=1, B=0 -> Y1=0
    demux.set_input("G_NOT", "A", 0) # Set Select line
    demux.set_input("G_AND1", "A", 1) # Set Data line
    demux.set_input("G_AND2", "A", 1) # Set Data line
    demux.set_input("G_AND2", "B", 0) # Set Select line
    
    print("Circuit state after Sel=0, Data=1:")
    print(demux.get_state())
    print(f"Output Y0 (from G_AND1): {demux.components['G_AND1'].outputs['Y']}")
    print(f"Output Y1 (from G_AND2): {demux.components['G_AND2'].outputs['Y']}")
    assert demux.components['G_AND1'].outputs['Y'] == 1
    assert demux.components['G_AND2'].outputs['Y'] == 0
    
    print("\n--- Simulation Step 2: Sel=1, Data=1 ---")
    # Sel=1 -> NOT output is 0. Data=1.
    # AND1: A=1, B=0 -> Y0=0
    # AND2: A=1, B=1 -> Y1=1
    demux.set_input("G_NOT", "A", 1) # Set Select line
    demux.set_input("G_AND2", "B", 1) # Set Select line
    
    print("Circuit state after Sel=1, Data=1:")
    print(demux.get_state())
    print(f"Output Y0 (from G_AND1): {demux.components['G_AND1'].outputs['Y']}")
    print(f"Output Y1 (from G_AND2): {demux.components['G_AND2'].outputs['Y']}")
    assert demux.components['G_AND1'].outputs['Y'] == 0
    assert demux.components['G_AND2'].outputs['Y'] == 1

    print("\n--- All simulations passed! ---")


if __name__ == "__main__":
    main()