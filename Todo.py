import shutil
import time
import msvcrt
import sys
import os
import base64
from ctypes import *
from datetime import datetime, date

# App settings
FPS = 30  # screen refresh rate
MIN_SIDE_WIDTH = 20  # min side panel width
MAX_SIDE_WIDTH_PERCENT = 33  # max side %
INFO_PANEL_HEIGHT = 7  # info panel height

# Priority options
PRIORITIES = ["High", "Medium", "Low", "None"]  # priorities
SORT_MODES = ["priority", "deadline", "created"]  # sort modes

# Alert symbols
DEADLINE_TODAY = "!"  # due soon
DEADLINE_PAST = "!"   # overdue

# Terminal colors
NORMAL = "\033[0m"      # reset
BLUE = "\033[34m"       # blue
GREEN = "\033[32m"      # green
RED = "\033[31m"        # red
YELLOW = "\033[33m"     # yellow
CYAN = "\033[36m"       # cyan
MAGENTA = "\033[35m"    # magenta
GRAY = "\033[90m"       # gray
WHITE = "\033[97m"      # white
BLUE_BG = "\033[44m"    # blue bg

# Color groups
SELECTED_COLOR = BLUE
ACTIVE_COLOR = GREEN
PRIORITY_COLORS = [RED, YELLOW, GREEN, WHITE]  # Colors for each priority level
INFO_LABEL_COLOR = CYAN
DEADLINE_COLOR = GRAY
CREATED_COLOR = GRAY
STATUS_OK = GREEN
STATUS_WARN = YELLOW
TAB_BG = BLUE_BG
TAB_FG = WHITE

# Terminal control
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
CLEAR_SCREEN = "\033[2J"
MOVE_TO_TOP = "\033[H"
DISABLE_LINEWRAP = "\033[7l"
DISABLE_SCROLL = "\033[r"
ALT_SCREEN = "\033[?1049h"
NORMAL_SCREEN = "\033[?1049l"

# Windows settings
STD_OUTPUT_HANDLE = -11
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
ENABLE_PROCESSED_OUTPUT = 0x0001
HELP_COLOR = "\033[96m"  # light cyan for help text
ALERT_BG = "\033[41m"  # red background for alert badge

# App state
app_state = {
    "active_tab": "topics",  # topics/todos/notes
    "nav_mode": True,        # nav vs focus
    "topics": [],           # topics list
    "todos": {},           # todos by topic
    "topic_index": 0,       # selected topic
    "todo_index": 0,        # selected todo
    "last_topic_index": 0,  # last topic
    "input_mode": False,    # input active
    "input_prompt": "",     # input prompt
    "input_buffer": "",     # input buffer
    "input_callback": None,  # input done callback
    "multi_step_data": {},  # multi-step state
    "todo_priority": 0,     # default priority
    "sort_mode": "priority"  # current sort
}

# status message shown briefly in the Info box
app_state["status_msg"] = ""
app_state["status_msg_until"] = 0
# Notes editor state (internal caret, selection, clipboard)
app_state["notes_cursor_offset"] = 0
app_state["notes_selection_anchor"] = None  # raw offset where selection started (None = no selection)
app_state["clipboard"] = ""
app_state["_cursor_last_blink"] = time.time()
app_state["_cursor_visible"] = True


def get_data_path():
    """Return the path to the .todo data file next to the script."""
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "todos.todo")


def save_data(path=None):
    """Serialize app_state topics/todos to a simple text .todo file.

    Format (TODO_V1):
    TODO_V1
    TOPIC:<topic_name>
    NUM_TODOS:<n>
    TODO_META:<name>\x1f<priority>\x1f<completed>\x1f<created_at>\x1f<deadline>\x1f<notes_b64>
    ...
    """
    if path is None:
        path = get_data_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("TODO_V1\n")
            for topic in app_state.get("topics", []):
                f.write(f"TOPIC:{topic}\n")
                todos = app_state.get("todos", {}).get(topic, [])
                f.write(f"NUM_TODOS:{len(todos)}\n")
                for t in todos:
                    notes = t.get("notes", "") or ""
                    notes_b64 = base64.b64encode(notes.encode("utf-8")).decode("ascii")
                    name = (t.get("name") or "").replace("\n", "\\n")
                    created = t.get("created_at", "")
                    deadline = t.get("deadline", "") or ""
                    completed = "1" if t.get("completed") else "0"
                    meta = "\x1f".join([name, str(t.get("priority", 3)), completed, created, deadline, notes_b64])
                    f.write("TODO_META:" + meta + "\n")
        # set status message
        app_state["status_msg"] = f"Saved {os.path.basename(path)}"
        app_state["status_msg_until"] = time.time() + 2
        return True
    except Exception as e:
        app_state["status_msg"] = f"Save failed: {e}"
        app_state["status_msg_until"] = time.time() + 3
        return False


def load_data(path=None):
    """Deserialize the .todo file into app_state.
    If file missing or invalid, do nothing.
    """
    if path is None:
        path = get_data_path()
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln.rstrip("\n") for ln in f]
        if not lines or lines[0] != "TODO_V1":
            return False
        idx = 1
        topics = []
        todos_map = {}
        while idx < len(lines):
            line = lines[idx]
            idx += 1
            if line.startswith("TOPIC:"):
                topic = line[len("TOPIC:"):]
                topics.append(topic)
                todos_map[topic] = []
                # expect NUM_TODOS next
                if idx < len(lines) and lines[idx].startswith("NUM_TODOS:"):
                    try:
                        n = int(lines[idx].split(":", 1)[1])
                    except Exception:
                        n = 0
                    idx += 1
                    for _ in range(n):
                        if idx >= len(lines):
                            break
                        meta_line = lines[idx]
                        idx += 1
                        if not meta_line.startswith("TODO_META:"):
                            continue
                        meta = meta_line[len("TODO_META:"):]
                        parts = meta.split("\x1f")
                        if len(parts) < 6:
                            continue
                        name = parts[0].replace("\\n", "\n")
                        priority = int(parts[1]) if parts[1].isdigit() else len(PRIORITIES) - 1
                        completed = parts[2] == "1"
                        created = parts[3]
                        deadline = parts[4] or None
                        notes_b64 = parts[5]
                        try:
                            notes = base64.b64decode(notes_b64.encode("ascii")).decode("utf-8")
                        except Exception:
                            notes = ""
                        todos_map[topic].append({
                            "name": name,
                            "priority": priority,
                            "completed": completed,
                            "created_at": created,
                            "deadline": deadline,
                            "notes": notes
                        })
        # apply to app_state
        app_state["topics"] = topics
        app_state["todos"] = todos_map
        # reset indexes safely
        app_state["topic_index"] = min(app_state.get("topic_index", 0), max(0, len(topics) - 1))
        return True
    except Exception as e:
        app_state["status_msg"] = f"Load failed: {e}"
        app_state["status_msg_until"] = time.time() + 3
        return False

