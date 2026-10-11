"""
Configuration, constants, and logging setup for the Digital Logic Simulator.
"""

from enum import Enum, auto
from PySide6.QtGui import QColor
import logging
import sys


# ============================================================================
# Signal States
# ============================================================================
LOW = 0
HIGH = 1
UNDEFINED = -1


# ============================================================================
# Enumerations
# ============================================================================
class PinType(Enum):
    """Pin direction type."""
    INPUT = auto()
    OUTPUT = auto()


class ComponentType(Enum):
    """Available component types."""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    XOR = "XOR"
    NAND = "NAND"
    NOR = "NOR"
    BUFFER = "BUFFER"
    SWITCH = "SWITCH"
    LED = "LED"
    CLOCK = "CLOCK"


# ============================================================================
# Color Scheme
# ============================================================================
COLOR_LOW = QColor(60, 120, 216)
COLOR_HIGH = QColor(255, 100, 100)
COLOR_UNDEFINED = QColor(128, 128, 128)
COLOR_WIRE_LOW = QColor(60, 120, 216)
COLOR_WIRE_HIGH = QColor(255, 80, 80)
COLOR_GATE_FILL = QColor(240, 240, 245)
COLOR_GATE_BORDER = QColor(40, 40, 60)
COLOR_PIN = QColor(80, 80, 100)
COLOR_PIN_HOVER = QColor(120, 120, 140)
COLOR_SWITCH_OFF = QColor(200, 200, 200)
COLOR_SWITCH_ON = QColor(100, 255, 100)
COLOR_LED_OFF = QColor(80, 80, 80)
COLOR_LED_ON = QColor(255, 50, 50)
COLOR_SELECTED = QColor(100, 180, 255)
COLOR_GRID = QColor(220, 220, 230)
COLOR_BACKGROUND = QColor(245, 245, 250)


# ============================================================================
# Grid and View Settings
# ============================================================================
GRID_SIZE = 20
MIN_ZOOM = 0.2
MAX_ZOOM = 5.0
ZOOM_FACTOR = 1.15


# ============================================================================
# Gate Dimensions
# ============================================================================
GATE_WIDTH = 100
GATE_HEIGHT = 60
SMALL_GATE_WIDTH = 80
SMALL_GATE_HEIGHT = 50
PIN_RADIUS = 6


# ============================================================================
# Simulation Settings
# ============================================================================
MAX_SIMULATION_ITERATIONS = 100
DEFAULT_CLOCK_SPEED_MS = 100
MIN_CLOCK_SPEED_MS = 10
MAX_CLOCK_SPEED_MS = 500
MIN_CLOCK_FREQUENCY_HZ = 0.1
MAX_CLOCK_FREQUENCY_HZ = 10.0


# ============================================================================
# Logging Configuration
# ============================================================================
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname:<8}{self.RESET}"
        return super().format(record)


def setup_logging(level: int = logging.DEBUG) -> logging.Logger:
    """Configure and return the main application logger."""
    logger = logging.getLogger("LogicSim")
    
    if not logger.handlers:
        logger.setLevel(level)
        
        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        
        # Colored formatter
        formatter = ColoredFormatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        ch.setFormatter(formatter)
        
        logger.addHandler(ch)
        
        # Prevent propagation to root logger
        logger.propagate = False
        
        logger.debug("Logger initialized")
    
    return logger


# Global logger instance
logger = setup_logging()