"""
Digital Logic Simulator - Main Application Window and UI Components
"""

import sys
import json
from typing import Optional, Dict, Any, List
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QDockWidget, QTreeWidget, QTreeWidgetItem,
    QToolBar, QMessageBox, QFileDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QDoubleSpinBox, QCheckBox, QGroupBox, QSpinBox,
    QWidget, QPushButton
)
from PySide6.QtGui import QAction, QFont, QKeySequence
from PySide6.QtCore import Qt, QTimer, QSize, Signal

from config import (ComponentType, MIN_CLOCK_FREQUENCY_HZ, MAX_CLOCK_FREQUENCY_HZ,
                   DEFAULT_CLOCK_SPEED_MS, MIN_CLOCK_SPEED_MS, MAX_CLOCK_SPEED_MS, logger)
from circuit import Circuit
from scene_view import CircuitScene, CircuitView
from gate_graphics import GateGraphicsItem, GATE_GRAPHICS_MAP
from wire_graphics import WireGraphicsItem
from gates import Switch, Clock


class ComponentPalette(QDockWidget):
    """Dockable widget with available components."""
    
    component_selected = Signal(object)  # ComponentType or None
    
    def __init__(self):
        super().__init__("Components")
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        widget = QTreeWidget()
        widget.setHeaderLabel("Gate Types")
        widget.setAnimated(True)
        widget.setIndentation(10)
        widget.setMinimumWidth(150)
        
        # Basic gates category
        basic = QTreeWidgetItem(widget, ["Basic Gates"])
        basic.setExpanded(True)
        for gate_type in [ComponentType.AND, ComponentType.OR, ComponentType.NOT,
                          ComponentType.XOR, ComponentType.NAND, ComponentType.NOR,
                          ComponentType.BUFFER]:
            item = QTreeWidgetItem(basic, [gate_type.value])
            item.setData(0, Qt.UserRole, gate_type)
            item.setToolTip(0, f"Add {gate_type.value} gate")
        
        # I/O components category
        io = QTreeWidgetItem(widget, ["Input/Output"])
        io.setExpanded(True)
        for comp_type in [ComponentType.SWITCH, ComponentType.LED, ComponentType.CLOCK]:
            item = QTreeWidgetItem(io, [comp_type.value])
            item.setData(0, Qt.UserRole, comp_type)
            tooltip = {
                ComponentType.SWITCH: "Toggle switch (click to toggle)",
                ComponentType.LED: "LED indicator",
                ComponentType.CLOCK: "Clock signal generator"
            }
            item.setToolTip(0, tooltip.get(comp_type, ""))
        
        widget.itemClicked.connect(self._on_item_clicked)
        widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        self.tree = widget
        self.setWidget(widget)
        self._selected_type: Optional[ComponentType] = None
        
        logger.debug("ComponentPalette created")
    
    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle item click."""
        data = item.data(0, Qt.UserRole)
        if data is not None:
            self._selected_type = data
            self.component_selected.emit(data)
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle item double click."""
        data = item.data(0, Qt.UserRole)
        if data is not None:
            self.component_selected.emit(data)
    
    def get_selected_type(self) -> Optional[ComponentType]:
        """Get currently selected component type."""
        return self._selected_type
    
    def clear_selection(self) -> None:
        """Clear the selected component type."""
        self._selected_type = None
        self.tree.clearSelection()