def init_windows_terminal():
    """Initialize Windows terminal for ANSI escape sequences"""
    kernel32 = windll.kernel32
    handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    mode = c_ulong()
    kernel32.GetConsoleMode(handle, byref(mode))
    mode.value |= ENABLE_VIRTUAL_TERMINAL_PROCESSING
    mode.value |= ENABLE_PROCESSED_OUTPUT
    kernel32.SetConsoleMode(handle, mode)
    
    # Switch to alternate screen and disable scrolling/wrapping
    sys.stdout.write(ALT_SCREEN + DISABLE_LINEWRAP + DISABLE_SCROLL)
    sys.stdout.flush()

def clear_screen():
    """Clear the terminal screen"""
    sys.stdout.write(CLEAR_SCREEN + MOVE_TO_TOP)
    sys.stdout.flush()

def get_terminal_size():
    """Get terminal dimensions"""
    size = shutil.get_terminal_size()
    return (size.columns, size.lines)

def strip_ansi(text):
    """Remove ANSI escape codes from text"""
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def build_display_lines(raw, width):
    """Wrap raw notes text into display lines of max 'width'.

    Returns (lines, line_start_offsets) where line_start_offsets[i] is the
    raw-string offset of the first character of lines[i].
    """
    lines = []
    starts = []
    off = 0
    for paragraph in raw.split('\n'):
        i = 0
        while i < len(paragraph):
            lines.append(paragraph[i:i+width])
            starts.append(off + i)
            i += width
        # If paragraph was empty or exactly multiple of width, still add an empty line for the newline
        if len(paragraph) == 0:
            lines.append("")
            starts.append(off + len(paragraph))
        # Account for the newline character in raw offsets
        off += len(paragraph) + 1
    # If the raw text ended with a newline, we added a trailing empty line; good.
    return lines, starts


def offset_to_rowcol(raw, width, offset):
    """Map a raw-string offset to (row, col) in wrapped display coordinates."""
    if offset <= 0:
        return 0, 0
    row = 0
    col = 0
    cur = 0
    for paragraph in raw.split('\n'):
        plen = len(paragraph)
        i = 0
        while i < plen:
            line_len = min(width, plen - i)
            if cur + line_len >= offset:
                # offset is inside this wrapped line
                return row, offset - cur - i
            i += line_len
            row += 1
            cur += line_len
        # account for the newline
        if cur + 1 > offset:
            # offset points to the newline; place cursor at start of next row (empty line)
            return row + 1, 0
        cur += 1
        # new empty line starts after newline
        if plen == 0:
            # empty paragraph created a single empty row
            if cur >= offset:
                return row, 0
        #row += 0
    # If offset beyond end, place at end
    lines, starts = build_display_lines(raw, width)
    if not lines:
        return 0, 0
    last = lines[-1]
    return len(lines) - 1, len(last)


def rowcol_to_offset(raw, width, row, col):
    """Inverse of offset_to_rowcol: map display (row,col) to raw offset.

    If row/col beyond end, return len(raw).
    """
    if row < 0:
        return 0
    cur = 0
    r = 0
    for paragraph in raw.split('\n'):
        plen = len(paragraph)
        i = 0
        while i < plen:
            if r == row:
                return min(cur + i + col, cur + plen)
            i += min(width, plen - i)
            cur += min(width, plen - i + (0 if i >= plen else 0))
            r += 1
        # newline
        if r == row:
            return min(cur + plen, len(raw))
        cur += 1
        r += 0
    return len(raw)


def color_cell_write(canvas, row, col, text, color):
    """Write text into canvas per-character with a color wrapper.

    Avoid embedding raw ANSI sequences into canvas cells; instead wrap each
    visible character so alignment stays correct.
    """
    for k, ch in enumerate(text):
        if col + k >= len(canvas[0]):
            break
        canvas[row][col + k] = color + ch + NORMAL


def deadline_status(deadline_str):
    """Return status for a deadline string (DD-MM-YYYY) -> 'ok','today','past'.

    Non-parseable or empty deadlines return 'ok'.
    """
    if not deadline_str:
        return 'ok'
    try:
        d = datetime.strptime(deadline_str, "%d-%m-%Y").date()
    except Exception:
        return 'ok'
    today = date.today()
    if d < today:
        return 'past'
    if d == today:
        return 'today'
    return 'ok'


def get_todo_display_order(topic):
    """Return a list of indices for todos in `topic` sorted according to current sort mode.

    The returned list contains original indices into the underlying todos list.
    """
    todos = app_state.get("todos", {}).get(topic, [])
    indices = list(range(len(todos)))
    mode = app_state.get("sort_mode", "priority")

    def deadline_key(t):
        d = t.get("deadline")
        # treat None/empty as far future
        return d if d else "9999-12-31"

    if mode == "priority":
        # sort by priority index (lower = higher priority), then by earlier deadline
        indices.sort(key=lambda i: (todos[i].get("priority", len(PRIORITIES) - 1), deadline_key(todos[i])))
    elif mode == "deadline":
        # sort by deadline (earlier first), then by priority
        indices.sort(key=lambda i: (deadline_key(todos[i]), todos[i].get("priority", len(PRIORITIES) - 1)))
    else:  # created
        # sort by created_at string (lexicographic YYYY-MM-DD HH:MM:SS) -> older first
        indices.sort(key=lambda i: todos[i].get("created_at", ""))

    return indices

