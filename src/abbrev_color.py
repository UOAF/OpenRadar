"""_future features_
    DFIDUI the missions from the Role-Colors file
        If you start typing, for example ESC then it tries to autofill ESCORT
        Tab out and it's good
    Add a button to set default Mission Colors to all in table
    Add a button to set 2L Abbrev or 3L Abbrevs (lookup in Callsign-Abbrevs.txt from Flight Name)
    Add functionality to the Apply Button to go through the list,
        And apply all abbreviations to display_name as well as all colors to symbols
    If I put in a Flight like Falcon1 then apply abbreviation and color to all 
        i.e. Falcon11, Falcon12, Falcon13, Falcon14
    Add a button to go read this week's UOAF signup sheet and populate the list from it (ha)
    If connected to server, let's put a button to search for human players and list them in the list   
    OK Fine, add a button to remove lines from the list rows...  maybe an x by each line???
"""

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple

from imgui_bundle import imgui


@dataclass
class AbbrevColorEntry:
    full_cs: str = ""
    abbrev: str = ""
    msn: str = ""
    color: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0, 1.0])


class AbbrevColorWindow:

    def __init__(self, rows: int = 4, gamestate=None):
        self.rows = rows
        self.gamestate = gamestate
        self.entries: List[AbbrevColorEntry] = [AbbrevColorEntry() for _ in range(rows)]
        self.open: bool = False
        self.color_picker_row: Optional[int] = None
        self.last_color: List[float] = [1.0, 1.0, 1.0, 1.0]
        self.mission_colors: Dict[str, Tuple[float, float, float]] = self._load_mission_colors()
        self.mission_list: List[str] = sorted(self.mission_colors.keys())
        self.callsign_abbrevs: Dict[str, Tuple[str, str]] = self._load_callsign_abbrevs()
        self.use_three_letter: bool = True
        self.msn_combo_row: Optional[int] = None
        self.msn_search: str = ""
        self.msn_highlight: int = -1
        self.msn_scroll_pending: bool = False
        self._color_col_x: Optional[float] = None
        self._abbrev_col_x: Optional[float] = None
        self.uoaf_window_open: bool = False
        self.uoaf_url: str = ""
        self.uoaf_status: str = ""
        self.uoaf_status_ok: bool = False

    def _add_rows(self, count: int):
        for _ in range(count):
            self.entries.append(AbbrevColorEntry())
        self.rows = len(self.entries)

    def _remove_row(self, row_index: int):
        if 0 <= row_index < len(self.entries):
            self.entries.pop(row_index)
            self.rows = len(self.entries)
            if self.color_picker_row is not None:
                if self.color_picker_row == row_index:
                    self.color_picker_row = None
                elif self.color_picker_row > row_index:
                    self.color_picker_row -= 1

    def _get_table_height(self) -> float:
        if hasattr(imgui, 'get_text_line_height_with_spacing'):
            line_height = imgui.get_text_line_height_with_spacing()
        elif hasattr(imgui, 'get_text_line_height'):
            line_height = imgui.get_text_line_height()
        else:
            line_height = 18.0

        visible_rows = min(len(self.entries), 16)
        header_height = line_height * 1.5
        row_height = line_height + 8.0
        calculated_height = visible_rows * row_height + header_height
        max_height = imgui.get_io().display_size.y * 0.75
        return min(calculated_height, max_height)

    def _load_mission_colors(self) -> Dict[str, Tuple[float, float, float]]:
        root = Path(__file__).resolve().parent.parent
        role_colors_path = root / "Data" / "Role-Colors.txt"
        mission_colors: Dict[str, Tuple[float, float, float]] = {}

        try:
            with role_colors_path.open("r", encoding="utf-8") as role_file:
                for line in role_file:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    parts = stripped.split("|")
                    if len(parts) < 2:
                        continue
                    names_part = parts[0].strip()
                    rgb_part = parts[1].strip()
                    rgb_values = [int(x) for x in rgb_part.split(",") if x.strip().isdigit()]
                    if len(rgb_values) != 3:
                        continue
                    normalized = tuple(v / 255.0 for v in rgb_values)
                    for name in names_part.split(","):
                        mission_name = name.strip().upper()
                        if mission_name:
                            mission_colors[mission_name] = normalized
        except FileNotFoundError:
            pass
        except Exception:
            pass

        return mission_colors

    def _load_callsign_abbrevs(self) -> Dict[str, Tuple[str, str]]:
        """Load FullName|2L|3L rows from Callsign-Abbrevs.txt."""
        root = Path(__file__).resolve().parent.parent
        abbrevs_path = root / "Data" / "Callsign-Abbrevs.txt"
        abbrevs: Dict[str, Tuple[str, str]] = {}

        try:
            with abbrevs_path.open("r", encoding="utf-8") as abbrev_file:
                for line in abbrev_file:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    parts = [p.strip() for p in stripped.split("|")]
                    if len(parts) < 3 or not parts[0]:
                        continue
                    abbrevs[parts[0].upper()] = (parts[1], parts[2])
        except FileNotFoundError:
            pass
        except Exception:
            pass

        return abbrevs

    def _abbrev_for_callsign(self, callsign: str, use_three_letter: bool) -> Optional[str]:
        """Abbreviate a callsign via the lookup table, keeping any numeric suffix."""
        match = re.match(r"([A-Za-z]+)(.*)", callsign.strip())
        if match is None:
            return None
        abbrev_pair = self.callsign_abbrevs.get(match.group(1).upper())
        if abbrev_pair is None:
            return None
        abbrev = abbrev_pair[1] if use_three_letter else abbrev_pair[0]
        return abbrev + match.group(2).strip()

    def _apply_abbrevs(self, use_three_letter: bool):
        """Fill every row's Abbrev from its callsign; remembers the AB/ABR choice."""
        self.use_three_letter = use_three_letter
        for entry in self.entries:
            abbrev = self._abbrev_for_callsign(entry.full_cs, use_three_letter)
            if abbrev is not None:
                entry.abbrev = abbrev

    def _clear_fields(self):
        self.entries = [AbbrevColorEntry() for _ in self.entries]

    # Security limits for the UOAF sheet loader
    _MAX_URL_LENGTH = 2048
    _MAX_SHEET_BYTES = 2 * 1024 * 1024
    _SHEET_ID_RE = re.compile(r"^([A-Za-z0-9_-]{10,120})$")
    _CALLSIGN_RE = re.compile(r"^[A-Za-z]+[A-Za-z0-9-]*$")

    @classmethod
    def _sheet_csv_url(cls, url: str) -> str:
        """Validate a pasted Google Sheets URL and rebuild its CSV export URL
        from the extracted document id only (nothing user-supplied is passed
        through). Raises ValueError with a user-facing message on any problem."""
        import urllib.parse

        # Drop control/non-printable characters before doing anything else
        url = "".join(ch for ch in url.strip() if ch.isprintable())
        if not url:
            raise ValueError("Paste a URL first")
        if len(url) > cls._MAX_URL_LENGTH:
            raise ValueError("That URL is too long to be a Sheets link")

        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https":
            raise ValueError("Only https:// links are accepted")
        if parsed.hostname != "docs.google.com":
            raise ValueError("Only docs.google.com spreadsheet links are accepted")

        gid_match = re.search(r"[#?&]gid=(\d+)", url)
        gid = gid_match.group(1) if gid_match else None
        if gid is not None and len(gid) > 12:
            gid = None  # not a real sheet tab id; ignore it

        # Published-to-web links (/spreadsheets/d/e/<id>/...)
        match = re.match(r"^/spreadsheets/d/e/([^/]+)", parsed.path)
        if match and cls._SHEET_ID_RE.match(match.group(1)):
            base = f"https://docs.google.com/spreadsheets/d/e/{match.group(1)}/pub?output=csv"
            return base + (f"&gid={gid}" if gid else "")
        # Regular share links (/spreadsheets/d/<id>/...)
        match = re.match(r"^/spreadsheets/d/([^/]+)", parsed.path)
        if match and cls._SHEET_ID_RE.match(match.group(1)):
            base = f"https://docs.google.com/spreadsheets/d/{match.group(1)}/export?format=csv"
            return base + (f"&gid={gid}" if gid else "")

        raise ValueError("That link is not a Google Sheets document")

    @classmethod
    def _fetch_csv_grid(cls, csv_url: str) -> List[List[str]]:
        """Fetch the CSV export. Only follows redirects within Google's domains,
        requires a CSV response, and caps the download size."""
        import csv
        import io
        import urllib.parse
        import urllib.request

        class _SafeRedirects(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                target = urllib.parse.urlparse(newurl)
                host = target.hostname or ""
                trusted = (host == "docs.google.com"
                           or host.endswith(".google.com")
                           or host.endswith(".googleusercontent.com"))
                if target.scheme != "https" or not trusted:
                    raise ValueError("Blocked a redirect to an untrusted address")
                return super().redirect_request(req, fp, code, msg, headers, newurl)

        opener = urllib.request.build_opener(_SafeRedirects)
        request = urllib.request.Request(csv_url, headers={"User-Agent": "OpenRadar"})
        with opener.open(request, timeout=10) as response:
            content_type = response.headers.get_content_type()
            if content_type not in ("text/csv", "text/plain"):
                raise ValueError(
                    "Link did not return a spreadsheet (is it shared with 'Anyone with the link'?)")
            data = response.read(cls._MAX_SHEET_BYTES + 1)
            if len(data) > cls._MAX_SHEET_BYTES:
                raise ValueError("That file is too large to be a signup sheet")

        text = data.decode("utf-8-sig", errors="replace")
        return list(csv.reader(io.StringIO(text)))

    def _parse_uoaf_grid(self, grid: List[List[str]]) -> List[Tuple[str, str]]:
        """Parse K5:O30 of a UOAF signup sheet.

        Three bands of five flights. Band rows (1-based): 5, 14, 23 (rows 13/22
        are package headers). Within a band each column is one flight:
        role / airframe / seat count / callsign / four seat rows.
        Flights are ignored when the callsign is blank or all four seats are
        blank or 'x'."""
        def cell(r0: int, c0: int) -> str:
            row = grid[r0] if r0 < len(grid) else []
            return row[c0].strip() if c0 < len(row) else ""

        flights: List[Tuple[str, str]] = []
        for band_top in (4, 13, 22):  # 0-based rows 5, 14, 23
            for col in range(10, 15):  # columns K..O
                role = cell(band_top, col)
                callsign = cell(band_top + 3, col)
                seats = [cell(band_top + 4 + i, col) for i in range(4)]
                # Sanitize: callsigns must look like callsigns, roles are
                # reduced to safe characters, both length-capped
                callsign = re.sub(r"\s+", "", callsign)[:24]
                if not self._CALLSIGN_RE.match(callsign):
                    continue
                occupied = [s for s in seats if s and s.lower() not in ("x", "xx", "-")]
                if not occupied:
                    continue
                role = re.sub(r"[^A-Z0-9 /()\-]", "", role.upper()).strip()[:24]
                if role == "NONE":
                    role = ""
                flights.append((callsign, role))
        return flights

    def _load_uoaf(self):
        try:
            csv_url = self._sheet_csv_url(self.uoaf_url)
            grid = self._fetch_csv_grid(csv_url)
            flights = self._parse_uoaf_grid(grid)
        except ValueError as exc:
            # Validation / safety rejections with user-facing messages
            self.uoaf_status = str(exc)
            self.uoaf_status_ok = False
            return
        except Exception as exc:
            # Network / HTTP / parsing failures
            self.uoaf_status = f"Couldn't load the sheet ({exc})"
            self.uoaf_status_ok = False
            return
        if not flights:
            self.uoaf_status = "No occupied flights in K5:O30 - is this the right sheet/tab?"
            self.uoaf_status_ok = False
            return
        self.entries = [AbbrevColorEntry(full_cs=callsign, msn=role)
                        for callsign, role in flights]
        self.rows = len(self.entries)
        self.uoaf_status = f"Loaded {len(flights)} flights"
        self.uoaf_status_ok = True

    def _render_uoaf_window(self):
        if not self.uoaf_window_open:
            return

        imgui.set_next_window_size(imgui.ImVec2(560, 0), imgui.Cond_.first_use_ever.value)
        result = imgui.begin("UOAF Signup", self.uoaf_window_open)
        if isinstance(result, tuple):
            expanded, open_state = result
        else:
            expanded = result
            open_state = True

        if not open_state:
            self.uoaf_window_open = False
            imgui.end()
            return

        if expanded:
            imgui.set_next_item_width(-70)
            _, self.uoaf_url = imgui.input_text("##uoaf_url", self.uoaf_url)
            imgui.same_line()
            if imgui.button("LOAD", imgui.ImVec2(60, 0)):
                self._load_uoaf()
            # Status line: green for success, red for problems.
            # Always rendered (blank when empty) so the window height is
            # constant and the message never requires resizing to see.
            if self.uoaf_status:
                if self.uoaf_status_ok:
                    color = imgui.ImVec4(0.5, 1.0, 0.5, 1.0)
                else:
                    color = imgui.ImVec4(1.0, 0.45, 0.45, 1.0)
                imgui.text_colored(color, self.uoaf_status)
            else:
                imgui.text(" ")

        imgui.end()

    def _select_mission(self, entry: AbbrevColorEntry, index: int):
        if 0 <= index < len(self.mission_list):
            entry.msn = self.mission_list[index]
        self.msn_search = ""
        self.msn_combo_row = None
        imgui.close_current_popup()

    def _msn_type_char(self, ch: str):
        if not self.mission_list:
            return
        candidate = self.msn_search + ch
        matches = [i for i, m in enumerate(self.mission_list) if m.startswith(candidate)]
        if matches:
            # Extend the search prefix and snap to its first match
            self.msn_search = candidate
            self.msn_highlight = matches[0]
            self.msn_scroll_pending = True
        elif self.msn_search and set(self.msn_search) == {ch}:
            # Same letter pressed again: cycle through items starting with it
            starts = [i for i, m in enumerate(self.mission_list) if m.startswith(ch)]
            if starts:
                if self.msn_highlight in starts:
                    next_pos = (starts.index(self.msn_highlight) + 1) % len(starts)
                    self.msn_highlight = starts[next_pos]
                else:
                    self.msn_highlight = starts[0]
                self.msn_scroll_pending = True

    def _handle_msn_keys(self, entry: AbbrevColorEntry) -> bool:
        """Handle typing inside the open mission combo. Returns True if a selection was made."""
        if imgui.is_key_pressed(imgui.Key.enter) or imgui.is_key_pressed(imgui.Key.keypad_enter):
            if 0 <= self.msn_highlight < len(self.mission_list):
                self._select_mission(entry, self.msn_highlight)
                return True

        if imgui.is_key_pressed(imgui.Key.delete):
            # Blank out the mission and close the dropdown
            entry.msn = ""
            self.msn_search = ""
            self.msn_combo_row = None
            imgui.close_current_popup()
            return True

        if imgui.is_key_pressed(imgui.Key.backspace) and self.msn_search:
            self.msn_search = self.msn_search[:-1]
            if self.msn_search:
                for i, m in enumerate(self.mission_list):
                    if m.startswith(self.msn_search):
                        self.msn_highlight = i
                        self.msn_scroll_pending = True
                        break

        if imgui.is_key_pressed(imgui.Key.down_arrow) and self.mission_list:
            if self.msn_highlight < 0:
                self.msn_highlight = 0
            else:
                self.msn_highlight = min(self.msn_highlight + 1, len(self.mission_list) - 1)
            self.msn_search = ""
            self.msn_scroll_pending = True

        if imgui.is_key_pressed(imgui.Key.up_arrow) and self.mission_list:
            self.msn_highlight = max(self.msn_highlight - 1, 0)
            self.msn_search = ""
            self.msn_scroll_pending = True

        for key_val in range(imgui.Key.a.value, imgui.Key.z.value + 1):
            if imgui.is_key_pressed(imgui.Key(key_val)):
                self._msn_type_char(chr(ord('A') + key_val - imgui.Key.a.value))
        if imgui.is_key_pressed(imgui.Key.space):
            self._msn_type_char(' ')

        return False

    def _step_mission(self, current_msn: str, step: int) -> str:
        """Return the next/previous mission relative to the current value."""
        if not self.mission_list:
            return current_msn
        current = current_msn.strip().upper()
        if current in self.mission_list:
            index = self.mission_list.index(current) + step
            index = max(0, min(index, len(self.mission_list) - 1))
        else:
            index = 0 if step > 0 else len(self.mission_list) - 1
        return self.mission_list[index]

    def _open_msn_combo(self, row_index: int, entry: AbbrevColorEntry):
        """Programmatically open the row's mission dropdown (call right after the combo item)."""
        popup_id = imgui.internal.im_hash_str("##ComboPopup", 0, imgui.get_item_id())
        imgui.internal.open_popup_ex(popup_id)
        self.msn_combo_row = row_index
        self.msn_search = ""
        current = entry.msn.strip().upper()
        if current in self.mission_list:
            self.msn_highlight = self.mission_list.index(current)
        else:
            self.msn_highlight = 0 if self.mission_list else -1
        self.msn_scroll_pending = True

    def _render_msn_combo(self, row_index: int, entry: AbbrevColorEntry):
        if self.msn_combo_row == row_index and self.msn_search:
            preview = self.msn_search
        else:
            preview = entry.msn

        imgui.set_next_item_width(-1)
        if imgui.begin_combo(f"##msn_{row_index}", preview, imgui.ComboFlags_.height_large.value):
            if self.msn_combo_row != row_index:
                # Combo just opened: reset search, highlight current value
                self.msn_combo_row = row_index
                self.msn_search = ""
                current = entry.msn.strip().upper()
                if current in self.mission_list:
                    self.msn_highlight = self.mission_list.index(current)
                else:
                    self.msn_highlight = 0 if self.mission_list else -1
                self.msn_scroll_pending = True

            # Cancel any pending nav move so arrow keys don't scroll the popup;
            # our own highlight handling owns the arrows
            imgui.internal.nav_move_request_cancel()

            # Only consume keystrokes when the dropdown popup itself has focus,
            # so typing elsewhere (e.g. on the map) never triggers mission search
            if imgui.is_window_focused(imgui.FocusedFlags_.root_and_child_windows.value):
                selected_now = self._handle_msn_keys(entry)
            else:
                selected_now = False

            # Nav is disabled on the list items so arrow keys drive our own
            # highlight instead of imgui's nav cursor
            imgui.push_item_flag(imgui.ItemFlags_.no_nav.value, True)
            for i, name in enumerate(self.mission_list):
                is_highlighted = (i == self.msn_highlight)
                clicked, _ = imgui.selectable(f"{name}##msn_item_{row_index}_{i}", is_highlighted)
                if clicked and not selected_now:
                    self._select_mission(entry, i)
                if is_highlighted and self.msn_scroll_pending:
                    imgui.set_scroll_here_y(0.5)
                    self.msn_scroll_pending = False
            imgui.pop_item_flag()
            imgui.end_combo()
        elif self.msn_combo_row == row_index:
            # Combo closed without a selection
            self.msn_combo_row = None
            self.msn_search = ""
        else:
            # Combo is closed: Delete blanks the field when it is focused or hovered
            if (imgui.is_item_focused() or imgui.is_item_hovered()) \
                    and imgui.is_key_pressed(imgui.Key.delete):
                entry.msn = ""
            if imgui.is_item_focused():
                # Up/Down on the closed field steps the value in place (no dropdown);
                # the nav move is cancelled so focus stays on this field
                if imgui.is_key_pressed(imgui.Key.down_arrow) and self.mission_list:
                    entry.msn = self._step_mission(entry.msn, 1)
                    imgui.internal.nav_move_request_cancel()
                if imgui.is_key_pressed(imgui.Key.up_arrow) and self.mission_list:
                    entry.msn = self._step_mission(entry.msn, -1)
                    imgui.internal.nav_move_request_cancel()
                # Space pops the list open
                if imgui.is_key_pressed(imgui.Key.space):
                    self._open_msn_combo(row_index, entry)
                # Typing a letter opens the list and starts the search with it
                for key_val in range(imgui.Key.a.value, imgui.Key.z.value + 1):
                    if imgui.is_key_pressed(imgui.Key(key_val)):
                        self._open_msn_combo(row_index, entry)
                        self._msn_type_char(chr(ord('A') + key_val - imgui.Key.a.value))
                        break

    def _default_color_for(self, entry: AbbrevColorEntry) -> Optional[List[float]]:
        mission_color = self.mission_colors.get(entry.msn.strip().upper())
        if mission_color is None:
            return None
        return [*mission_color, 1.0]

    def _apply_default_colors(self):
        for entry in self.entries:
            default = self._default_color_for(entry)
            if default is not None:
                entry.color = default

    def _select_color(self, row_index: int, selected_color: List[float]):
        if 0 <= row_index < len(self.entries):
            self.entries[row_index].color = list(selected_color)
        self.last_color = list(selected_color)
        self.color_picker_row = None
        imgui.close_current_popup()

    def apply(self):
        """Apply each row to the game objects: every object whose callsign (CallSign,
        else Pilot) starts with the row's Full CS gets its track label replaced with
        the row's Abbrev plus the remaining suffix (Devil1 w/ DVL1 -> Devil12 becomes
        DVL12), and its color set from the row. CallSign/Pilot data are preserved
        (only the display override_name/override_color are touched)."""
        if self.gamestate is None:
            return

        for entry in self.entries:
            flight = entry.full_cs.strip()
            if not flight:
                continue
            flight_upper = flight.upper()
            abbrev = entry.abbrev.strip()
            color = tuple(entry.color)

            for obj in self.gamestate.all_objects.values():
                callsign = (getattr(obj, "CallSign", "") or "").strip()
                pilot = (getattr(obj, "Pilot", "") or "").strip()
                for base in (callsign, pilot):
                    if not base or not base.upper().startswith(flight_upper):
                        continue
                    if abbrev:
                        obj.override_name = abbrev + base[len(flight):]
                    obj.override_color = color
                    self.gamestate.render_arrays.update_object(obj)
                    break

    @staticmethod
    def _flight_from_callsign(callsign: str) -> Optional[str]:
        """Derive the flight from a ship callsign: Devil12 / Devil 1-2 -> Devil1."""
        normalized = re.sub(r"\s+", "", callsign)
        match = re.match(r"([A-Za-z]+)(\d+)", normalized)
        if match is None:
            return None
        name, digits = match.group(1), match.group(2)
        flight_num = digits if len(digits) == 1 else digits[:-1]
        return name + flight_num

    def add_human_flights(self):
        """Add every flight containing a human (Pilot field non-empty) to the
        table. Fills blank rows first, then appends. No role data available."""
        if self.gamestate is None:
            return

        existing = {e.full_cs.strip().upper() for e in self.entries if e.full_cs.strip()}
        flights: List[str] = []
        for obj in self.gamestate.all_objects.values():
            pilot = (getattr(obj, "Pilot", "") or "").strip()
            callsign = (getattr(obj, "CallSign", "") or "").strip()
            # AI ships carry their callsign in the Pilot field; a differing
            # Pilot value means a human is in the seat
            if not pilot or pilot.upper() == callsign.upper():
                continue
            base = callsign or pilot
            flight = self._flight_from_callsign(base)
            if flight is None or flight.upper() in existing:
                continue
            existing.add(flight.upper())
            flights.append(flight)

        # Fill blank rows first, then append the rest
        index = 0
        for entry in self.entries:
            if index >= len(flights):
                break
            if not entry.full_cs.strip():
                entry.full_cs = flights[index]
                index += 1
        for flight in flights[index:]:
            self.entries.append(AbbrevColorEntry(full_cs=flight))
        self.rows = len(self.entries)

    def apply_ai(self):
        """Abbreviate the track label (AB/ABR as last selected) of every object
        not covered by a row in the list. No color change."""
        if self.gamestate is None:
            return

        flights = [e.full_cs.strip().upper() for e in self.entries if e.full_cs.strip()]

        for obj in self.gamestate.all_objects.values():
            callsign = (getattr(obj, "CallSign", "") or "").strip()
            pilot = (getattr(obj, "Pilot", "") or "").strip()
            bases = [b for b in (callsign, pilot) if b]
            if not bases:
                continue
            # Skip tracks already covered by a row in the list
            if any(b.upper().startswith(f) for f in flights for b in bases):
                continue
            for base in bases:
                abbrev = self._abbrev_for_callsign(base, self.use_three_letter)
                if abbrev is not None:
                    obj.override_name = abbrev
                    break

    @staticmethod
    def _set_keyboard_nav(enabled: bool):
        """Enable Tab/keyboard navigation only while this window is in use."""
        io = imgui.get_io()
        nav_flag = imgui.ConfigFlags_.nav_enable_keyboard.value
        if enabled:
            io.config_flags = io.config_flags | nav_flag
        else:
            io.config_flags = io.config_flags & ~nav_flag

    def render(self):
        if not self.open:
            self._set_keyboard_nav(False)
            return

        imgui.set_next_window_size_constraints(imgui.ImVec2(640, 0), imgui.ImVec2(9999, 9999))
        result = imgui.begin("Abbrev Color", self.open, imgui.WindowFlags_.always_auto_resize.value)
        if isinstance(result, tuple):
            expanded, open_state = result
        else:
            expanded = result
            open_state = True

        if not open_state:
            self.open = False
            self._set_keyboard_nav(False)
            imgui.end()
            return

        # Tab cycles through Full CS -> Abbrev -> Msn per row; keyboard nav is
        # only active while this window (or its popups) has focus
        self._set_keyboard_nav(
            imgui.is_window_focused(imgui.FocusedFlags_.root_and_child_windows.value)
            or self.msn_combo_row is not None
            or self.color_picker_row is not None)

        if expanded:
            # Toolbar row above the table (more controls will live here later).
            # Buttons are aligned over their columns (x captured last frame).
            imgui.push_item_flag(imgui.ItemFlags_.no_tab_stop.value, True)
            if imgui.small_button("UOAF"):
                self.uoaf_window_open = True
            imgui.same_line()
            if imgui.small_button("HF"):
                self.add_human_flights()
            imgui.same_line()
            if self._abbrev_col_x is not None:
                cur = imgui.get_cursor_screen_pos()
                imgui.set_cursor_screen_pos(imgui.ImVec2(self._abbrev_col_x, cur.y))
            if imgui.small_button("AB"):
                self._apply_abbrevs(False)
            imgui.same_line()
            if imgui.small_button("ABR"):
                self._apply_abbrevs(True)
            imgui.same_line()
            if self._color_col_x is not None:
                cur = imgui.get_cursor_screen_pos()
                imgui.set_cursor_screen_pos(imgui.ImVec2(self._color_col_x, cur.y))
            if imgui.small_button("Def"):
                self._apply_default_colors()
            imgui.pop_item_flag()
            imgui.separator()

            child_height = self._get_table_height()
            # nav_flattened: Tab goes straight to the first field instead of
            # selecting the child window / whole table
            imgui.begin_child("AbbrevColorTableChild", imgui.ImVec2(0, child_height),
                              imgui.ChildFlags_.borders.value
                              | imgui.ChildFlags_.nav_flattened.value)
            if imgui.begin_table("AbbrevColorTable", 5,
                                 imgui.TableFlags_.borders.value
                                 | imgui.TableFlags_.row_bg.value
                                 | imgui.TableFlags_.resizable.value
                                 | imgui.TableFlags_.no_host_extend_x.value):
                imgui.table_setup_column("Full CS", imgui.TableColumnFlags_.width_stretch.value)
                imgui.table_setup_column("Abbrev", imgui.TableColumnFlags_.width_fixed.value, 120.0)
                imgui.table_setup_column("Msn", imgui.TableColumnFlags_.width_fixed.value, 80.0)
                imgui.table_setup_column("Clr", imgui.TableColumnFlags_.width_fixed.value, 32.0)
                imgui.table_setup_column("##remove", imgui.TableColumnFlags_.width_fixed.value, 30.0)
                # Headers are not tab stops / nav targets
                imgui.push_item_flag(imgui.ItemFlags_.no_tab_stop.value, True)
                imgui.push_item_flag(imgui.ItemFlags_.no_nav.value, True)
                imgui.table_headers_row()
                imgui.pop_item_flag()
                imgui.pop_item_flag()

                row_to_remove: Optional[int] = None

                for row_index, entry in enumerate(self.entries):
                    imgui.table_next_row()

                    imgui.table_set_column_index(0)
                    _, entry.full_cs = imgui.input_text(f"##fullcs_{row_index}", entry.full_cs)

                    imgui.table_set_column_index(1)
                    if row_index == 0:
                        self._abbrev_col_x = imgui.get_cursor_screen_pos().x
                    _, entry.abbrev = imgui.input_text(f"##abbrev_{row_index}", entry.abbrev)

                    imgui.table_set_column_index(2)
                    self._render_msn_combo(row_index, entry)

                    imgui.table_set_column_index(3)
                    swatch_pos = imgui.get_cursor_screen_pos()
                    if row_index == 0:
                        self._color_col_x = swatch_pos.x
                    imgui.push_item_flag(imgui.ItemFlags_.no_tab_stop.value, True)
                    if imgui.color_button(f"##color_btn_{row_index}", entry.color,
                                          imgui.ColorEditFlags_.alpha_preview_half.value,
                                          imgui.ImVec2(20, 20)):
                        self.color_picker_row = row_index

                    # Tiny button beside the top-right of the swatch:
                    # sets this row's color to its Msn default, no questions asked
                    row_default = self._default_color_for(entry)
                    if row_default is not None:
                        tiny = 6.0
                        imgui.set_cursor_screen_pos(
                            imgui.ImVec2(swatch_pos.x + 20 + 3, swatch_pos.y))
                        imgui.push_style_color(imgui.Col_.button.value, imgui.ImVec4(*row_default))
                        imgui.push_style_color(imgui.Col_.button_hovered.value, imgui.ImVec4(*row_default))
                        imgui.push_style_color(imgui.Col_.button_active.value, imgui.ImVec4(*row_default))
                        if imgui.button(f"##rowdef_{row_index}", imgui.ImVec2(tiny, tiny)):
                            entry.color = row_default
                        imgui.pop_style_color(3)
                    imgui.pop_item_flag()

                    if self.color_picker_row == row_index:
                        imgui.open_popup(f"ColorPickerPopup_{row_index}")

                    if imgui.begin_popup(f"ColorPickerPopup_{row_index}", imgui.WindowFlags_.always_auto_resize.value):
                        changed, new_color = imgui.color_edit4(f"Color##picker_{row_index}", entry.color)
                        if changed:
                            entry.color = list(new_color)
                            self.last_color = list(new_color)
                        # Auto-close once the user finishes picking (mouse released / edit done)
                        if imgui.is_item_deactivated_after_edit():
                            self.color_picker_row = None
                            imgui.close_current_popup()

                        if imgui.button("Close"):
                            self.color_picker_row = None
                            imgui.close_current_popup()

                        imgui.same_line()
                        imgui.text("Last:")
                        imgui.same_line()
                        if imgui.color_button(f"##last_color_{row_index}", self.last_color,
                                              imgui.ColorEditFlags_.alpha_preview_half.value,
                                              imgui.ImVec2(20, 20)):
                            self._select_color(row_index, self.last_color)

                        if entry.msn.strip():
                            mission_name = entry.msn.strip().upper()
                            mission_color = self.mission_colors.get(mission_name)
                            if mission_color is not None:
                                imgui.same_line()
                                imgui.text(mission_name)
                                imgui.same_line()
                                if imgui.color_button(f"##mission_color_{row_index}",
                                                      [*mission_color, 1.0],
                                                      imgui.ColorEditFlags_.alpha_preview_half.value,
                                                      imgui.ImVec2(20, 20)):
                                    self._select_color(row_index, [*mission_color, 1.0])

#                        imgui.same_line()
#                        imgui.text("Current:")
#                        imgui.same_line()
#                        if imgui.color_button(f"##current_color_{row_index}", entry.color,
#                                              imgui.ColorEditFlags_.alpha_preview_half.value,
#                                              imgui.ImVec2(20, 20)):
#                            self._select_color(row_index, entry.color)

#                        imgui.same_line()
#                        imgui.text("Previous:")
#                        imgui.same_line()
#                        if imgui.color_button(f"##previous_color_{row_index}", self.last_color,
#                                              imgui.ColorEditFlags_.alpha_preview_half.value,
#                                              imgui.ImVec2(20, 20)):
#                            self._select_color(row_index, self.last_color)

                        imgui.end_popup()

                    imgui.table_set_column_index(4)
                    imgui.push_item_flag(imgui.ItemFlags_.no_tab_stop.value, True)
                    if imgui.button(f"-##remove_{row_index}", imgui.ImVec2(22, 0)):
                        row_to_remove = row_index
                    imgui.pop_item_flag()

                if row_to_remove is not None:
                    self._remove_row(row_to_remove)

                imgui.end_table()
            imgui.end_child()

            imgui.separator()
            imgui.push_item_flag(imgui.ItemFlags_.no_tab_stop.value, True)
            if imgui.button("+1", imgui.ImVec2(30, 0)):
                self._add_rows(1)
            imgui.same_line()
            if imgui.button("+4", imgui.ImVec2(30, 0)):
                self._add_rows(4)
            imgui.same_line()
            if imgui.button("Apply", imgui.ImVec2(60, 0)):
                self.apply()
            imgui.same_line()
            if imgui.button("AI", imgui.ImVec2(40, 0)):
                self.apply_ai()
            # Clear sits all the way to the right on the same row
            imgui.same_line()
            clear_width = 60.0
            remaining = imgui.get_content_region_avail().x
            if remaining > clear_width:
                imgui.set_cursor_pos_x(
                    imgui.get_cursor_pos_x() + remaining - clear_width)
            if imgui.button("Clear", imgui.ImVec2(clear_width, 0)):
                self._clear_fields()
            imgui.pop_item_flag()

        imgui.end()

        self._render_uoaf_window()
