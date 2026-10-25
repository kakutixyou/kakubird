"""
VSCode Modular Handler Package
backend/api/services/handlers/VSCode/
"""

from .VSCodeHandler import VSCodeHandler, VSCodePreResponder
from .VSCodeIntentParser import VSCodeIntent, VSCodeIntentParser
from .VSCodeKnowledgeService import VSCodeKnowledgeService
from .VSCodeLauncher import VSCodeLauncher
from .VSCodeResponseBuilder import VSCodeResponseBuilder
from .VSCodeTaskBuilder import VSCodeTaskBuilder
from .VSCodeWorkspaceInspector import FileDiagnosticsResult, VSCodeWorkspaceInspector
from .WorkspaceFileService import WorkspaceFileService

__all__ = [
    "VSCodeIntent",
    "VSCodeIntentParser",
    "VSCodeKnowledgeService",
    "VSCodeTaskBuilder",
    "WorkspaceFileService",
    "VSCodeLauncher",
    "VSCodeResponseBuilder",
    "VSCodeWorkspaceInspector",
    "FileDiagnosticsResult",
    "VSCodeHandler",
    "VSCodePreResponder",
]