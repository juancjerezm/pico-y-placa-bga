"""Plate parser — pure-function module for Colombian vehicle plate classification."""

from plate_parser.parser import ParseResult, PlateValidationError, parse_placa

__all__ = ["parse_placa", "ParseResult", "PlateValidationError"]
