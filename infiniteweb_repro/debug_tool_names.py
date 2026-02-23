from openhands.tools.terminal.definition import TerminalTool
from openhands.tools.file_editor.definition import FileEditorTool
from openhands.sdk.tool.registry import list_registered_tools

print(f"TerminalTool.name: {TerminalTool.name}")
print(f"FileEditorTool.name: {FileEditorTool.name}")
print(f"Registered tools: {list_registered_tools()}")