def draw_box(width, height, title="", is_selected=False, is_active=False):
    """Creates a box with optional title and border colors based on selection state"""
    color = ACTIVE_COLOR if is_active else (SELECTED_COLOR if is_selected else NORMAL)
    # Calculate title space (visible) and allow title coloring separately
    title_space = f" {title} " if title else ""
    title_visible_len = len(strip_ansi(title_space))
    remaining_width = width - title_visible_len - 2  # -2 for corners
    # Colorize title differently for active tab to give a tab-like look
    if title:
        if is_active:
            title_display = f"{TAB_BG}{TAB_FG}{title_space}{NORMAL}"
        elif is_selected:
            title_display = f"{INFO_LABEL_COLOR}{title_space}{NORMAL}"
        else:
            title_display = title_space
    else:
        title_display = title_space
    # Top border: left corner, title, then border color for the rest
    top = f"{color}┌{title_display}{color}{'─' * remaining_width}┐{NORMAL}"
    middle = f"{color}│{' ' * (width - 2)}│{NORMAL}"
    bottom = f"{color}└{'─' * (width - 2)}┘{NORMAL}"
    assert len(strip_ansi(top)) == width
    assert len(strip_ansi(middle)) == width
    assert len(strip_ansi(bottom)) == width
    box = [top]
    box.extend(middle for _ in range(height - 2))
    box.append(bottom)
    return box

def create_topic(name):
    """Adds a new topic and makes it the current selection"""
    app_state["topics"].append(name)
    app_state["topic_index"] = len(app_state["topics"]) - 1
    app_state["last_topic_index"] = app_state["topic_index"]
    # Switch to topics focus mode
    app_state["active_tab"] = "topics"
    app_state["nav_mode"] = False
    # Finish input mode after creating a single topic
    app_state["input_mode"] = False
    app_state["input_callback"] = None

def delete_topic(index):
    """Removes a topic and its todos, updates selection"""
    if 0 <= index < len(app_state["topics"]):
        topic = app_state["topics"].pop(index)
        if topic in app_state["todos"]:
            del app_state["todos"][topic]
        # fix topic_index bounds
        app_state["topic_index"] = min(index, max(0, len(app_state["topics"]) - 1))
        app_state["last_topic_index"] = app_state["topic_index"]

def create_todo(name):
    """Step 1: Start creating a new todo - asks for priority"""
    app_state["multi_step_data"]["name"] = name
    app_state["input_mode"] = True
    # Keep prompt compact (single line) to avoid extra newlines/flicker
    app_state["input_prompt"] = f"Priority? (1={PRIORITIES[0]},2={PRIORITIES[1]},3={PRIORITIES[2]},4={PRIORITIES[3]}): "
    app_state["input_callback"] = todo_priority_step

def todo_priority_step(priority_input):
    """Step 2: Save todo priority, then ask for deadline"""
    try:
        priority_index = int(priority_input) - 1
        if not (0 <= priority_index < len(PRIORITIES)):
            # invalid, default to 'None'
            priority_index = len(PRIORITIES) - 1
    except Exception:
        # On parse error default to 'None'
        priority_index = len(PRIORITIES) - 1

    # store the chosen priority and prompt for deadline (or skip)
    app_state["multi_step_data"]["priority"] = priority_index
    app_state["input_mode"] = True
    app_state["input_prompt"] = "Deadline? (DD-MM-YYYY) or press 's' to skip: "
    app_state["input_callback"] = todo_deadline_step


def todo_deadline_step(deadline_input):
    """Step 3: Save deadline (if given) and create the todo"""
    name = app_state["multi_step_data"].get("name", "")
    priority_index = app_state["multi_step_data"].get("priority", len(PRIORITIES) - 1)
    deadline = None

    if deadline_input and deadline_input.lower() == 's':
        deadline = None
    elif deadline_input:
        # Expect DD-MM-YYYY; validate roughly
        try:
            time.strptime(deadline_input.strip(), "%d-%m-%Y")
            deadline = deadline_input.strip()
        except Exception:
            # invalid format -> treat as no deadline
            deadline = None

    if name and app_state["topics"]:
        current_topic = app_state["topics"][app_state["topic_index"]]
        if current_topic not in app_state["todos"]:
            app_state["todos"][current_topic] = []
        # record creation time
        created = time.strftime("%d-%m-%Y %H:%M:%S", time.localtime())
        app_state["todos"][current_topic].append({
            "name": name,
            "priority": priority_index,
            "completed": False,
            "created_at": created,
            "deadline": deadline,
            "notes": ""
        })
        # select the newly added todo
        app_state["todo_index"] = len(app_state["todos"][current_topic]) - 1

    # finish input mode and remain in focus mode on todos
    app_state["multi_step_data"] = {}
    app_state["input_mode"] = False
    app_state["nav_mode"] = False
    app_state["active_tab"] = "todos"

def delete_todo(topic_index, todo_index):
    """Removes a todo and updates selection if needed"""
    if topic_index < len(app_state["topics"]):
        topic = app_state["topics"][topic_index]
        if topic in app_state["todos"] and todo_index < len(app_state["todos"][topic]):
            app_state["todos"][topic].pop(todo_index)
            # adjust todo_index
            app_state["todo_index"] = min(todo_index, max(0, len(app_state["todos"].get(topic, [])) - 1))

def toggle_todo(topic_index, todo_index):
    """Marks or unmarks a todo as completed"""
    if topic_index < len(app_state["topics"]):
        topic = app_state["topics"][topic_index]
        if topic in app_state["todos"] and todo_index < len(app_state["todos"][topic]):
            app_state["todos"][topic][todo_index]["completed"] = not app_state["todos"][topic][todo_index]["completed"]