class PropertiesPanel(QDockWidget):
    """Dockable widget showing component properties."""
    
    def __init__(self):
        super().__init__("Properties")
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        self._setup_ui()
        self._current_gate: Optional[GateGraphicsItem] = None
        
        logger.debug("PropertiesPanel created")
    
    def _setup_ui(self) -> None:
        """Set up the UI."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.name_label = QLabel("Name: -")
        self.name_label.setFont(QFont("Consolas", 10))
        self.type_label = QLabel("Type: -")
        
        self.inputs_group = QGroupBox("Inputs")
        self.inputs_layout = QVBoxLayout()
        self.inputs_group.setLayout(self.inputs_layout)
        
        self.outputs_group = QGroupBox("Outputs")
        self.outputs_layout = QVBoxLayout()
        self.outputs_group.setLayout(self.outputs_layout)
        
        self.extra_container = QVBoxLayout()
        
        layout.addWidget(self.name_label)
        layout.addWidget(self.type_label)
        layout.addWidget(self.inputs_group)
        layout.addWidget(self.outputs_group)
        layout.addLayout(self.extra_container)
        layout.addStretch()
        
        self.setWidget(widget)
        self._extra_widgets: List[QWidget] = []
    
    def update_properties(self, gate: Optional[GateGraphicsItem]) -> None:
        """Update the properties panel for the given gate."""
        self._clear_extra_widgets()
        self._current_gate = gate
        
        # Clear labels
        self._clear_layout(self.inputs_layout)
        self._clear_layout(self.outputs_layout)
        
        if gate is None:
            self.name_label.setText("Name: -")
            self.type_label.setText("Type: -")
            self.inputs_group.setVisible(False)
            self.outputs_group.setVisible(False)
            return
        
        # Check if gate is still valid
        if gate.component is None:
            return
            
        comp = gate.component
        self.name_label.setText(f"Name: {comp.name}")
        self.type_label.setText(f"Type: {comp.comp_type.value}")
        
        # Show inputs
        has_inputs = len(comp.inputs) > 0
        self.inputs_group.setVisible(has_inputs)
        for name, pin in comp.inputs.items():
            color = "#FF6464" if pin.value == 1 else "#3C78D8"
            label = QLabel(f"{name}: <span style='color:{color}'>{pin.value}</span>")
            self.inputs_layout.addWidget(label)
        
        # Show outputs
        has_outputs = len(comp.outputs) > 0
        self.outputs_group.setVisible(has_outputs)
        for name, pin in comp.outputs.items():
            color = "#FF6464" if pin.value == 1 else "#3C78D8"
            label = QLabel(f"{name}: <span style='color:{color}'>{pin.value}</span>")
            self.outputs_layout.addWidget(label)
        
        # Extra controls for specific components
        if isinstance(comp, Clock):
            self._add_clock_controls(comp, gate)
        elif isinstance(comp, Switch):
            self._add_switch_controls(comp, gate)
    
    def _add_clock_controls(self, clock: Clock, gate: GateGraphicsItem) -> None:
        """Add clock-specific controls."""
        group = QGroupBox("Clock Settings")
        layout = QVBoxLayout()
        
        # Frequency control
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Frequency (Hz):"))
        freq_spin = QDoubleSpinBox()
        freq_spin.setRange(MIN_CLOCK_FREQUENCY_HZ, MAX_CLOCK_FREQUENCY_HZ)
        freq_spin.setValue(clock.frequency)
        freq_spin.setSingleStep(0.1)
        freq_spin.setDecimals(1)
        freq_spin.valueChanged.connect(lambda v: self._set_clock_freq(clock, v))
        freq_layout.addWidget(freq_spin)
        layout.addLayout(freq_layout)
        
        # Running control
        running_check = QCheckBox("Running")
        running_check.setChecked(clock.running)
        running_check.toggled.connect(lambda v: self._set_clock_running(clock, v))
        layout.addWidget(running_check)
        
        group.setLayout(layout)
        self.extra_container.addWidget(group)
        self._extra_widgets.append(group)
    
    def _add_switch_controls(self, switch: Switch, gate: GateGraphicsItem) -> None:
        """Add switch-specific controls."""
        group = QGroupBox("Switch Control")
        layout = QVBoxLayout()
        
        btn = QPushButton("Toggle Switch")
        btn.clicked.connect(lambda: self._toggle_switch(switch, gate))
        layout.addWidget(btn)
        
        state_label = QLabel(f"State: {'ON' if switch.state else 'OFF'}")
        state_label.setObjectName("switchState")
        layout.addWidget(state_label)
        
        group.setLayout(layout)
        self.extra_container.addWidget(group)
        self._extra_widgets.append(group)
    
    def _set_clock_freq(self, clock: Clock, freq: float) -> None:
        """Set clock frequency."""
        clock.set_frequency(freq)
    
    def _set_clock_running(self, clock: Clock, running: bool) -> None:
        """Set clock running state."""
        clock.running = running
        logger.info(f"Clock '{clock.name}' {'started' if running else 'stopped'}")
    
    def _toggle_switch(self, switch: Switch, gate: GateGraphicsItem) -> None:
        """Toggle switch and update."""
        switch.toggle()
        gate.update_visuals()
        scene = gate.scene()
        if scene and hasattr(scene, 'simulate'):
            scene.simulate()
        self.update_properties(gate)
    
    def _clear_extra_widgets(self) -> None:
        """Remove extra widgets from layout."""
        for widget in self._extra_widgets:
            self.extra_container.removeWidget(widget)
            widget.deleteLater()
        self._extra_widgets.clear()
    
    def _clear_layout(self, layout) -> None:
        """Clear all items from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Digital Logic Simulator")
        self.setMinimumSize(1000, 700)
        self.resize(1400, 900)
        
        logger.info("=" * 50)
        logger.info("Digital Logic Simulator Starting")
        logger.info("=" * 50)
        
        # Core objects
        self.circuit = Circuit()
        self.scene = CircuitScene(self.circuit)
        self.view = CircuitView(self.scene)
        self.setCentralWidget(self.view)
        
        # UI components
        self.palette = ComponentPalette()
        self.properties = PropertiesPanel()
        
        # Clock timer
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self._on_clock_tick)
        self.clock_running = False
        self.clock_speed = DEFAULT_CLOCK_SPEED_MS
        
        # File tracking
        self._current_file: Optional[str] = None
        self._is_modified = False
        
        # Setup UI
        self._setup_docks()
        self._setup_menus()
        self._setup_toolbars()
        self._setup_statusbar()
        self._connect_signals()
        
        # Center view
        self.view.centerOn(0, 0)
        
        logger.info("MainWindow initialized")
    
    def _setup_docks(self) -> None:
        """Setup dock widgets."""
        self.addDockWidget(Qt.LeftDockWidgetArea, self.palette)
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties)
    
    def _setup_menus(self) -> None:
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_action = QAction("&New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_circuit)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_circuit)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_circuit)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self._save_circuit_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        delete_action = QAction("&Delete Selected", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self._delete_selected)
        edit_menu.addAction(delete_action)
        
        edit_menu.addSeparator()
        
        select_all_action = QAction("Select &All", self)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        select_all_action.triggered.connect(self._select_all)
        edit_menu.addAction(select_all_action)
        
        # Simulation menu
        sim_menu = menubar.addMenu("&Simulation")
        
        self.run_action = QAction("&Run Clocks", self)
        self.run_action.setCheckable(True)
        self.run_action.setShortcut("F5")
        self.run_action.triggered.connect(self._toggle_clock_running)
        sim_menu.addAction(self.run_action)
        
        step_action = QAction("&Step Clocks", self)
        step_action.setShortcut("F6")
        step_action.triggered.connect(self._step_clocks)
        sim_menu.addAction(step_action)
        
        reset_action = QAction("&Reset", self)
        reset_action.setShortcut("F7")
        reset_action.triggered.connect(self._reset_simulation)
        sim_menu.addAction(reset_action)
        
        # Speed submenu
        speed_menu = sim_menu.addMenu("Clock &Speed")
        
        speeds = [("Slow (200ms)", 200), ("Normal (100ms)", 100), 
                  ("Fast (50ms)", 50), ("Very Fast (20ms)", 20)]
        for name, speed in speeds:
            action = QAction(name, self)
            action.setData(speed)
            action.triggered.connect(lambda checked, s=speed: self._set_clock_speed(s))
            speed_menu.addAction(action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self.view.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self.view.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        fit_action = QAction("&Fit to View", self)
        fit_action.setShortcut("Ctrl+0")
        fit_action.triggered.connect(self.view.fit_to_scene)
        view_menu.addAction(fit_action)
        
        reset_zoom_action = QAction("Reset &Zoom", self)
        reset_zoom_action.setShortcut("Ctrl+9")
        reset_zoom_action.triggered.connect(self.view.reset_zoom)
        view_menu.addAction(reset_zoom_action)
        
        view_menu.addSeparator()
        
        grid_action = QAction("Show &Grid", self)
        grid_action.setCheckable(True)
        grid_action.setChecked(True)
        grid_action.triggered.connect(self._toggle_grid)
        view_menu.addAction(grid_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
        help_action = QAction("&Help", self)
        help_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        help_action.triggered.connect(self._show_help)
        help_menu.addAction(help_action)
    
    def _setup_toolbars(self) -> None:
        """Setup toolbars."""
        # Main toolbar
        toolbar = QToolBar("Main")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Simulation controls
        self.run_btn = QAction("▶ Run", self)
        self.run_btn.setCheckable(True)
        self.run_btn.triggered.connect(self._toggle_clock_running)
        toolbar.addAction(self.run_btn)
        
        step_btn = QAction("⏭ Step", self)
        step_btn.triggered.connect(self._step_clocks)
        toolbar.addAction(step_btn)
        
        reset_btn = QAction("⏹ Reset", self)
        reset_btn.triggered.connect(self._reset_simulation)
        toolbar.addAction(reset_btn)
        
        toolbar.addSeparator()
        
        # Zoom controls
        zoom_in_btn = QAction("🔍+", self)
        zoom_in_btn.triggered.connect(self.view.zoom_in)
        toolbar.addAction(zoom_in_btn)
        
        zoom_out_btn = QAction("🔍-", self)
        zoom_out_btn.triggered.connect(self.view.zoom_out)
        toolbar.addAction(zoom_out_btn)
        
        fit_btn = QAction("⊞ Fit", self)
        fit_btn.triggered.connect(self.view.fit_to_scene)
        toolbar.addAction(fit_btn)
        
        toolbar.addSeparator()
        
        # Speed control
        speed_spin = QSpinBox()
        speed_spin.setRange(MIN_CLOCK_SPEED_MS, MAX_CLOCK_SPEED_MS)
        speed_spin.setValue(DEFAULT_CLOCK_SPEED_MS)
        speed_spin.setSuffix(" ms")
        speed_spin.setToolTip("Clock tick interval (ms)")
        speed_spin.valueChanged.connect(self._set_clock_speed)
        toolbar.addWidget(QLabel(" Speed: "))
        toolbar.addWidget(speed_spin)
        self._speed_spin = speed_spin
    
    def _setup_statusbar(self) -> None:
        """Setup status bar."""
        self.statusBar().showMessage("Ready - Select a component from the palette and click on the canvas")
        
        # Add component count label
        self._comp_count_label = QLabel("Components: 0")
        self._wire_count_label = QLabel("Wires: 0")
        self._sim_state_label = QLabel("Simulation: Idle")
        self.statusBar().addPermanentWidget(self._comp_count_label)
        self.statusBar().addPermanentWidget(self._wire_count_label)
        self.statusBar().addPermanentWidget(self._sim_state_label)
    
    def _connect_signals(self) -> None:
        """Connect signals."""
        self.scene.circuit_changed.connect(self._on_circuit_changed)
        self.scene.simulation_updated.connect(self._on_simulation_updated)
        self.scene.selection_changed_signal.connect(self.properties.update_properties)
        self.scene.component_placed.connect(self._on_component_placed)
        
        # Handle placing components from palette
        self.palette.component_selected.connect(self._on_component_type_selected)
    
    def _on_component_type_selected(self, comp_type: ComponentType) -> None:
        """Handle component type selection from palette."""
        self.statusBar().showMessage(
            f"Click on canvas to place {comp_type.value} component")
        logger.debug(f"Selected component type: {comp_type.value}")
    
    def _on_component_placed(self, comp_type: ComponentType) -> None:
        """Handle component placement."""
        # Keep the selected type so user can place multiple
        self.statusBar().showMessage(
            f"Placed {comp_type.value} - Click again to place more, or select another component", 3000)
    
    def _on_circuit_changed(self) -> None:
        """Handle circuit changes."""
        self._is_modified = True
        self._update_counts()
    
    def _on_simulation_updated(self) -> None:
        """Handle simulation updates."""
        # Update properties panel if something is selected
        selected = self.scene.selectedItems()
        for item in selected:
            if isinstance(item, GateGraphicsItem):
                self.properties.update_properties(item)
                break
        
        self._sim_state_label.setText("Simulation: Active")
    
    def _update_counts(self) -> None:
        """Update status bar counts."""
        self._comp_count_label.setText(f"Components: {len(self.scene.gate_items)}")
        self._wire_count_label.setText(f"Wires: {len(self.scene.wire_items)}")
    
    def _toggle_grid(self, show: bool) -> None:
        """Toggle grid visibility."""
        self.scene.show_grid = show
        self.scene.update()
        logger.debug(f"Grid {'shown' if show else 'hidden'}")
    
    # File operations
    
    def _new_circuit(self) -> None:
        """Create new circuit."""
        if self._is_modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "Do you want to save changes before creating a new circuit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | 
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            if reply == QMessageBox.StandardButton.Yes:
                if not self._save_circuit():
                    return
        
        self._stop_clocks()
        self.scene.clear_circuit()
        self._current_file = None
        self._is_modified = False
        self._update_title()
        self.statusBar().showMessage("New circuit created")
        logger.info("New circuit created")
    
    def _open_circuit(self) -> None:
        """Open circuit from file."""
        if self._is_modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "Do you want to save changes before opening?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | 
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            if reply == QMessageBox.StandardButton.Yes:
                if not self._save_circuit():
                    return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Circuit", "", "Circuit Files (*.json);;All Files (*)"
        )
        
        if file_path:
            self._load_from_file(file_path)
    
    def _load_from_file(self, file_path: str) -> None:
        """Load circuit from file."""
        try:
            logger.info(f"Loading circuit from: {file_path}")
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            self._stop_clocks()
            self.scene.clear_circuit()
            
            # Store positions if available
            positions = {c['name']: (c.get('x', 0), c.get('y', 0)) 
                        for c in data.get('components', [])}
            
            self.circuit.from_dict(data)
            
            # Recreate graphics items with positions
            for name, comp in self.circuit.components.items():
                x, y = positions.get(name, (0, 0))
                graphics_class = GATE_GRAPHICS_MAP.get(comp.comp_type, GateGraphicsItem)
                gate_item = graphics_class(comp, x, y)
                self.scene.addItem(gate_item)
                self.scene.gate_items[name] = gate_item
            
            # Recreate wires
            for conn in self.circuit.connections:
                if len(conn) == 4:
                    src_gate = self.scene.gate_items.get(conn[0])
                    dst_gate = self.scene.gate_items.get(conn[2])
                    if src_gate and dst_gate:
                        wire = WireGraphicsItem(src_gate, conn[1], 
                                              dst_gate, conn[3], conn)
                        self.scene.addItem(wire)
                        self.scene.wire_items.append(wire)
            
            self._current_file = file_path
            self._is_modified = False
            self._update_title()
            self._update_counts()
            self.statusBar().showMessage(f"Opened: {file_path}")
            
            # Run initial simulation
            self.scene.simulate()
            
            logger.info(f"Circuit loaded successfully: {len(self.circuit.components)} components")
            
        except Exception as e:
            logger.error(f"Failed to load circuit: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open file:\n{e}")
    
    def _save_circuit(self) -> bool:
        """Save circuit to current file."""
        if self._current_file:
            return self._save_to_file(self._current_file)
        return self._save_circuit_as()
    
    def _save_circuit_as(self) -> bool:
        """Save circuit to new file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Circuit", "", "Circuit Files (*.json);;All Files (*)"
        )
        
        if file_path:
            if not file_path.endswith('.json'):
                file_path += '.json'
            return self._save_to_file(file_path)
        return False
    
    def _save_to_file(self, file_path: str) -> bool:
        """Save circuit to specified file."""
        try:
            logger.info(f"Saving circuit to: {file_path}")
            
            # Get positions from graphics items
            data = self.circuit.to_dict()
            for comp_data in data['components']:
                name = comp_data['name']
                if name in self.scene.gate_items:
                    pos = self.scene.gate_items[name].pos()
                    comp_data['x'] = pos.x()
                    comp_data['y'] = pos.y()
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            self._current_file = file_path
            self._is_modified = False
            self._update_title()
            self.statusBar().showMessage(f"Saved: {file_path}")
            
            logger.info(f"Circuit saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save circuit: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")
            return False
    
    def _update_title(self) -> None:
        """Update window title."""
        title = "Digital Logic Simulator"
        if self._current_file:
            name = Path(self._current_file).name
            modified = " *" if self._is_modified else ""
            title = f"{name}{modified} - {title}"
        self.setWindowTitle(title)
    
    # Edit operations
    
    def _delete_selected(self) -> None:
        """Delete selected items."""
        self.scene._delete_selected()
    
    def _select_all(self) -> None:
        """Select all items."""
        for item in self.scene.items():
            if isinstance(item, (GateGraphicsItem, WireGraphicsItem)):
                item.setSelected(True)
    
    # Simulation operations
    
    def _toggle_clock_running(self, checked: bool) -> None:
        """Toggle clock simulation."""
        if checked:
            self._start_clocks()
        else:
            self._stop_clocks()
    
    def _start_clocks(self) -> None:
        """Start clock simulation."""
        self.clock_running = True
        self.clock_timer.start(self.clock_speed)
        self.run_action.setChecked(True)
        self.run_btn.setText("⏸ Pause")
        self.run_btn.setChecked(True)
        self._sim_state_label.setText("Simulation: Running")
        self.statusBar().showMessage("Clock simulation running", 2000)
        logger.info(f"Clock simulation started (interval: {self.clock_speed}ms)")
    
    def _stop_clocks(self) -> None:
        """Stop clock simulation."""
        self.clock_running = False
        self.clock_timer.stop()
        self.run_action.setChecked(False)
        self.run_btn.setText("▶ Run")
        self.run_btn.setChecked(False)
        self._sim_state_label.setText("Simulation: Stopped")
        logger.info("Clock simulation stopped")
    
    def _on_clock_tick(self) -> None:
        """Handle clock tick."""
        self.scene.tick_clocks()
    
    def _step_clocks(self) -> None:
        """Step clocks once."""
        self.scene.tick_clocks()
        self.statusBar().showMessage("Stepped clocks", 1000)
        logger.debug("Clock step executed")
    
    def _reset_simulation(self) -> None:
        """Reset simulation."""
        self._stop_clocks()
        self.circuit.reset()
        self.scene.update_all_visuals()
        self._sim_state_label.setText("Simulation: Reset")
        self.statusBar().showMessage("Simulation reset", 2000)
        logger.info("Simulation reset")
    
    def _set_clock_speed(self, speed: int) -> None:
        """Set clock tick speed."""
        self.clock_speed = speed
        self._speed_spin.setValue(speed)
        if self.clock_running:
            self.clock_timer.setInterval(speed)
        logger.debug(f"Clock speed set to {speed}ms")
    
    # Help
    
    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self, "About Digital Logic Simulator",
            "<h2>Digital Logic Simulator</h2>"
            "<p>A visual tool for designing and simulating digital logic circuits.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Drag and drop gate placement</li>"
            "<li>Real-time signal propagation</li>"
            "<li>Multiple gate types (AND, OR, NOT, XOR, NAND, NOR, BUFFER)</li>"
            "<li>Interactive switches and LED indicators</li>"
            "<li>Clock signal generator</li>"
            "<li>Save/Load circuits</li>"
            "</ul>"
            "<p><b>Controls:</b></p>"
            "<ul>"
            "<li>Left-click on pin and drag to connect</li>"
            "<li>Left-click on switch to toggle</li>"
            "<li>Double-click on switch to toggle</li>"
            "<li>Middle-click drag to pan</li>"
            "<li>Scroll wheel to zoom</li>"
            "<li>Delete key to remove selected items</li>"
            "<li>Escape to cancel wire drawing</li>"
            "</ul>"
        )
    
    def _show_help(self) -> None:
        """Show help dialog."""
        QMessageBox.information(
            self, "Help",
            "<h2>Getting Started</h2>"
            "<ol>"
            "<li>Select a component type from the left palette</li>"
            "<li>Click on the canvas to place it</li>"
            "<li>Click on an output pin (right side) and drag to an input pin (left side)</li>"
            "<li>Click on switches to toggle them</li>"
            "<li>Press F5 or click Run to start clock simulation</li>"
            "</ol>"
            "<h2>Tips</h2>"
            "<ul>"
            "<li>You can start a wire from either an input or output pin</li>"
            "<li>Only one connection per input pin is allowed</li>"
            "<li>Use middle mouse button to pan the view</li>"
            "<li>Use Ctrl+0 to fit all components in view</li>"
            "<li>Press Escape to cancel wire drawing</li>"
            "</ul>"
        )
    
    def closeEvent(self, event) -> None:
        """Handle window close."""
        if self._is_modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "Do you want to save changes before closing?",
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if reply == QMessageBox.StandardButton.Save:
                if not self._save_circuit():
                    event.ignore()
                    return
        
        self._stop_clocks()
        logger.info("Application closing")
        event.accept()