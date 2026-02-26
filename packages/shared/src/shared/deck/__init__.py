"""Shared deck builder engine and universal PPTX generation."""

from shared.deck.engine import DeckBuilder, SlideContent
from shared.deck.universal import build_deck_from_results

__all__ = ["DeckBuilder", "SlideContent", "build_deck_from_results"]