def render_frame(terminal_width, terminal_height):
    """Draws all UI elements and calculates their positions"""
    # Reserve bottom line for help text/input
    usable_height = terminal_height - 1
    
    # Calculate panel dimensions
    side_width = min(max(20, terminal_width // 4), terminal_width // 3)  # 20-33% of width
    main_width = terminal_width - side_width
    
    # Increase info height so we can show Topic + Todo name + Status + Priority + Created
    info_height = 7
    side_panel_height = usable_height // 2
    files_panel_height = usable_height - side_panel_height
    main_panel_height = usable_height - info_height
    
    # Create canvas first
    canvas = [[" " for _ in range(terminal_width)] for _ in range(terminal_height)]
    
    def write_box_to_canvas(box, x, y):
        """Places a box on screen, handling color codes properly"""
        current_color = NORMAL
        for box_y, line in enumerate(box):
            if y + box_y >= terminal_height:
                break
                
            canvas_x = x
            chars = list(line)
            while chars and canvas_x < terminal_width:
                if chars[0] == '\033':  # ANSI escape sequence
                    code = []
                    while chars and chars[0] != 'm':
                        code.append(chars.pop(0))
                    if chars:
                        code.append(chars.pop(0))
                    current_color = ''.join(code)
                else:
                    if canvas_x < terminal_width:
                        canvas[y + box_y][canvas_x] = current_color + chars.pop(0) + NORMAL
                    canvas_x += 1
    
    # Create and position boxes
    # Track topic selection (always show selected topic)
    selected_topic_index = app_state.get("topic_index", 0)
    app_state["last_topic_index"] = app_state.get("topic_index", 0)

    # Create topics box
    topics_lines = []
    for i, topic in enumerate(app_state["topics"]):
        prefix = ">" if i == selected_topic_index else " "
        topics_lines.append(f"{prefix} {topic}")
    
    # Write topics content
    topics_box = draw_box(
        side_width, 
        side_panel_height, 
        "Topics",
        app_state["nav_mode"] and app_state["active_tab"] == "topics",
        not app_state["nav_mode"] and app_state["active_tab"] == "topics"
    )
    
    # Build todos content in display order according to sort mode
    todos_lines = []
    if app_state["topics"]:
        current_topic = app_state["topics"][app_state.get("topic_index", 0)]
        todos = app_state["todos"].get(current_topic, [])
        ordered_indices = get_todo_display_order(current_topic)
        selected_underlying = app_state.get("todo_index", 0)
        for disp_i, orig_i in enumerate(ordered_indices):
            todo = todos[orig_i]
            prefix = ">" if (orig_i == selected_underlying and app_state["active_tab"] == "todos") else " "
            checkbox = "☑" if todo.get("completed") else "☐"
            name = todo.get('name', '')
            line_text = f"{prefix} {checkbox} {name}"
            name_start = len(f"{prefix} {checkbox} ")
            # Get deadline info and status (today/past/ok)
            deadline = todo.get('deadline') or ""
            status = deadline_status(deadline)
            todos_lines.append((line_text, todo.get("priority"), name_start, orig_i, status, deadline))
    # Create todos box (content will be built in display order below)

    todos_box = draw_box(
        side_width, 
        files_panel_height, 
        "Todos",
        app_state["nav_mode"] and app_state["active_tab"] == "todos",
        not app_state["nav_mode"] and app_state["active_tab"] == "todos"
    )
    
    info_box = draw_box(
        main_width, 
        info_height, 
        "Info"
    )
    
    main_box = draw_box(
        main_width, 
        main_panel_height, 
        "Notes",
        app_state["nav_mode"] and app_state["active_tab"] == "notes",
        not app_state["nav_mode"] and app_state["active_tab"] == "notes"
    )
    
    # Draw the topics box first (top left)
    write_box_to_canvas(topics_box, 0, 0)
    
    # Show topics with scrolling if needed
    visible_topics = max(1, side_panel_height - 2)  # Account for box borders
    total_topics = len(topics_lines)
    if total_topics > 0:
        start_topic = max(0, min(selected_topic_index - visible_topics // 2, max(0, total_topics - visible_topics)))
    else:
        start_topic = 0

    for vis_i in range(visible_topics):
        idx = start_topic + vis_i
        if idx >= total_topics:
            break
        line = topics_lines[idx]
        # color selected topic differently
        is_sel = (idx == selected_topic_index)
        for j, ch in enumerate(line):
            if j >= side_width - 2:
                break
            if is_sel:
                canvas[1 + vis_i][1 + j] = SELECTED_COLOR + ch + NORMAL
            else:
                canvas[1 + vis_i][1 + j] = ch
    
    # Write todos content
    write_box_to_canvas(todos_box, 0, side_panel_height)
    # Render sort badge on the top border of the Todos box (right-aligned)
    if app_state.get("topics"):
        sort_mode = app_state.get("sort_mode", "priority").capitalize()
        badge = f"Sort: {sort_mode}"
        badge_row = side_panel_height  # top border line of the Todos box
        # compute starting column so badge is right-aligned inside the top border (avoid corners)
        badge_col = max(1, side_width - 1 - len(badge))
        for k, ch in enumerate(badge[: max(0, side_width - 2)]):
            if badge_col + k < side_width - 1:
                color = INFO_LABEL_COLOR if k < len("Sort:") else CREATED_COLOR
                canvas[badge_row][badge_col + k] = color + ch + NORMAL
    # Calculate how many todos we can show at once
    visible_todos = max(1, files_panel_height - 2)
    total_todos = len(todos_lines)
    # Find where the selected todo will appear in the sorted list
    selected_display_pos = 0
    if app_state.get("active_tab") == "todos":
        sel_under = app_state.get("todo_index", 0)
        for di, itm in enumerate(todos_lines):
            if isinstance(itm, tuple) and len(itm) >= 4 and itm[3] == sel_under:
                selected_display_pos = di
                break

    if total_todos > 0:
        start_todo = max(0, min(selected_display_pos - visible_todos // 2, max(0, total_todos - visible_todos)))
    else:
        start_todo = 0

    for vis_i in range(visible_todos):
        idx = start_todo + vis_i
        if idx >= total_todos:
            break
        item = todos_lines[idx]
        if isinstance(item, tuple) and len(item) >= 3:
            # tuple shape: (line_text, priority_index, name_start, orig_index, dstat, dstr)
            line = item[0]
            pidx = item[1]
            name_start = item[2]
            dstat = item[4] if len(item) > 4 else 'ok'
        else:
            line = item
            pidx = None
            name_start = -1
            dstat = 'ok'

        name_end = len(line)
        # Draw todo text with priority colors for the name part
        canvas_row = side_panel_height + 1 + vis_i
        for j, ch in enumerate(line):
            if j >= side_width - 2:
                break
            # Color the name part based on priority
            if pidx is not None and name_start <= j < name_end:
                color = PRIORITY_COLORS[pidx] if pidx is not None and 0 <= pidx < len(PRIORITY_COLORS) else NORMAL
                canvas[canvas_row][1 + j] = color + ch + NORMAL
            else:
                canvas[canvas_row][1 + j] = ch
                
        # Add warning symbols for urgent deadlines
        if pidx is not None and dstat in ('today', 'past'):
            sym = DEADLINE_TODAY if dstat == 'today' else DEADLINE_PAST
            sym_color = DEADLINE_COLOR if dstat == 'today' else STATUS_WARN
            sym_col = name_end
            if sym_col < side_width - 2:
                canvas[canvas_row][1 + sym_col] = sym_color + sym + NORMAL

    # Write info and main boxes
    write_box_to_canvas(info_box, side_width, 0)
    # Prepare info panel content
    info_lines = []
    info_deadline_stat = 'ok'
    info_deadline_str = ''
    
    # Get current topic info
    if app_state["topics"]:
        current_topic = app_state["topics"][app_state.get("topic_index", 0)]
        info_lines.append(f"Topic: {current_topic}")
        
        # Get selected todo details if available
        todos = app_state["todos"].get(current_topic, [])
        if todos and 0 <= app_state.get("todo_index", 0) < len(todos):
            todo = todos[app_state.get("todo_index", 0)]
            
            # Format todo information
            status = "Completed" if todo.get("completed") else "Not Completed"
            info_deadline_str = todo.get('deadline', '') or 'None'
            info_deadline_stat = deadline_status(todo.get('deadline', ''))
            
            info_lines.extend([
                f"Todo:  {todo.get('name')}",
                f"State: {status}",
                f"Prio:  {PRIORITIES[todo.get('priority',0)]} | Due: {info_deadline_str}",
                f"Date:  {todo.get('created_at','-')}"
            ])
        else:
            info_lines.append("No todo selected")
    else:
        info_lines.append("No topics")

    for i, line in enumerate(info_lines):
        if i >= info_height - 2:
            break

        # Split label and value on first ':' if present
        if ':' in line:
            label, val = line.split(':', 1)
            label = label.strip()
            val = val.lstrip()
        else:
            label = None
            val = line

        write_x = side_width + 1
        write_y = i + 1

        def write_label_text(text, color):
            # write visible text with color per-char to avoid embedding raw ANSI sequences
            for k, ch in enumerate(text):
                if k < main_width - 2:
                    canvas[write_y][write_x + k] = color + ch + NORMAL

        if label == "Topic":
            label_text = f"{label}: "
            write_label_text(label_text, INFO_LABEL_COLOR)
            offset = len(label_text)
            for j, ch in enumerate(val[: main_width - 2 - offset]):
                canvas[write_y][write_x + offset + j] = SELECTED_COLOR + ch + NORMAL

        elif label == "Todo":
            label_text = f"{label}: "
            write_label_text(label_text, INFO_LABEL_COLOR)
            offset = len(label_text)
            for j, ch in enumerate(val[: main_width - 2 - offset]):
                canvas[write_y][write_x + offset + j] = ch

        elif label == "State":
            label_text = f"{label}: "
            write_label_text(label_text, INFO_LABEL_COLOR)
            offset = len(label_text)
            color = STATUS_OK if val.strip().lower().startswith("completed") else STATUS_WARN
            for j, ch in enumerate(val[: main_width - 2 - offset]):
                canvas[write_y][write_x + offset + j] = color + ch + NORMAL

        elif label == "Prio":
            # val format: '<PRIORITY> | Due: <deadline>'
            parts = val.split('|', 1)
            prio = parts[0].strip()
            rest = parts[1].strip() if len(parts) > 1 else ""
            label_text = f"{label}: "
            write_label_text(label_text, INFO_LABEL_COLOR)
            offset = len(label_text)
            try:
                pidx = PRIORITIES.index(prio)
            except ValueError:
                pidx = None
            for j, ch in enumerate(prio):
                if offset + j < main_width - 2:
                    if pidx is not None:
                        canvas[write_y][write_x + offset + j] = PRIORITY_COLORS[pidx] + ch + NORMAL
                    else:
                        canvas[write_y][write_x + offset + j] = ch
            # color deadline part depending on urgency (use info_deadline_stat computed earlier)
            rest_str = (" | " + rest) if rest else ""
            rest_start = offset + len(prio)
            # choose deadline color based on status
            dl_color = DEADLINE_COLOR
            if 'info_deadline_stat' in locals() and info_deadline_stat == 'past':
                dl_color = STATUS_WARN
            elif 'info_deadline_stat' in locals() and info_deadline_stat == 'today':
                dl_color = DEADLINE_COLOR
            for j, ch in enumerate(rest_str[: max(0, main_width - 2 - rest_start)]):
                canvas[write_y][write_x + rest_start + j] = dl_color + ch + NORMAL
            # Add warning icon for urgent deadlines
            if info_deadline_stat in ('today', 'past'):
                sym = DEADLINE_TODAY if info_deadline_stat == 'today' else DEADLINE_PAST
                sym_color = DEADLINE_COLOR if info_deadline_stat == 'today' else STATUS_WARN
                sym_pos = rest_start + len(rest_str)
                if sym_pos < main_width - 2:
                    canvas[write_y][write_x + sym_pos] = sym_color + sym + NORMAL

        elif label == "Date":
            label_text = f"{label}: "
            write_label_text(label_text, INFO_LABEL_COLOR)
            offset = len(label_text)
            for j, ch in enumerate(val[: main_width - 2 - offset]):
                canvas[write_y][write_x + offset + j] = CREATED_COLOR + ch + NORMAL

        else:
            # Fallback: write the whole line plain
            for j, ch in enumerate(line[: main_width - 2]):
                canvas[write_y][write_x + j] = ch

    # show transient status message if present
    if app_state.get("status_msg") and time.time() < app_state.get("status_msg_until", 0):
        msg = app_state.get("status_msg")
        # place on the line after info lines if space allows
        si = min(len(info_lines), info_height - 2)
        for j, ch in enumerate(msg[: main_width - 2]):
            canvas[si + 1][side_width + 1 + j] = ch

    write_box_to_canvas(main_box, side_width, info_height)

    # Get and format todo notes with word wrap. We render an internal caret and selection
    notes_width = main_width - 2
    notes_height = main_panel_height - 2
    note_lines = []
    note_line_starts = []  # line start offsets
    raw_notes = ""
    # Get notes for selected todo
    if app_state["topics"]:
        topic = app_state["topics"][app_state.get("topic_index", 0)]
        todos = app_state["todos"].get(topic, [])
        if todos and 0 <= app_state.get("todo_index", 0) < len(todos):
            todo = todos[app_state.get("todo_index", 0)]
            raw_notes = todo.get("notes", "") or ""
            note_lines, note_line_starts = build_display_lines(raw_notes, notes_width)
    # Selection/cursor
    sel_anchor = app_state.get("notes_selection_anchor")
    cursor_off = app_state.get("notes_cursor_offset", 0)
    if sel_anchor is not None:
        sel_start = min(sel_anchor, cursor_off)
        sel_end = max(sel_anchor, cursor_off)
    else:
        sel_start = sel_end = None

    for i, line in enumerate(note_lines[:notes_height]):
        start_off = note_line_starts[i] if i < len(note_line_starts) else 0
        for j, ch in enumerate(line[:notes_width]):
            raw_off = start_off + j
            # Draw caret at cursor, highlight selection
            if raw_off == cursor_off and app_state.get("active_tab") == "notes" and not app_state.get("nav_mode", True) and app_state["topics"] and app_state.get("_cursor_visible", True):
                if sel_start is not None and sel_start <= cursor_off < sel_end:
                    canvas[info_height + 1 + i][side_width + 1 + j] = "\033[7m|" + NORMAL
                else:
                    canvas[info_height + 1 + i][side_width + 1 + j] = SELECTED_COLOR + "|" + NORMAL
            else:
                if sel_start is not None and sel_start <= raw_off < sel_end:
                    canvas[info_height + 1 + i][side_width + 1 + j] = "\033[7m" + ch + NORMAL
                else:
                    canvas[info_height + 1 + i][side_width + 1 + j] = ch
    # Draw caret at end
    if app_state.get("active_tab") == "notes" and not app_state.get("nav_mode", True) and app_state["topics"] and app_state.get("_cursor_visible", True):
        if cursor_off == len(raw_notes) and note_lines:
            last_row = min(len(note_lines)-1, notes_height-1)
            last_col = len(note_lines[last_row]) if last_row < len(note_lines) else 0
            if last_col < notes_width:
                canvas[info_height + 1 + last_row][side_width + 1 + last_col] = SELECTED_COLOR + "|" + NORMAL
    # Blink caret
    now = time.time()
    if now - app_state.get("_cursor_last_blink", 0) >= 0.5:
        app_state["_cursor_last_blink"] = now
        app_state["_cursor_visible"] = not app_state.get("_cursor_visible", True)

    # Add help text or input prompt at bottom
    if app_state["input_mode"]:
        prompt_text = f"{app_state['input_prompt']}{app_state['input_buffer']}_"
        for i, char in enumerate(prompt_text):
            if i < terminal_width:
                canvas[-1][i] = char
    else:
        if app_state["input_mode"]:
            help_text = f"INPUT: {app_state.get('input_prompt','')}"
        elif app_state["nav_mode"]:
            help_text = "NAV MODE | Enter: focus tab, j/k: switch tabs, n: new, S: save, Q: quit"
        elif app_state["active_tab"] == "topics":
            help_text = "TOPICS | j/k: select, n: new topic, d: delete, Enter: todos, Esc: nav, S: save, Q: quit"
        elif app_state["active_tab"] == "todos":
            help_text = "TODOS | j/k: select, n: new todo, d: delete, s: cycle sort, Enter: open notes, Space: toggle, Esc: nav, S: save, Q: quit"
        elif app_state["active_tab"] == "notes":
            help_text = "NOTES | type: edit, Enter: newline, Backspace: delete, Esc: close notes, S: save, Q: quit"
        # Show key bindings at the bottom of the screen
        if len(help_text) < terminal_width:
            for i, ch in enumerate(help_text):
                canvas[-1][i] = HELP_COLOR + ch + NORMAL
    
    # Always render the frame
    frame = "\n".join("".join(line) for line in canvas)
    sys.stdout.write(MOVE_TO_TOP)
    sys.stdout.write(frame)
    sys.stdout.flush()

def handle_input():
    """Handle keyboard input"""
    if msvcrt.kbhit():
        key = msvcrt.getch()

        # Handle input mode
        if app_state["input_mode"]:
            if key == b'\r':  # Enter
                # capture buffer and callback, then clear buffer for the next input
                buffer = app_state.get("input_buffer", "")
                cb = app_state.get("input_callback")
                app_state["input_buffer"] = ""
                # Assume input completes; allow callback to re-enable input_mode for multi-step flows
                app_state["input_mode"] = False
                # call the callback (it may set input_mode and a new input_callback for next step)
                if cb:
                    try:
                        cb(buffer)
                    except Exception:
                        # swallow to avoid breaking UI loop; real app could log
                        pass
                # if callback didn't re-enable input_mode, clear callback to avoid stale handlers
                if not app_state.get("input_mode", False):
                    app_state["input_callback"] = None
                return True
            elif key == b'\x1b':  # Escape
                app_state["input_mode"] = False
                app_state["input_buffer"] = ""
                app_state["input_callback"] = None
                return True
            elif key == b'\x08':  # Backspace
                app_state["input_buffer"] = app_state["input_buffer"][:-1]
                return True
            
            try:
                char = key.decode('utf-8')
                app_state["input_buffer"] += char
            except:
                pass
            return True
            
        # Handle special keys (arrow keys)
        if key == b'\xe0':
            key = msvcrt.getch()
            if app_state["nav_mode"]:
                if key in (b'H', b'P'):  # Up/Down arrows
                    if app_state["active_tab"] == "topics":
                        app_state["active_tab"] = "todos"
                        app_state["todo_index"] = 0
                    elif app_state["active_tab"] == "todos":
                        app_state["active_tab"] = "topics"
                        app_state["topic_index"] = 0
            elif not app_state["nav_mode"]:
                if app_state["active_tab"] == "topics":
                    if key == b'H':  # Up arrow
                        app_state["topic_index"] = max(0, app_state["topic_index"] - 1)
                    elif key == b'P':  # Down arrow
                        app_state["topic_index"] = min(len(app_state["topics"]) - 1, app_state["topic_index"] + 1)
                    app_state["last_topic_index"] = app_state["topic_index"]
                elif app_state["active_tab"] == "todos" and app_state["topics"]:
                    current_topic = app_state["topics"][app_state["topic_index"]]
                    todos = app_state["todos"].get(current_topic, [])
                    if todos:
                        ordered = get_todo_display_order(current_topic)
                        try:
                            pos = ordered.index(app_state.get("todo_index", 0))
                        except ValueError:
                            pos = 0
                        if key == b'H':  # Up arrow
                            newpos = max(0, pos - 1)
                        elif key == b'P':  # Down arrow
                            newpos = min(len(ordered) - 1, pos + 1)
                        else:
                            newpos = pos
                        app_state["todo_index"] = ordered[newpos]
                elif app_state["active_tab"] == "notes":
                    # Move caret within notes: left/right by char, up/down by wrapped row using terminal width
                    current_topic = app_state["topics"][app_state["topic_index"]]
                    todos = app_state["todos"].get(current_topic, [])
                    if todos and 0 <= app_state.get("todo_index", 0) < len(todos):
                        todo = todos[app_state["todo_index"]]
                        raw = todo.get("notes", "") or ""
                        # approximate notes width using terminal layout
                        tw, th = get_terminal_size()
                        side_w = min(max(MIN_SIDE_WIDTH, int(tw * 0.2)), int(tw * MAX_SIDE_WIDTH_PERCENT / 100))
                        notes_w = max(10, tw - side_w - 4)
                        cur = app_state.get("notes_cursor_offset", len(raw))
                        # Up/Down/Left/Right
                        if key == b'H':  # Up
                            r, c = offset_to_rowcol(raw, notes_w, cur)
                            nr = max(0, r - 1)
                            app_state["notes_cursor_offset"] = rowcol_to_offset(raw, notes_w, nr, c)
                        elif key == b'P':  # Down
                            r, c = offset_to_rowcol(raw, notes_w, cur)
                            nr = r + 1
                            app_state["notes_cursor_offset"] = rowcol_to_offset(raw, notes_w, nr, c)
                        elif key == b'K':  # Left
                            app_state["notes_cursor_offset"] = max(0, cur - 1)
                        elif key == b'M':  # Right
                            app_state["notes_cursor_offset"] = min(len(raw), cur + 1)
            return True
            
        key = key.decode('utf-8', errors='ignore')

        # NOTES editing mode: when focused on notes, typing and keys modify the selected todo's notes
        if not app_state.get("nav_mode", True) and app_state.get("active_tab") == "notes":
            if not app_state["topics"]:
                return True
            current_topic = app_state["topics"][app_state.get("topic_index", 0)]
            todos = app_state["todos"].get(current_topic, [])
            if not todos or not (0 <= app_state.get("todo_index", 0) < len(todos)):
                return True
            todo = todos[app_state.get("todo_index", 0)]
            raw = todo.get("notes", "") or ""
            cur = app_state.get("notes_cursor_offset", len(raw))

            # Escape: close notes view
            if key == '\x1b':
                app_state["active_tab"] = "todos"
                app_state["nav_mode"] = False
                app_state["notes_selection_anchor"] = None
                return True

            # Ctrl-C: copy selection (or whole notes if no selection)
            if key == '\x03':
                anchor = app_state.get("notes_selection_anchor")
                if anchor is None:
                    app_state["clipboard"] = raw
                    app_state["status_msg"] = "Copied all notes"
                else:
                    a = min(anchor, cur)
                    b = max(anchor, cur)
                    app_state["clipboard"] = raw[a:b]
                    app_state["status_msg"] = "Copied selection"
                app_state["status_msg_until"] = time.time() + 2
                return True

            # Ctrl-X: cut selection
            if key == '\x18':
                anchor = app_state.get("notes_selection_anchor")
                if anchor is not None:
                    a = min(anchor, cur)
                    b = max(anchor, cur)
                    app_state["clipboard"] = raw[a:b]
                    todo["notes"] = raw[:a] + raw[b:]
                    app_state["notes_selection_anchor"] = None
                    app_state["notes_cursor_offset"] = a
                    app_state["status_msg"] = "Cut selection"
                    app_state["status_msg_until"] = time.time() + 2
                return True

            # Ctrl-V: paste
            if key == '\x16':
                clip = app_state.get("clipboard", "")
                if clip:
                    todo["notes"] = raw[:cur] + clip + raw[cur:]
                    app_state["notes_cursor_offset"] = cur + len(clip)
                return True

            # Enter -> insert newline at cursor
            if key == '\r':
                todo["notes"] = raw[:cur] + "\n" + raw[cur:]
                app_state["notes_cursor_offset"] = cur + 1
                return True

            # Backspace -> delete before cursor or delete selection
            if key in ('\x08', '\x7f'):
                anchor = app_state.get("notes_selection_anchor")
                if anchor is not None:
                    a = min(anchor, cur)
                    b = max(anchor, cur)
                    todo["notes"] = raw[:a] + raw[b:]
                    app_state["notes_cursor_offset"] = a
                    app_state["notes_selection_anchor"] = None
                else:
                    if cur > 0:
                        todo["notes"] = raw[:cur-1] + raw[cur:]
                        app_state["notes_cursor_offset"] = cur - 1
                return True

            # Toggle selection anchor with 'v' (visual select start/stop)
            if key == 'v':
                if app_state.get("notes_selection_anchor") is None:
                    app_state["notes_selection_anchor"] = cur
                else:
                    app_state["notes_selection_anchor"] = None
                return True

            # Insert printable characters at cursor
            if len(key) == 1 and (32 <= ord(key) <= 126 or ord(key) >= 128):
                todo["notes"] = raw[:cur] + key + raw[cur:]
                app_state["notes_cursor_offset"] = cur + 1
                # If there was a selection, clear it
                app_state["notes_selection_anchor"] = None
                return True

            return True

        # Manual save with uppercase S
        if key == 'S':
            save_data()
            return True

        # Cycle sort modes with lowercase s when in todos focus
        if key == 's' and not app_state.get("nav_mode", True) and app_state.get("active_tab") == "todos" and app_state.get("topics"):
            try:
                cur = SORT_MODES.index(app_state.get("sort_mode", "priority"))
            except ValueError:
                cur = 0
            nxt = SORT_MODES[(cur + 1) % len(SORT_MODES)]
            app_state["sort_mode"] = nxt
            # Don't set status_msg to avoid duplicate text with the Info area; the Todos badge shows it now
            return True

        if key == '\r':  # Enter key
            if app_state["nav_mode"]:
                app_state["nav_mode"] = False
            elif not app_state["nav_mode"] and app_state["active_tab"] == "topics":
                app_state["active_tab"] = "todos"
            elif not app_state["nav_mode"] and app_state["active_tab"] == "todos":
                if not app_state.get("topics"):
                    return True
                current_topic = app_state["topics"][app_state.get("topic_index", 0)]
                todos = app_state["todos"].get(current_topic, [])
                if not todos:
                    app_state["status_msg"] = "No todos in topic"
                    app_state["status_msg_until"] = time.time() + 2
                    return True
                todo = todos[app_state.get("todo_index", 0)]
                notes = todo.get("notes", "") or ""
                app_state["notes_cursor_offset"] = len(notes)
                app_state["active_tab"] = "notes"
                app_state["nav_mode"] = False
                return True
            elif key == 'S':
                save_data()
                return True

        elif key == '\x1b':  # Escape key
            app_state["nav_mode"] = True
            
        elif key == 'q':  # Quit
            return False
            
        elif key == 'n':  # New item (topic or todo) in both nav and focus modes
            # In nav mode or focus mode, create based on active tab
            if app_state["active_tab"] == "topics":
                app_state["input_mode"] = True
                app_state["input_prompt"] = "Enter new topic name: "
                app_state["input_callback"] = create_topic
            elif app_state["active_tab"] == "todos" and app_state["topics"]:
                app_state["input_mode"] = True
                app_state["input_prompt"] = "Enter todo name: "
                app_state["input_callback"] = create_todo
            
        elif key == 'd':  # Delete item based on active tab
            
            if app_state["active_tab"] == "topics" and app_state["topics"]:
                if app_state["topic_index"] < len(app_state["topics"]):
                    app_state["input_mode"] = True
                    app_state["input_prompt"] = f"Delete topic '{app_state['topics'][app_state['topic_index']]}' (y/n)? "
                    app_state["input_callback"] = lambda x: delete_topic(app_state["topic_index"]) if x.lower() == 'y' else None
            elif app_state["active_tab"] == "todos" and app_state["topics"]:
                current_topic = app_state["topics"][app_state["topic_index"]]
                if current_topic in app_state["todos"] and app_state["todos"][current_topic]:
                    todo_index = app_state["todo_index"]
                    if todo_index < len(app_state["todos"][current_topic]):
                        app_state["input_mode"] = True
                        app_state["input_prompt"] = f"Delete todo '{app_state['todos'][current_topic][todo_index]['name']}' (y/n)? "
                        app_state["input_callback"] = lambda x: delete_todo(app_state["topic_index"], todo_index) if x.lower() == 'y' else None
            
        # Space to toggle todo completion
        elif key == ' ' and app_state["active_tab"] == "todos" and app_state["topics"]:
            current_topic = app_state["topics"][app_state["topic_index"]]
            if current_topic in app_state["todos"] and app_state["todos"][current_topic]:
                todo_index = app_state["todo_index"]
                if todo_index < len(app_state["todos"][current_topic]):
                    toggle_todo(app_state["topic_index"], todo_index)
            
        # Vim-style navigation in focus mode
        elif not app_state["nav_mode"]:
            if app_state["active_tab"] == "topics":
                if key == 'k':  # Up
                    app_state["topic_index"] = max(0, app_state["topic_index"] - 1)
                    app_state["last_topic_index"] = app_state["topic_index"]
                elif key == 'j':  # Down
                    app_state["topic_index"] = min(len(app_state["topics"]) - 1, app_state["topic_index"] + 1)
                    app_state["last_topic_index"] = app_state["topic_index"]
            elif app_state["active_tab"] == "todos":
                if key in ('j', 'k') and app_state["topics"]:
                    current_topic = app_state["topics"][app_state["topic_index"]]
                    todos = app_state["todos"].get(current_topic, [])
                    if todos:
                        ordered = get_todo_display_order(current_topic)
                        try:
                            pos = ordered.index(app_state.get("todo_index", 0))
                        except ValueError:
                            pos = 0
                        if key == 'k':  # Up
                            newpos = max(0, pos - 1)
                        elif key == 'j':  # Down
                            newpos = min(len(ordered) - 1, pos + 1)
                        else:
                            newpos = pos
                        app_state["todo_index"] = ordered[newpos]
                        
        # Navigation mode j/k to switch between Topics and Todos
        elif app_state["nav_mode"]:
            if key in ('j', 'k'):
                if app_state["active_tab"] == "topics":
                    app_state["active_tab"] = "todos"
                elif app_state["active_tab"] == "todos":
                    app_state["active_tab"] = "topics"
            
    return True

def main():
    # Initialize terminal
    init_windows_terminal()
    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.flush()
    try:
        # Load saved data if available
        try:
            load_data()
        except Exception:
            pass
        
        # Main loop
        running = True
        while running:
            # Get current terminal size
            width, height = get_terminal_size()
            
            # Render frame
            render_frame(width, height)
            
            # Handle input
            running = handle_input()
            
            # Control frame rate
            time.sleep(0.033)  # ~30 FPS
            
    finally:
        # Auto-save on exit
        try:
            save_data()
        except Exception:
            pass
        # Restore normal screen (don't change the terminal cursor)
        sys.stdout.write(SHOW_CURSOR + NORMAL_SCREEN)
        sys.stdout.flush()

if __name__ == "__main__":
    main()