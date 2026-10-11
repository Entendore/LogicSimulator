#!/usr/bin/env python3
"""
Digital Logic Simulator - Entry Point
"""

import sys
import logging
import traceback
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from config import logger


def parse_args():
    """Parse command line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Digital Logic Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_const',
        const=logging.DEBUG,
        default=logging.INFO,
        help='Enable verbose (debug) logging'
    )
    
    parser.add_argument(
        '-q', '--quiet',
        action='store_const',
        const=logging.WARNING,
        dest='log_level',
        help='Reduce logging to warnings only'
    )
    
    parser.add_argument(
        '--log-level',
        type=int,
        choices=[logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR],
        default=logging.INFO,
        help='Set log level (10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR)'
    )
    
    parser.add_argument(
        'file',
        nargs='?',
        help='Circuit file to open on startup (.json)'
    )
    
    return parser.parse_args()


def exception_hook(exc_type, exc_value, exc_tb):
    """Global exception hook to catch unhandled exceptions."""
    if exc_type is KeyboardInterrupt:
        sys.exit(0)
    
    logger.critical("=" * 60)
    logger.critical("UNHANDLED EXCEPTION")
    logger.critical("=" * 60)
    logger.critical(f"Type: {exc_type.__name__}")
    logger.critical(f"Value: {exc_value}")
    logger.critical("Traceback:")
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
    for line in tb_lines:
        logger.critical(line.rstrip())
    logger.critical("=" * 60)
    
    # Call the original exception hook
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def main():
    """Main entry point."""
    # Install global exception hook FIRST
    sys.excepthook = exception_hook
    
    args = parse_args()
    
    # Configure logging level based on args
    log_level = args.log_level if not args.verbose else args.verbose
    for handler in logger.handlers:
        handler.setLevel(log_level)
    logger.setLevel(log_level)
    
    logger.info("Starting Digital Logic Simulator")
    
    # Enable faulthandler for better segfault debugging
    try:
        import faulthandler
        faulthandler.enable()
        logger.debug("Faulthandler enabled for segfault debugging")
    except ImportError:
        pass
    
    # Create application
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Set application font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    try:
        # Import and create main window
        from ui import MainWindow
        
        window = MainWindow()
        window.show()
        
        # Open file if specified
        if args.file:
            logger.info(f"Opening file: {args.file}")
            window._load_from_file(args.file)
        
        logger.info("Application ready")
        
        exit_code = app.exec()
        logger.info(f"Application exited with code: {exit_code}")
        
        sys.exit(exit_code)
        
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        logger.critical(traceback.format_exc())
        
        # Try to show error dialog
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                None, 
                "Fatal Error",
                f"A fatal error occurred:\n\n{e}\n\nCheck the terminal for details."
            )
        except Exception:
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()